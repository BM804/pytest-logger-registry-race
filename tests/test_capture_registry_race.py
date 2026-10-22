"""Deterministic regression coverage for pytest issue #15237."""

from __future__ import annotations

import logging
import threading
import unittest
from unittest.mock import patch

from logger_registry_race.capture import attach_non_propagating_loggers, detach_loggers


class TriggerLogger(logging.Logger):
    def __init__(self, name: str, on_propagate_read):
        super().__init__(name)
        self._on_propagate_read = on_propagate_read

    @property
    def propagate(self) -> bool:
        self._on_propagate_read()
        return True

    @propagate.setter
    def propagate(self, value: bool) -> None:
        pass


class LoggerRegistryRaceTests(unittest.TestCase):
    def run_setup(self, *, snapshot: bool) -> None:
        manager = logging.root.manager
        trigger_name = "repro.concurrent-registration.trigger"
        new_name = "repro.concurrent-registration.from-worker"
        mutation_completed = threading.Event()
        worker_errors: list[BaseException] = []

        def register_logger() -> None:
            try:
                logging.getLogger(new_name)
            except BaseException as exc:  # surfaced in the controlling thread below
                worker_errors.append(exc)
            finally:
                mutation_completed.set()

        worker: threading.Thread | None = None

        def mutate_registry() -> None:
            nonlocal worker
            worker = threading.Thread(target=register_logger, daemon=True)
            worker.start()
            if not mutation_completed.wait(timeout=2):
                raise AssertionError("worker did not register its logger")

        handler = logging.NullHandler()
        old_trigger = manager.loggerDict.get(trigger_name)
        old_new = manager.loggerDict.get(new_name)
        manager.loggerDict[trigger_name] = TriggerLogger(trigger_name, mutate_registry)
        try:
            with patch.object(manager, "loggerDict", manager.loggerDict):
                attached = attach_non_propagating_loggers(handler, snapshot=snapshot)
            if worker is not None:
                worker.join(timeout=2)
            self.assertFalse(worker and worker.is_alive(), "logger registration worker did not finish")
            self.assertEqual(worker_errors, [])
        finally:
            if worker is not None:
                worker.join(timeout=2)
            detach_loggers(handler, [logging.getLogger(), manager.loggerDict.get(trigger_name)])
            if old_trigger is None:
                manager.loggerDict.pop(trigger_name, None)
            else:
                manager.loggerDict[trigger_name] = old_trigger
            if old_new is None:
                manager.loggerDict.pop(new_name, None)
            else:
                manager.loggerDict[new_name] = old_new

    def test_live_view_reproduces_dictionary_changed_size(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "dictionary changed size during iteration"):
            self.run_setup(snapshot=False)

    def test_snapshot_survives_concurrent_logger_registration(self) -> None:
        self.run_setup(snapshot=True)


if __name__ == "__main__":
    unittest.main()

