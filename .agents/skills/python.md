# Skill: Python Contributions

> **Purpose**: the house style, structure, and workflow for every Python change in DreamStudio.
> **Applies to**: all `*.py` in the repository.

---

## 0. Non-Negotiables

1. **Copyright header** on every new file (`.agents/style_rules.md` §1).
2. **110-column** maximum line length — code, comments, and docstrings alike.
3. **Docstrings** on every class and every public function (`Args:` / `Returns:`).
4. **Type hints** on every signature.
5. **Trailing newline** at the end of every file.
6. **Auto-format** before hand-off.
7. **Run the tests** that cover your change and report the result, including pre-existing failures.

---

## 1. File Template

```python
"""
(C) COPYRIGHT 2026 Excellent TechStacks - All Rights Reserved.

One or two sentences describing what this file is for and why it exists.
"""

from editor import *

logger = logging.getLogger(__name__)
```

> The header format varies slightly across the tree (`(C) COPYRIGHT 2026 ...` vs `(C) COPYRIGHT - 2026 ...`). Copy the style of the **nearest sibling file**.

---

## 2. The Import Hub

Most `editor/` modules start with:

```python
from editor import *
```

That single line gives you the stdlib subset, `pathlib.Path`, `typing.*`, and all of PyQt6 (`QtCore`, `QtGui`, `QtWidgets`, `QtSvg`, `Qsci`). See `dependencies.md` §8 for the exact list.

**Rules:**
- Use the hub in `editor/` modules. Outside `editor/` (e.g. `bootstrap/`), import explicitly — `bootstrap/` must not import `editor/` at all.
- **Do not** add a name to `editor/__init__.py` for one module's benefit. Add it only if many modules need it.
- **Removing** a name from the hub can break dozens of modules at once:
  ```bash
  grep -rn "from editor import \*" --include=*.py editor | wc -l
  ```

---

## 3. Naming

| Kind | Convention | Example |
|---|---|---|
| Module / package | `snake_case` | `diagnostic_store.py` |
| Class | `PascalCase` | `DiagnosticStore` |
| Function / method | `snake_case` | `problems_for` |
| Variable / parameter | `snake_case` | `file_path` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_FRAME_BYTES` |
| Private member | leading underscore | `_is_dirty` |
| Qt signal | `snake_case` noun | `dirty_state_changed` |
| Qt slot / handler | `snake_case` verb-first | `_on_text_changed` |
| Window callback | `_<verb>_<noun>` | `_toggle_file_explorer` |
| Window action | `set_<noun>` | `set_save_current_file` |

---

## 4. Type Hints

```python
def analyze_buffer(path: str, content: str, root: Optional[str] = None) -> list[Problem]:
    """Analyze *content* as source code.

    Args:
        path: Absolute path of the buffer being analyzed.
        content: The buffer text.
        root: Optional workspace root used for context.

    Returns:
        A list of ``Problem`` objects found in the buffer.
    """
```

- Use `from typing import *` semantics via the hub (`Optional`, `Union`, `Callable`, …).
- Prefer built-in generics (`list[str]`, `dict[str, int]`) — the codebase already uses them.
- `Optional[X]` over `X | None` in files that target older syntax; both appear in the tree, match the file.

---

## 5. Docstrings

Google-style, and **required** on every class and public function:

```python
class DiagnosticStore(QObject):
    """Central store for diagnostics across the workspace.

    Attributes:
        _buckets: Mapping of bucket key to the problems it holds.
        _revision: Monotonic counter used to discard stale results.
    """

    def problems_for(self, path: str) -> list[Problem]:
        """Return the problems that apply to *path*.

        Args:
            path: Absolute path of the file.

        Returns:
            The merged problem list for the file.
        """
```

Comments: **precise and rare**. Allowed — small inline notes about tricky algorithms, `TODO:` for planned work, `NOTE:` for critical edge cases. Not allowed — narrating what the code does.

```python
# GOOD
# NOTE: Scintilla positions are byte offsets, not character indices.
byte_len = len(match.group(0).encode("utf-8"))

# BAD
# increment x by 1
x += 1
```

---

## 6. Error Handling

```python
# Feature boundary: degrade, log, and continue.
try:
    repo = Repo(path)
except Exception:
    logger.debug("Not a git repository: %s", path)
    return None
```

Rules:
- **Never** let an exception escape into the Qt event loop.
- Use `except Exception` at integration boundaries. **Never** swallow `KeyboardInterrupt` / `SystemExit`.
- Log with `logger.<level>(...)` and `%s` placeholders — never f-strings in log calls.
- Report user-visible failures through the notification manager:
  ```python
  from editor.utils.notifications.notification_manager import get_notification_manager

  get_notification_manager().add_error("Title", "Message", source="Editor")
  ```
- Never `print()` in library code.

---

## 7. Logging

```python
logger = logging.getLogger(__name__)
```

| Level | Use for |
|---|---|
| `logger.debug` | Trace-level detail (off by default) |
| `logger.info` | Significant lifecycle events (startup phases, plugin loads) |
| `logger.warning` | Degraded but recoverable (a file failed to load, a plugin was skipped) |
| `logger.error` | An operation failed and the user is affected |
| `logger.exception` | Inside an `except` block, when the traceback matters |

---

## 8. Qt Rules

```python
# Signals
value_changed = pyqtSignal(str)

# Slots
@pyqtSlot()
def _on_value_changed(self, value: str) -> None:
    """Handle the value change."""
```

- **Widgets are only touched on the GUI thread.** Workers emit signals.
- Always disconnect signals and stop threads in teardown:
  ```python
  try:
      self._editor.dirty_state_changed.disconnect()
  except (TypeError, RuntimeError):
      pass
  ```
- Never create a second `QApplication`.
- Prefer `QTimer.singleShot` over `time.sleep` for deferred work.

---

## 9. Optional Dependencies

```python
# GOOD — lazy, guarded, degrades
def _ruff_command() -> Optional[list[str]]:
    """Return the ruff argv prefix, or None when unavailable."""
    on_path = shutil.which("ruff")
    if on_path:
        return [on_path]
    if importlib.util.find_spec("ruff") is not None:
        return [sys.executable, "-m", "ruff"]
    return None
```

- Import heavy or optional packages **inside** the function.
- A missing dependency must disable a **feature**, never the IDE.
- Return a structured "unavailable" reason rather than raising.

---

## 10. Performance

- The GUI thread must never block on I/O or heavy compute.
- Debounce expensive work: the project uses **600 ms** for the outline refresh and **500 ms** for fold recomputation.
- Use the existing worker infrastructure (`ProblemsWidget`, `GitStatusService`, `AnalysisProcessManager`, `CppIndexer`) rather than adding a new thread.
- Prefer the out-of-process analysis server for whole-document Python analysis.

---

## 11. Formatting & Linting

```bash
# format the files you touched (project line length is 110, not black's 88)
./venv/bin/python -m black --line-length 110 editor/path/to/file.py

# syntax / undefined-name gate
./venv/bin/python -m ruff check editor/path/to/file.py
```

> `black` is **not** applied to the codebase as a whole. Formatting an untouched file creates diff noise. Format only what you changed.

There is no `pyproject.toml` / `setup.cfg` / `ruff.toml` in this repo, so pass options explicitly.

---

## 12. Tests

```bash
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_my_feature.py -p no:cacheprovider -q
```

```python
"""
(C) COPYRIGHT 2026 Excellent TechStacks - All Rights Reserved.

Regression test for <feature>.
"""

import os
import sys

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def test_<behaviour>():
    """<What must hold.>"""
    assert True
```

Rules:
- File name `tests/test_<feature>.py`.
- Use the session `qapp` fixture for anything touching Qt.
- Use `tmp_path` for filesystem work.
- No network, no real git server, no writes outside `tmp_path`.
- Assert behaviour, not implementation.
- Clean up widgets (`deleteLater()`).

---

## 13. Pre-Existing Failures

The repository has a known-failing baseline (24 failures + 3 collection errors). See `.agents/context/build-and-test.md` §4.3.

- Do **not** "fix" them by weakening an assertion.
- Report them as pre-existing.
- A change is green when it does not increase the failure count.

---

## 14. Pre-Commit Checklist

- [ ] Copyright header on any new file.
- [ ] ≤ 110 columns everywhere.
- [ ] Class docstring + `Args:`/`Returns:` on every public function.
- [ ] Type hints on every signature.
- [ ] `from editor import *` used correctly; no unused imports.
- [ ] No module-scope import of a heavy/optional package.
- [ ] No bare `except:`; no swallowed `KeyboardInterrupt`.
- [ ] No `print()` — use `logger`.
- [ ] Signals disconnected / threads stopped on teardown.
- [ ] No widget access from a worker thread.
- [ ] Trailing newline present; file auto-formatted.
- [ ] Tests added and the relevant subset run.
- [ ] Pre-existing failures reported, not hidden.
- [ ] `.agents/context/*.md` updated if a public interface changed.
