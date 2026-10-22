# Skill: Debugging

> **Purpose**: a repeatable triage procedure for DreamStudio — how to find the real cause, which traps are known, and which tools to reach for.

---

## 0. Triage Order

1. **Reproduce** headlessly (see §1). A bug you cannot reproduce is a bug you cannot fix.
2. **Localise** the layer (§2). Most DreamStudio bugs live in exactly one of five layers.
3. **Read the invariants** (`.agents/context/invariants.md`) for the layer you landed in.
4. **Find the known traps** (§5). They are documented because they were already hit.
5. **Fix at the boundary**, not at the symptom (§6).
6. **Add a regression test** (§7).

---

## 1. Reproducing Headlessly

```bash
# full suite
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests -p no:cacheprovider -q

# one file
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_xxx.py -p no:cacheprovider -q

# one test
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_xxx.py::test_name -p no:cacheprovider -q
```

`tests/conftest.py` forces `QT_QPA_PLATFORM=offscreen` and provides a session-scoped `qapp` fixture.

For interactive debugging:

```bash
# run the IDE with a breakpoint
./venv/bin/python -m pdb startup.py

# or with pdb post-mortem on an exception
./venv/bin/python -m pdb -c continue startup.py
```

> `pytest --timeout=…` is **not available** (`pytest-timeout` is not installed). Use the shell `timeout 120 pytest …` instead.

---

## 2. Which Layer Is Broken?

| Symptom | Layer | Look at |
|---|---|---|
| The IDE does not start / splash hangs | Bootstrap | `bootstrap/manager.py`, `bootstrap/phases.py` |
| The window opens but is empty / wrong theme | Shell UI | `ui_build.py`, `editor/api/editor_api.py`, `editor/qss/` |
| A panel is missing or does not toggle | Panel registry | `editor/workspace_container.py`, `editor/api/vertical_menus_api.py` |
| Wrong syntax colours | Editor theme | `editor/Ironica/themes/*.json`, `editor/Ironica/retheme.py` |
| No hover / completion / go-to-definition | Language provider | `editor/Ironica/plugins/<lang>/provider.py` |
| Wrong or missing squiggles | Diagnostics | `editor/analysis/`, `editor/debugger/problems_widget.py` |
| Terminal will not start / no output | PTY | `editor/terminal/Emulator/emulator.py` |
| Git panel empty | VCS | `editor/utils/git_control/` |
| Freezes on startup | Threading / subprocess | §5.1, §5.2 |

---

## 3. Reading the Logs

DreamStudio uses `logging` with a module-level logger:

```python
logger = logging.getLogger(__name__)
```

There is no global logging setup in the source tree — configure it yourself when debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
```

Targeted logging:

```bash
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -c "
import logging; logging.basicConfig(level=logging.DEBUG)
import startup; startup.main()
" 2>&1 | grep -E "bootstrap|editor.Ironica"
```

Useful loggers:
- `bootstrap.manager`, `bootstrap.phases` — startup pipeline
- `editor.Ironica.language_engine`, `editor.Ironica.plugins.registration` — plugin loading
- `editor.analysis.providers`, `editor.analysis.ruff_provider`, `editor.analysis.pyright_provider` — diagnostics
- `editor.Ironica.plugins.cpp.*` — C++ intelligence

> The **notification manager** (`editor/utils/notifications/notification_manager.py`) is the user-facing error channel. If a bug "does not show an error", look there first — the error may have been swallowed into a notification.

---

## 4. The Status Bar and the Problems Panel

Two built-in diagnostic surfaces:

| Surface | Shows | API |
|---|---|---|
| **Status bar** | Bootstrap log, problem counts (errors/warnings/checks), branch, indexing progress | `editor/base/statusBar.py` |
| **Problems panel** | Per-file diagnostics with groups, severity filters, squiggle toggles | `editor/debugger/problems_widget.py` |

The status bar keeps a bootstrap log with a details menu (`show_bootstrap_details`, line 244). When startup "silently fails", the failure is usually recorded there.

---

## 5. Known Traps

### 5.1 The analysis subprocess can wedge

`editor/Ironica/analysis_bridge.py` guards the pipe with a **lock timeout** and a **15 s request timeout**. Symptoms: a modal-looking hang when the editor loses/gains focus.

```bash
# is the analysis server wedged?
ps aux | grep -i analysis_server
```

Fix: kill the stray `analysis_server.py` / `DreamStudioAnalysisServer` process. The IDE restarts it on the next request.

### 5.2 Blocking the GUI thread

Symptoms: the window stops repainting, the "not responding" dialog appears.

Checklist:
- Is new work running on a `threading.Thread` or `QThread` that should be there?
- Is a `clang` parse happening on the GUI thread? (`plugins/cpp/intellisense/engine.py` — C++ navigation is currently **synchronous** by design.)
- Is a `shutil.which("ruff")` / `basedpyright` subprocess being waited on without a timeout? (`ruff_provider.py`, `pyright_provider.py` — both have timeouts.)

### 5.3 A stale `CMakeCache.txt`

```
CMake Error: The current CMakeCache.txt directory ... is different than the directory ...
```

The checked-in `hex-editor/build/` and `DreamCLI/build/` caches point at a different absolute path. Fix:

```bash
rm -rf hex-editor/build DreamCLI/build
```

### 5.4 A missing plugin is silently skipped

`registration.py` catches plugin load failures and continues. Check the log for:

```
Failed to load plugin ...
```

And verify the plugin's `plugin.json` / `provider.py` and its `create_provider()` factory.

### 5.5 Diagnostics disappear on an unsaved buffer

**By design.** `DiagnosticStore.problems_for` returns **live-only** results for a dirty buffer. If you are testing "why don't I see the workspace errors", save the file first.

### 5.6 The terminal shows nothing

The PTY reader is a daemon thread feeding a ~15 ms GUI-thread timer. If output is missing:
- check `editor/terminal/Emulator/emulator.py` for the reader thread,
- on Windows confirm `pywinpty` is installed (it is **not** in `requirements.txt`).

### 5.7 A stale import hub

`editor/__init__.py` re-exports names. If a symbol "does not exist" in one module but exists in another, check whether it is exported from the hub. Conversely, **removing** a name from the hub breaks every module that used `from editor import *`.

```bash
grep -rn "from editor import \*" --include=*.py editor | wc -l
```

### 5.8 The frozen build is missing a module

Anything imported via `importlib` (bootstrap phases, plugin factories) must be listed in `packaging/DreamStudio.spec` → `hiddenimports`. Symptom: works from source, `ModuleNotFoundError` in the packaged app.

### 5.9 Theme looks half-applied

A new QSS theme is missing the token selectors. `editor/api/editor_api.py::_apply_theme_content` parses:
- `QMainWindow, QWidget { background-color }` → `_qss_bg`
- `QMainWindow, QWidget { color }` → `_qss_fg`
- `UtilityTabBar::tab:selected { background-color }` → `_qss_sel`

Without them the terminal and selection colours stay at their defaults.

---

## 6. Fixing at the Boundary

| Symptom | Wrong fix | Right fix |
|---|---|---|
| A provider raises on an unsupported file | Swallow the exception in the provider | Return "unavailable" from the provider and let the caller degrade |
| A missing optional package breaks startup | `try/except` around the whole app | Import it lazily, inside the function that needs it |
| A panel keeps a stale workspace | Reset it in the panel's `__init__` | Re-point it in `WorkspaceService._repoint_panels` |
| The UI freezes | Increase a timeout | Move the work to a worker |
| Diagnostics do not appear | Force-paint from the widget | Fix the bucket/revision logic in `DiagnosticStore` |
| An exception escapes into the event loop | `except Exception: pass` everywhere | Handle it at the boundary and notify the user |

---

## 7. Writing a Regression Test

```python
"""
(C) COPYRIGHT 2026 Excellent TechStacks - All Rights Reserved.

Regression test for <the bug>.
"""

import os
import sys

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def test_<the behaviour that was broken>():
    """<What must hold now.>"""
    from editor.Ironica.code_editor import CodeEditor

    editor = CodeEditor()
    try:
        editor.setText("hello")
        assert editor.is_dirty() is False
    finally:
        editor.deleteLater()
```

Rules:
- Name the file `tests/test_<feature>.py`.
- Assert the **behaviour**, not the implementation.
- Use `tmp_path` for any filesystem work.
- Do not require network, a real repo, or a writable home.
- Clean up Qt widgets (`deleteLater()`), and never create a second `QApplication`.

---

## 8. Escalation Path

| Situation | Action |
|---|---|
| Bug is in the C++ provider (libclang) | `editor/Ironica/plugins/cpp/intellisense/engine.py`; check the compile database at `.ds/cpp/compile_commands.json` |
| Bug is in the native inspector | `hex-editor/src/inspector.c`; rebuild with `cmake --build hex-editor/build` |
| Bug is in the startup pipeline | `bootstrap/phases.py`; check the phase order invariant in `invariants.md` §3 |
| Bug is architectural | Stop. Do **not** restructure. Report it and propose a plan. |
| Bug needs an interface change | Stop. Interfaces are stable by policy (`AGENTS.md`). Report it and propose a plan. |

---

## 9. Debugging Checklist

- [ ] Reproduced headlessly?
- [ ] Located the layer (§2)?
- [ ] Read the invariants for that layer?
- [ ] Checked the known traps (§5)?
- [ ] Log output inspected (`logging.basicConfig(level=logging.DEBUG)`)?
- [ ] Checked the notification manager for a swallowed error?
- [ ] Checked for a stray `analysis_server.py` process?
- [ ] Fixed at the boundary, not at the symptom?
- [ ] Regression test added and passing?
- [ ] Pre-existing failures reported separately?
