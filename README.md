# pytest logger registry race

A focused reproduction and fix for [pytest issue #15237](https://github.com/pytest-dev/pytest/issues/15237).

## Problem

pytest's logging capture setup iterates `logging.root.manager.loggerDict.values()` while another thread can register a logger with `logging.getLogger()`. That mutates the dictionary during iteration and can raise `RuntimeError: dictionary changed size during iteration` before tests run.

## Fix

Take a shallow snapshot of the logger registry before iterating it. Loggers registered after setup begins need not be inspected for that capture scope. The upstream change is included in [`patches/pytest-logging-race.patch`](patches/pytest-logging-race.patch).

## Reproduce and verify

Requires Python 3.10 or newer; no third-party package is needed.

```powershell
python -m unittest discover -s tests -v
```

The regression test forces the race deterministically: while capture setup inspects a logger's `propagate` property, a second thread registers another logger. It asserts that the live-dictionary implementation raises and that snapshot iteration completes successfully.

## Scope

This repository isolates the reported failure and demonstrates the proposed one-line fix. It does not vendor pytest or claim that the full pytest suite has been run.

