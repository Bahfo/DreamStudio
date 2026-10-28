# Editor Test Suite

## Overview
Tests for the Ironica code editor: CodeEditor loading/saving, dirty-state propagation, encoding fallback, tab lifecycle and deduplication, binary/fallback tabs, the EditorAPI facade, DiagnosticStore merge policy, and the dirty→git-scan fan-out.

## Latest Run

- **Run ID**: 20261027T175027Z-1f8c0fb-dirty
- **Timestamp**: 2026-10-27T17:50:27Z
- **Verdict**: FAILED
- **Passed**: 43 | **Failed**: 1 | **Errors**: 0 | **Skipped**: 1 | **Blocked**: 0
- [Report](../reports/runs/20261027T175027Z-1f8c0fb-dirty/report.md)

## Historical Runs

| Run ID | Timestamp | Verdict | Passed | Failed | Errors | Skipped | Blocked | Report |
|--------|-----------|---------|--------|--------|--------|---------|---------|--------|
| 20261027T175027Z-1f8c0fb-dirty | 2026-10-27T17:50:27Z | FAILED | 43 | 1 | 0 | 1 | 0 | [Report](../reports/runs/20261027T175027Z-1f8c0fb-dirty/report.md) |
| 20261027T160636Z-1f8c0fb-dirty | 2026-10-27T16:06:36Z | FAILED | 43 | 1 | 0 | 1 | 0 | [Report](../reports/runs/20261027T160636Z-1f8c0fb-dirty/report.md) |
| 20261025T175133Z-1f8c0fb-dirty | 2026-10-25T17:51:33Z | FAILED | 43 | 1 | 0 | 1 | 0 | [Report](../reports/runs/20261025T175133Z-1f8c0fb-dirty/report.md) |
| 20261025T170334Z-7c47925-dirty | 2026-10-25T17:03:34Z | FAILED | 43 | 1 | 0 | 1 | 0 | [Report](../reports/runs/20261025T170334Z-7c47925-dirty/report.md) |
| 20261025T165632Z-7c47925-dirty | 2026-10-25T16:56:32Z | FAILED | 43 | 1 | 0 | 1 | 0 | [Report](../reports/runs/20261025T165632Z-7c47925-dirty/report.md) |

## Scope & Limitations
- **In scope**: `editor/Ironica/code_editor.py` — loading, saving, dirty state, encoding fallback, read-only handling
- **In scope**: `editor/Ironica/tab_editor.py` — tab lifecycle, dedup, close interceptors, fallback/binary editors
- **In scope**: `editor/Ironica/api.py` — EditorAPI facade: clipboard, history, structure, existing navigation methods, folding, file ops
- **In scope**: `editor/widgets/QDreamTabEditor.py` — dirty/read-only tab indicators
- **In scope**: `editor/analysis/diagnostic_store.py` — dirty/clean merge policy, live revision ordering
- **In scope**: `editor/utils/git_control/status_service.py` — dirty-state scan requests (mocked boundary)
- **Out of scope**: Visual syntax highlighting, minimap rendering, ghost-text folding, language providers
- **Known limitations**: Qt/Scintilla runs on the offscreen platform; no pixel/screenshot assertions
- **Known failure**: `EditorAPI.set_language()` is documented in `editor-model.md` but absent from the facade
- **Manual verification needed**: Minimap rendering, syntax highlighting visuals, theme appearance

## Failure Reproduction
To reproduce failures from this run:
```bash
./tests/run_tests.sh --suite editor
```

Or directly with pytest:
```bash
QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/editor_test/ -p no:cacheprovider -q
```
