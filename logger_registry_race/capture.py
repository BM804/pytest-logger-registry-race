"""Small reproduction of pytest's logging registry traversal race."""

from __future__ import annotations

import logging


def attach_non_propagating_loggers(handler: logging.Handler, *, snapshot: bool) -> list[logging.Logger]:
    """Attach a handler to non-propagating loggers and return attached loggers.

    ``snapshot=False`` models the vulnerable live ``dict_values`` iteration.
    ``snapshot=True`` applies the fix proposed for pytest issue #15237.
    """
    root_logger = logging.getLogger()
    attached = [root_logger]
    root_logger.addHandler(handler)
    values = root_logger.manager.loggerDict.values()
    if snapshot:
        values = list(values)
    for logger in values:
        if isinstance(logger, logging.Logger) and not logger.propagate and logger is not root_logger:
            logger.addHandler(handler)
            attached.append(logger)
    return attached


def detach_loggers(handler: logging.Handler, attached: list[logging.Logger]) -> None:
    for logger in attached:
        logger.removeHandler(handler)
