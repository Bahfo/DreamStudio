# DreamStudio IDE Test History

> **Purpose**: Chronological index of all test runs. Append-only — never modify previous entries.

---

## Test Run Index



---

## Format

Each entry contains:
- **Run ID**: `YYYYMMDDTHHMMSSZ-gitrev[-dirty]`
- **Timestamp**: UTC ISO 8601
- **Suites**: Test suites executed
- **Git**: Commit hash + dirty status
- **Duration**: Seconds
- **Verdict**: PASSED/FAILED/INTERRUPTED/INFRASTRUCTURE ERROR/NO TESTS
- **Counts**: Passed | Failed | Errors | Skipped | Blocked
- **Links**: Report, console log, summary JSON

## Run Artifacts Location

- Per-run details: `tests/reports/runs/<run_id>/`
- Machine-readable history: `tests/reports/history/<run_id>.json`

## Notes

- This file is version-controlled
- Detailed artifacts in `runs/` are **not** version-controlled (see `.gitignore`)
- A newer successful run **never erases** earlier failure records
- If a recording error is discovered, preserve original and append correction

## 20261025T165620Z-7c47925-dirty

- **Timestamp**: 2026-10-25T16:56:20Z
- **Suites**: bootstrapping
- **Git**: 7c47925 (dirty)
- **Duration**: 2s
- **Verdict**: PASSED
- **Passed**: 38 | **Failed**: 0 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261025T165620Z-7c47925-dirty/report.md`
- **Console**: `tests/reports/runs/20261025T165620Z-7c47925-dirty/console.log`
- **Summary**: `tests/reports/runs/20261025T165620Z-7c47925-dirty/summary.json`

## 20261025T165632Z-7c47925-dirty

- **Timestamp**: 2026-10-25T16:56:32Z
- **Suites**: bootstrapping, editor, navigation
- **Git**: 7c47925 (dirty)
- **Duration**: 9s
- **Verdict**: FAILED
- **Passed**: 98 | **Failed**: 7 | **Errors**: 0 | **Skipped**: 1 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261025T165632Z-7c47925-dirty/report.md`
- **Console**: `tests/reports/runs/20261025T165632Z-7c47925-dirty/console.log`
- **Summary**: `tests/reports/runs/20261025T165632Z-7c47925-dirty/summary.json`

## 20261025T170314Z-7c47925-dirty

- **Timestamp**: 2026-10-25T17:03:14Z
- **Suites**: bootstrapping
- **Git**: 7c47925 (dirty)
- **Duration**: 0s
- **Verdict**: INTERRUPTED
- **Passed**: 0 | **Failed**: 0 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261025T170314Z-7c47925-dirty/report.md`
- **Console**: `tests/reports/runs/20261025T170314Z-7c47925-dirty/console.log`
- **Summary**: `tests/reports/runs/20261025T170314Z-7c47925-dirty/summary.json`

## 20261025T170324Z-7c47925-dirty-2

- **Timestamp**: 2026-10-25T17:03:24Z
- **Suites**: bootstrapping
- **Git**: 7c47925 (dirty)
- **Duration**: 2s
- **Verdict**: PASSED
- **Passed**: 38 | **Failed**: 0 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261025T170324Z-7c47925-dirty-2/report.md`
- **Console**: `tests/reports/runs/20261025T170324Z-7c47925-dirty-2/console.log`
- **Summary**: `tests/reports/runs/20261025T170324Z-7c47925-dirty-2/summary.json`

## 20261025T170334Z-7c47925-dirty

- **Timestamp**: 2026-10-25T17:03:34Z
- **Suites**: bootstrapping, editor, navigation
- **Git**: 7c47925 (dirty)
- **Duration**: 10s
- **Verdict**: FAILED
- **Passed**: 98 | **Failed**: 7 | **Errors**: 0 | **Skipped**: 1 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261025T170334Z-7c47925-dirty/report.md`
- **Console**: `tests/reports/runs/20261025T170334Z-7c47925-dirty/console.log`
- **Summary**: `tests/reports/runs/20261025T170334Z-7c47925-dirty/summary.json`

## 20261025T175058Z-1f8c0fb

- **Timestamp**: 2026-10-25T17:50:58Z
- **Suites**: bootstrapping
- **Git**: 1f8c0fb
- **Duration**: 2s
- **Verdict**: PASSED
- **Passed**: 38 | **Failed**: 0 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261025T175058Z-1f8c0fb/report.md`
- **Console**: `tests/reports/runs/20261025T175058Z-1f8c0fb/console.log`
- **Summary**: `tests/reports/runs/20261025T175058Z-1f8c0fb/summary.json`

## 20261025T175133Z-1f8c0fb-dirty

- **Timestamp**: 2026-10-25T17:51:33Z
- **Suites**: bootstrapping, editor, navigation
- **Git**: 1f8c0fb (dirty)
- **Duration**: 8s
- **Verdict**: FAILED
- **Passed**: 98 | **Failed**: 7 | **Errors**: 0 | **Skipped**: 1 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261025T175133Z-1f8c0fb-dirty/report.md`
- **Console**: `tests/reports/runs/20261025T175133Z-1f8c0fb-dirty/console.log`
- **Summary**: `tests/reports/runs/20261025T175133Z-1f8c0fb-dirty/summary.json`

## 20261027T160625Z-1f8c0fb-dirty

- **Timestamp**: 2026-10-27T16:06:25Z
- **Suites**: bootstrapping
- **Git**: 1f8c0fb (dirty)
- **Duration**: 2s
- **Verdict**: PASSED
- **Passed**: 38 | **Failed**: 0 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261027T160625Z-1f8c0fb-dirty/report.md`
- **Console**: `tests/reports/runs/20261027T160625Z-1f8c0fb-dirty/console.log`
- **Summary**: `tests/reports/runs/20261027T160625Z-1f8c0fb-dirty/summary.json`

## 20261027T160636Z-1f8c0fb-dirty

- **Timestamp**: 2026-10-27T16:06:36Z
- **Suites**: editor
- **Git**: 1f8c0fb (dirty)
- **Duration**: 5s
- **Verdict**: FAILED
- **Passed**: 43 | **Failed**: 1 | **Errors**: 0 | **Skipped**: 1 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261027T160636Z-1f8c0fb-dirty/report.md`
- **Console**: `tests/reports/runs/20261027T160636Z-1f8c0fb-dirty/console.log`
- **Summary**: `tests/reports/runs/20261027T160636Z-1f8c0fb-dirty/summary.json`

## 20261027T160649Z-1f8c0fb-dirty

- **Timestamp**: 2026-10-27T16:06:49Z
- **Suites**: navigation
- **Git**: 1f8c0fb (dirty)
- **Duration**: 3s
- **Verdict**: FAILED
- **Passed**: 17 | **Failed**: 6 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261027T160649Z-1f8c0fb-dirty/report.md`
- **Console**: `tests/reports/runs/20261027T160649Z-1f8c0fb-dirty/console.log`
- **Summary**: `tests/reports/runs/20261027T160649Z-1f8c0fb-dirty/summary.json`

## 20261027T171422Z-1f8c0fb-dirty

- **Timestamp**: 2026-10-27T17:14:22Z
- **Suites**: python_plugin
- **Git**: 1f8c0fb (dirty)
- **Duration**: 234s
- **Verdict**: PASSED
- **Passed**: 591 | **Failed**: 0 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261027T171422Z-1f8c0fb-dirty/report.md`
- **Console**: `tests/reports/runs/20261027T171422Z-1f8c0fb-dirty/console.log`
- **Summary**: `tests/reports/runs/20261027T171422Z-1f8c0fb-dirty/summary.json`

## 20261027T172526Z-1f8c0fb-dirty

- **Timestamp**: 2026-10-27T17:25:26Z
- **Suites**: python_plugin
- **Git**: 1f8c0fb (dirty)
- **Duration**: 197s
- **Verdict**: PASSED
- **Passed**: 591 | **Failed**: 0 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261027T172526Z-1f8c0fb-dirty/report.md`
- **Console**: `tests/reports/runs/20261027T172526Z-1f8c0fb-dirty/console.log`
- **Summary**: `tests/reports/runs/20261027T172526Z-1f8c0fb-dirty/summary.json`

## 20261027T175027Z-1f8c0fb-dirty

- **Timestamp**: 2026-10-27T17:50:27Z
- **Suites**: bootstrapping, editor, navigation, python_plugin
- **Git**: 1f8c0fb (dirty)
- **Duration**: 183s
- **Verdict**: FAILED
- **Passed**: 689 | **Failed**: 7 | **Errors**: 0 | **Skipped**: 1 | **Blocked**: 0
- **Report**: `tests/reports/runs/20261027T175027Z-1f8c0fb-dirty/report.md`
- **Console**: `tests/reports/runs/20261027T175027Z-1f8c0fb-dirty/console.log`
- **Summary**: `tests/reports/runs/20261027T175027Z-1f8c0fb-dirty/summary.json`

