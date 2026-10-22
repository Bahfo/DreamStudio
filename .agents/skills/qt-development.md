# Skill: Qt / PyQt6 Development

> **Purpose**: a repeatable playbook for adding or changing UI in DreamStudio.
> **Applies to**: `ui_build.py`, `editor/base/`, `editor/widgets/`, `editor/workspace_container.py`, `editor/api/`, `editor/Ironica/ui_build.py`, `editor/utils/panel_shell.py`.

---

## 0. Before You Touch Any UI

- [ ] Read `.agents/context/ui-layout.md` — the widget tree and the panel table.
- [ ] Read `.agents/context/invariants.md` §4 (UI Composition) and §6 (Threading).
- [ ] Decide **which layer** your change belongs to (see §1).
- [ ] Never hard-code a colour; use the theme pipeline (§7).

---

## 1. Which Layer Do I Touch?

| I want to… | Layer | File |
|---|---|---|
| Add a toolbar / sidebar button | **JSON** + callback method | `editor/base/json/*.json` |
| Add a menu item | **JSON** + `set_<name>` method | `editor/base/json/menus.json` |
| Add a side panel | **Python widget** + registration | `editor/workspace_container.py` |
| Add a bottom-dock tab | **Python widget** + stack entry | `editor/Ironica/ui_build.py` |
| Add a reusable widget | **New file** in `editor/widgets/` | `editor/widgets/Q<Name>.py` |
| Change the layout tree | **Surgical** — read `invariants.md` U4 first | `ui_build.py` / `workspace_container.py` |
| Change behaviour of an existing action | The mixin | `editor/api/editor_api.py` / `menus_api.py` |

---

## 2. The Mandatory Header and Geometry

```python
"""
(C) COPYRIGHT 2026 Excellent TechStacks - All Rights Reserved.

One or two sentences describing what this file is for.
"""

from editor import *
```

- `from editor import *` gives you `os`, `sys`, `Path`, `QWidget`, `QSplitter`, `QsciScintilla`, `logging`, `logger` conventions, etc. See `dependencies.md` §8.
- **Max line length: 110 columns.** Wrap, do not truncate.
- Every class gets a docstring describing its responsibility and main attributes.
- Every public method gets a docstring with `Args:` / `Returns:`.

---

## 3. Building a New Side Panel

### Step 1 — the widget

Subclass `PanelShell` so the close button works:

```python
from editor.utils.panel_shell import PanelShell


class MyPanel(PanelShell):
    """Panel that shows <thing>.

    Attributes:
        _model: The backing data model for this panel.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model = None
        self._build_ui()

    def _build_ui(self) -> None:
        """Create the panel's widget tree."""
        layout = QVBoxLayout(self)
        self._tree = QTreeView(self)
        layout.addWidget(self._tree)

    def set_workspace(self, root: str) -> None:
        """Point the panel at workspace *root*.

        Args:
            root: Absolute path to the workspace root.
        """
        self._model = build_model(root)
        self._tree.setModel(self._model)
```

`PanelShell` provides `close_requested = pyqtSignal()` (`editor/utils/panel_shell.py:7`).

### Step 2 — instantiate it

In `WorkspaceContainer._populate_panels()` (`editor/workspace_container.py:296`):

```python
self._my_panel = MyPanel(self)
```

### Step 3 — register it

In the table at `editor/workspace_container.py:81-148`:

```python
(
    "my_panel",
    self._my_panel,
    self._right_utils_manager,
    "right",
    2,
    220,
),
```

`panel_id` must be unique. `splitter_index` is `0` for left, `2` for right.

### Step 4 — add a toggle

On the window (`editor/api/editor_api.py`):

```python
def _toggle_my_panel(self) -> None:
    """Toggle the visibility of the My Panel side panel."""
    api = self.hero_window._vertical_menus_api
    if api.is_active("my_panel"):
        api.deactivate_panel("my_panel")
    else:
        api.activate_panel("my_panel")
```

### Step 5 — add a button

`editor/base/json/rightbar.json`:

```json
{
    "id": "btn",
    "icon_path": "assets/system/info.png",
    "tooltip": "Toggle My Panel",
    "size": [40, 40],
    "icon_size": [27, 27],
    "callback": "_toggle_my_panel"
}
```

### Step 6 — re-point it on workspace change

Add it to `WorkspaceService._repoint_panels` (`editor/utils/solution/workspace_service.py:155`):

```python
self._my_panel.set_workspace(path)
```

> **Invariant W4:** a panel that keeps a stale workspace root after a switch is a bug. Every panel with a workspace concept must be re-pointed.

---

## 4. Adding a Bottom-Dock Tab

`UtilsContainer` (`editor/Ironica/ui_build.py:121`) owns a `QStackedWidget`:

```python
self._stack = QStackedWidget(self)
self.terminal_window = TerminalPanel(self)
self.problems_window = ProblemsWidget(self)
self._stack.addWidget(self.terminal_window)   # index 0 — DO NOT REORDER
self._stack.addWidget(self.problems_window)   # index 1 — DO NOT REORDER
```

To add a third tab: append it **after** index 1 and update `EditorAPI._toggle_lower_panel` (`editor/api/editor_api.py:23`) to know about it.

> **Invariant U4:** the terminal must stay at index 0 and problems at index 1 — `EditorAPI._toggle_lower_panel` reaches into `_stack` directly.

---

## 5. Threading Rules (non-negotiable)

```python
# WRONG — touching a widget from a worker thread
def _scan(root):
    for path in walk(root):
        self._tree.addItem(path)          # crash risk

# RIGHT — compute in the worker, apply on the GUI thread
class _ScanWorker(QObject):
    finished = pyqtSignal(list)

    def __init__(self, root: str) -> None:
        super().__init__()
        self._root = root

    @pyqtSlot()
    def run(self) -> None:
        """Collect results off the GUI thread."""
        results = walk(self._root)
        self.finished.emit(results)
```

Then in the widget:

```python
self._worker = _ScanWorker(root)
self._worker.finished.connect(self._apply_results)
self._thread = QThread(self)
self._worker.moveToThread(self._thread)
self._thread.started.connect(self._worker.run)
self._thread.start()
```

Rules:
1. Never touch a widget from a worker.
2. Always `moveToThread` a `QObject` worker before starting it.
3. Always `quit()`/`wait()` the thread on teardown — otherwise the widget is destroyed while the thread still references it.
4. Prefer the existing managers (`ProblemsWidget`, `GitStatusService`, `AnalysisProcessManager`) over a new thread.

---

## 6. Signals and Cleanup

Every signal you connect must be disconnected when the owner dies, or the slot fires on a deleted C++ object.

```python
# in __init__
self._editor.dirty_state_changed.connect(self._on_dirty)

# in teardown
try:
    self._editor.dirty_state_changed.disconnect()
except (TypeError, RuntimeError):
    pass
```

The `except (TypeError, RuntimeError)` guard is the project idiom — `disconnect()` raises `RuntimeError` when the connection no longer exists.

---

## 7. Theming

### Shell (QSS)

Theme colours come from `editor/qss/<theme>.qss`, applied globally by `EditorAPI._apply_theme_content`.

- To read a theme colour in code, use the palette or the extracted tokens (`_qss_bg`, `_qss_fg`, `_qss_sel`).
- To style a widget, prefer a **scoped** QSS rule over a global one:
  ```css
  QPushButton#myButton { background-color: #2D2D30; }
  ```
  and set `self._btn.setObjectName("myButton")`.

### Editor (palette JSON)

`editor/Ironica/themes/<theme>.json` holds the 23 Scintilla colour keys. Adding a key means updating **every** theme JSON, or the token falls back to a default.

### Custom painting

```python
def paintEvent(self, event: QPaintEvent) -> None:
    """Paint the widget background using the current palette."""
    painter = QPainter(self)
    painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))
    painter.end()
```

Never hard-code `#1E1E1E`. Read from the palette.

---

## 8. Scintilla (QsciScintilla) Notes

The editor is a Scintilla widget. Important quirks:

| Topic | Rule |
|---|---|
| Units | Scintilla positions are **bytes**, not characters. Use `editor.text()` character indices for Python-level work and convert explicitly. |
| Styles | Set colours with `SetPaperColor` / `SCI_STYLESETBACK`, not with QSS. QSS does not reach Scintilla's internal painting. |
| Transparency | Scintilla style backgrounds cannot be alpha-blended. Match the paper colour exactly instead. |
| Lexer | Always call `setLanguage(lang)` (which rebuilds the lexer) before touching style indices for that language. |
| Indicators | Use high indicator numbers for user overlays; the project already uses a range of them — check `code_editor.py` before allocating a new one. |
| Folding text | `SCI_SETFOLDEXPANDEDTEXT` (UTF-8 encoded bytes). |

---

## 9. Testing UI Changes

```bash
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_titlebar_menus.py -p no:cacheprovider -q
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_ui_batching.py -p no:cacheprovider -q
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_problem_display_options.py -p no:cacheprovider -q
```

Test rules:
- Use the session-scoped `qapp` fixture from `tests/conftest.py`. **Never** create a second `QApplication`.
- Assert on **state** (`isVisible()`, `isChecked()`, model contents), not on pixels.
- Clean up widgets you create so they do not leak into the next test.

---

## 10. Checklist

- [ ] `from editor import *` at the top; no unused imports.
- [ ] Copyright header on new files.
- [ ] ≤ 110 columns.
- [ ] Class docstring + `Args:`/`Returns:` on every public method.
- [ ] Type hints on every signature.
- [ ] No hard-coded colours; theme-aware.
- [ ] No widget access from a worker thread.
- [ ] Signals disconnected on teardown; threads stopped.
- [ ] Panel registered in `WorkspaceContainer` **and** re-pointed in `WorkspaceService._repoint_panels`.
- [ ] Button/menu entry added to the right JSON with the exact callback/action name.
- [ ] Tests added under `tests/test_*.py`; the relevant subset passes.
- [ ] Pre-existing failures reported, not hidden.
