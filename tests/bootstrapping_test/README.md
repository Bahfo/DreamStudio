# Bootstrapping Test Suite

## Overview
Tests for the DreamStudio IDE startup kernel: phase pipeline, service registry, configuration, resources, splash screen, solution prompt, and main window initialization.

## Latest Run

- **Run ID**: 20261025T170334Z-7c47925-dirty
- **Timestamp**: 2026-10-25T17:03:34Z
- **Verdict**: PASSED
- **Passed**: 38 | **Failed**: 0 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- [Report](../reports/runs/20261025T170334Z-7c47925-dirty/report.md)

## Historical Runs

| Run ID | Timestamp | Verdict | Passed | Failed | Errors | Skipped | Blocked | Report |
|--------|-----------|---------|--------|--------|--------|---------|---------|--------|
| 20261025T170334Z-7c47925-dirty | 2026-10-25T17:03:34Z | PASSED | 38 | 0 | 0 | 0 | 0 | [Report](../reports/runs/20261025T170334Z-7c47925-dirty/report.md) |
| 20261025T170324Z-7c47925-dirty-2 | 2026-10-25T17:03:24Z | PASSED | 38 | 0 | 0 | 0 | 0 | [Report](../reports/runs/20261025T170324Z-7c47925-dirty-2/report.md) |
| 20261025T170314Z-7c47925-dirty | 2026-10-25T17:03:14Z | INTERRUPTED | 0 | 0 | 0 | 0 | 0 | [Report](../reports/runs/20261025T170314Z-7c47925-dirty/report.md) |
| 20261025T165632Z-7c47925-dirty | 2026-10-25T16:56:32Z | PASSED | 38 | 0 | 0 | 0 | 0 | [Report](../reports/runs/20261025T165632Z-7c47925-dirty/report.md) |
| 20261025T165620Z-7c47925-dirty | 2026-10-25T16:56:20Z | PASSED | 38 | 0 | 0 | 0 | 0 | [Report](../reports/runs/20261025T165620Z-7c47925-dirty/report.md) |

## Scope & Limitations
- **In scope**: `config/` package (manager, phases, registry, config, resources, splash, recovery) — older docs call this the bootstrap package
- **In scope**: `startup.py` entry point and `_reveal_result` logic
- **In scope**: Service registry contract keys and phase context mutation
- **Out of scope**: UI rendering, editor initialization, plugin loading (separate suites)
- **Known limitations**: Full startup requires a Qt event loop; orchestration and phase contracts are tested in isolation
- **Manual verification needed**: Splash screen visual, recovery window rendering

## Failure Reproduction
To reproduce failures from this run:
```bash
./tests/run_tests.sh --suite bootstrapping
```

Or directly with pytest:
```bash
QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/bootstrapping_test/ -p no:cacheprovider -q
```
