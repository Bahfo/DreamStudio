# Navigation Test Suite

## Overview
Tests for code navigation: EditorAPI delegation, the CodeEditor go-to-definition pipeline, target opening, language registration/resolution, provider defaults, and outline parser registration.

## Latest Run

- **Run ID**: 20261030T184920Z-3f9e2ee-dirty
- **Timestamp**: 2026-10-30T18:49:20Z
- **Verdict**: FAILED
- **Passed**: 17 | **Failed**: 6 | **Errors**: 0 | **Skipped**: 0 | **Blocked**: 0
- [Report](../reports/runs/20261030T184920Z-3f9e2ee-dirty/report.md)

## Historical Runs

| Run ID | Timestamp | Verdict | Passed | Failed | Errors | Skipped | Blocked | Report |
|--------|-----------|---------|--------|--------|--------|---------|---------|--------|
| 20261030T184920Z-3f9e2ee-dirty | 2026-10-30T18:49:20Z | FAILED | 17 | 6 | 0 | 0 | 0 | [Report](../reports/runs/20261030T184920Z-3f9e2ee-dirty/report.md) |
| 20261027T175027Z-1f8c0fb-dirty | 2026-10-27T17:50:27Z | FAILED | 17 | 6 | 0 | 0 | 0 | [Report](../reports/runs/20261027T175027Z-1f8c0fb-dirty/report.md) |
| 20261027T160649Z-1f8c0fb-dirty | 2026-10-27T16:06:49Z | FAILED | 17 | 6 | 0 | 0 | 0 | [Report](../reports/runs/20261027T160649Z-1f8c0fb-dirty/report.md) |
| 20261025T175133Z-1f8c0fb-dirty | 2026-10-25T17:51:33Z | FAILED | 17 | 6 | 0 | 0 | 0 | [Report](../reports/runs/20261025T175133Z-1f8c0fb-dirty/report.md) |
| 20261025T170334Z-7c47925-dirty | 2026-10-25T17:03:34Z | FAILED | 17 | 6 | 0 | 0 | 0 | [Report](../reports/runs/20261025T170334Z-7c47925-dirty/report.md) |
| 20261025T165632Z-7c47925-dirty | 2026-10-25T16:56:32Z | FAILED | 17 | 6 | 0 | 0 | 0 | [Report](../reports/runs/20261025T165632Z-7c47925-dirty/report.md) |

## Scope & Limitations
- **In scope**: `editor/Ironica/api.py` — navigation facade delegation for implemented methods
- **In scope**: `editor/Ironica/code_editor.py` — definition resolution, target opening, same-line guard, failure path
- **In scope**: `editor/Ironica/language_engine.py` — language registration, extension/filename resolution, provider binding and defaults
- **In scope**: `editor/utils/file_properties/outline.py` — outline parser registration and symbol kinds
- **Out of scope**: Live Jedi/libclang/CMake provider accuracy and cross-file indexing (optional dependencies)
- **Out of scope**: Hover tooltips, multi-target navigation popup rendering, out-of-process analysis
- **Known failures (contract gaps)**: `goto_declaration()` and `goto_implementation()` reuse the definition handler; `goto_usage`, `goto_reference`, `find_usages`, and `goto_implementation_file` are documented but absent
- **Known limitation**: Tests use mocks at the provider/tab-container boundary; no real language server is launched
- **Manual verification needed**: Cross-file navigation accuracy, hover tooltip rendering, multi-target popup

## Failure Reproduction
To reproduce failures from this run:
```bash
./tests/run_tests.sh --suite navigation
```

Or directly with pytest:
```bash
QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/navigation_test/ -p no:cacheprovider -q
```
