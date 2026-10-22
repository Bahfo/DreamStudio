# UI Layout — DreamStudio IDE

> **Purpose**: the widget tree, who owns what, how to add a panel/button/menu/theme, and the rules that keep the chrome consistent.

---

## 1. The Widget Tree

```
DreamStudio (QMainWindow, frameless)                        ui_build.py:19
├── central_widget (QWidget)
│   └── main_layout (QVBoxLayout, margins 0, spacing 0)
│       ├── [0] title_bar     DreamStudioTitleBar (QWidget)  editor/base/titleBar.py:11
│       ├── [1] options_menu  OptionsMenu (QFrame)           editor/base/optionsBar.py:12
│       ├── body_layout (QHBoxLayout, margins 0, spacing 0)
│       │   ├── left_sidebar   VerticalSidebar (QFrame)      editor/base/verticalBar.py:6
│       │   ├── hero_window    WorkspaceContainer (QWidget)  editor/workspace_container.py:28
│       │   └── right_sidebar  VerticalSidebar (QFrame)
│       └── [2] status_bar    StatusBar (QFrame)              editor/base/statusBar.py:53
└── (no QMainWindow docks, menus, or toolbars — everything is custom)
```

> The window is `Qt.WindowType.FramelessWindowHint` (`ui_build.py:32`). The custom title bar **is** the window chrome: it implements `mousePressEvent` / `mouseMoveEvent` / `mouseReleaseEvent` for dragging and `mouseDoubleClickEvent` for maximize.

---

## 2. `WorkspaceContainer` — the Hero

`editor/workspace_container.py:28`. This is the panel registry and the splitter owner.

```
WorkspaceContainer
└── _base_layout (QHBoxLayout)
    └── _main_vertical_splitter (QSplitter, Vertical)
        ├── [0] _top_horizontal_splitter (QSplitter, Horizontal)
        │   ├── [0] _left_utils_manager   (UtilityTabManager)   min width 250
        │   ├── [1] _text_editor_center   (EditorContainer)     min width 300, stretch 1
        │   └── [2] _right_utils_manager  (UtilityTabManager)   min width 250
        └── [1] _lower_widget (UtilsContainer)
```

### 2.1 Panel registration table (`workspace_container.py:81-148`)

| Panel id | Widget | Side | Splitter idx | Default width | Default state |
|---|---|---|---|---|---|
| `solution_explorer` | `SolutionExplorer` (`editor/utils/explorer/explorer.py`) | left | 0 | 220 | **visible** (activated at line 162) |
| `source_control` | `GitVersionControl` (`editor/utils/git_control/source_control.py`) | left | 0 | 220 | hidden |
| `file_outline` | `TreeOutline` (`editor/utils/file_properties/tree_outline.py`) | left | 0 | 220 | hidden |
| `properties` | `PropertiesExplorer` (`editor/utils/properties/properties.py`) | right | 2 | 220 | **visible** (activated at line 163) |
| `todo_search` | `TODOSearch` (`editor/utils/tools/todo_search.py`) | right | 2 | 220 | hidden |
| `server_explorer` | `ServerExplorer` (`editor/utils/server_explorer/server_explorer.py`) | right | 2 | 220 | hidden |
| `notifications` | `NotificationsPanel` (`editor/utils/notifications/notifications_panel.py`) | right | 2 | 220 | hidden |
| `ether_ai` | `EtherAI` (`editor/utils/etherAI/etherAI.py`) | right | 2 | 450 | hidden |

Registration is done with `VerticalMenusAPI.register_panel(panel_id, widget, manager, side, splitter=..., splitter_index=..., default_width=...)` (`editor/api/vertical_menus_api.py`).

### 2.2 `UtilityTabManager` — the side stacks

`editor/utils/utils_tabmanager.py`. Each side has **one** `UtilityTabManager` holding a stack of panels as tabs. It emits:

- `panel_changed(str)` — the active panel on that side changed
- `panel_close_requested(str)` — the user closed a panel tab

On close, `WorkspaceContainer` deactivates the panel through the API (`workspace_container.py:150-153`).

### 2.3 `EditorContainer` — the center

`editor/Ironica/ui_build.py:44`. A `QStackedWidget` with two pages:

```
EditorContainer
└── _stack (QStackedWidget)
    ├── [0] QuickStartMenu   (editor/base/user/quickStartMenu.py)  ← shown when 0 tabs
    └── [1] DreamTabbedEditor (editor/Ironica/tab_editor.py:28)    ← shown when ≥1 tab
```

`_sync_view()` (`ui_build.py:71`) flips between them based on `tab count`. `self.methods` is a thin adapter (`_EditorMethods`) exposing `open_new_tab`, `open_file`, `save_current`, `save_all`, `current_editor` to the toolbar.

### 2.4 `UtilsContainer` — the bottom dock

`editor/Ironica/ui_build.py:121`.

```
UtilsContainer
└── _stack (QStackedWidget)
    ├── [0] terminal_window  TerminalPanel      (editor/terminal/api.py → Emulator/terminal_ui.py:332)
    └── [1] problems_window  ProblemsWidget     (editor/debugger/problems_widget.py:336)
```

> **Load-bearing coupling:** `EditorAPI._toggle_lower_panel` (`editor/api/editor_api.py:23`) reaches directly into `container._stack` to switch between the terminal and the Problems panel. There is no public API for this. If you restructure `UtilsContainer._stack`, the toggle silently breaks.

`TerminalPanel.close_requested` is wired to `UtilsContainer._hide_show_terminal`, which hides the whole lower widget and collapses the vertical splitter to `[1, 0]`.

---

## 3. The Bars

### 3.1 Title bar — `DreamStudioTitleBar` (`editor/base/titleBar.py:11`)

- Loads the menu structure from `editor/base/json/menus.json` via `load_menus_from_json` (line 157) → `setup_menus` (166) → `_build_menu_items` (179).
- Window controls: minimize / maximize / close, built by `_build_control_button` (149).
- Drag handling: `mousePressEvent` (377) / `mouseMoveEvent` (383) / `mouseReleaseEvent` (403) with a `QEventFilter` (422) installed on the application.
- Gradient painting: `paintEvent` (428) + `_title_bar_base_color` (444) + `_title_bar_gradient_end` (473).
- **Action state sync**: `_update_menu_state(has_tabs)` (227) → `refresh_action_states()` (236) → `_editor_action_flags()` (248) enables/disables menu items based on the active editor. `_bind_selection_tracking` (302) listens for selection changes so copy/cut enable correctly.

### 3.2 Options bar (toolbar) — `OptionsMenu` (`editor/base/optionsBar.py:12`)

Built from `editor/base/json/optionbar.json`. Supports these entry ids:

| `id` | Meaning | Extra keys |
|---|---|---|
| `btn` | Push button | `icon_path`, `tooltip`, `size`, `icon_size`, `text`, `callback` |
| `sep` | Separator | — |
| `menu` | Dropdown button | `text`, `icon_path`, `size`, `options[]` (each with `text`, `icon_path`, `callback`) |
| `stretch` | Expanding spacer | — |
| `frame` | Empty frame | — |

`callback` is a **string**: the name of a method on the main window (`"_toggle_file_explorer"`, `"_run_current_file"`, …). A `callback` of `false` means "not wired yet".

### 3.3 Left / right sidebars — `VerticalSidebar` (`editor/base/verticalBar.py:6`)

Same JSON schema as the options bar, but vertical. Files: `editor/base/json/leftbar.json`, `editor/base/json/rightbar.json`.

Left bar buttons (top → bottom):

| Button | Callback | Target panel |
|---|---|---|
| Solution Explorer | `_toggle_file_explorer` | `solution_explorer` |
| Search Files | `_toggle_search_widget` | (bottom dock / search) |
| Version Control | `_toggle_git_source_control` | `source_control` |
| Outline | `_toggle_outline` | `file_outline` |
| *(stretch)* | — | — |
| Toggle Terminal | `_toggle_terminal` | bottom dock |
| Python Interpreter Shell | `_toggle_python_console` | `terminal/PythonConsole` |
| Settings | `false` | not wired |

Right bar buttons: **Toggle Properties** (`_toggle_properties`), **TODOs Search** (`_toggle_todo_search`).

### 3.4 Status bar — `StatusBar` (`editor/base/statusBar.py:53`)

| Region | API |
|---|---|
| Bootstrap progress | `set_bootstrap_status(step, message)` (209), `set_bootstrap_finished(success)` (224), `show_bootstrap_details()` (244), `clear_bootstrap_log()` (262), `bootstrap_done(bool)` signal (54) |
| Problem counters | `set_problem_counts(errors, warnings, checks)` (427) |
| Diagnostics menu | `build_diagnostics_menu` (350), `_set_group_shown` (392), `_set_group_underlined` (397), `_reset_display_options` (422) |
| Workspace / git | `set_workspace(directory)` (446), `get_branch()` (455), `get_repo_name()` (473), `show_branches_menu()` (489), `handle_branch_switch(branch)` (542) |
| Attachments | `attach_problems_panel(panel)` (276), `attach_cpp_indexer(indexer)` (298) |
| Debug styling | `set_debug_background()` (265), `reset_background()` (272) |

---

## 4. Menus — `editor/base/json/menus.json`

Top-level keys are menu names: **File, Edit, View, Tools, Code, Run, Marketplace, Help**.

Each entry:

```json
{ "text": "Save Current File", "icon": "assets/menus/save.png", "action": "set_save_current_file" }
```

- `null` entries are **separators**.
- The action key here is **`action`** (not `callback` as in the bars) and maps to a `set_<name>` method on the window.
- Counts: File 19, Edit 18, View 9, Tools 27, Code 26, Run 20, Marketplace 8, Help 6.

> The `action` vs `callback` naming split is a known inconsistency — keep using whichever the file you are editing already uses.

---

## 5. Theming

### 5.1 Two-layer theme system

| Layer | Files | Governs |
|---|---|---|
| **Shell QSS** | `editor/qss/<theme>.qss` | The IDE chrome: window, bars, panels, menus, status bar. |
| **Editor palette JSON** | `editor/Ironica/themes/<theme>.json` | Scintilla syntax colors for the code editor. |

Both layers must exist for a theme to work. The 14 shipped themes are:

`coffee_dark`, `coffee_light`, `dark`, `dark_hc`, `davy`, `light`, `light_hc`, `material_dark`, `material_light`, `monokai`, `moses`, `solarized_dark`, `solarized_light`, `tokyonight`

Plus shell-only stylesheets: `startup_dark.qss`, `startup_light.qss`, `create_dialog.qss`.

### 5.2 Applying a theme

```
EditorAPI._set_theme_by_name(name)
 └─ ResourceManager.load_theme(name)        # cached; falls back to dark.qss
     └─ _apply_theme_content(qss)
         ├─ _inject_font_family(qss, configured_family)
         ├─ self.setStyleSheet(qss)
         ├─ extract tokens: _qss_bg, _qss_fg, _qss_sel
         ├─ current_theme = "dark" if lightness(bg) < 128 else "light"
         ├─ _apply_custom_theme() → hero.set_theme(bg, fg, sel) + terminal.set_theme(...)
         └─ _retheme_editors() → RethemeEngine.apply_current(window)
```

### 5.3 Theme token extraction

The QSS is parsed for the first `background-color` / `color` under `QMainWindow, QWidget` and under `UtilityTabBar::tab:selected`:

| Token | Source | Default |
|---|---|---|
| `_qss_bg` | `QMainWindow, QWidget { background-color }` | `#1E1E1E` |
| `_qss_fg` | `QMainWindow, QWidget { color }` | `#CCCCCC` |
| `_qss_sel` | `UtilityTabBar::tab:selected { background-color }` | — |

If you add a new QSS theme, keep these selectors present, otherwise the terminal and selection colors will not follow the theme.

### 5.4 Editor palette schema (`editor/Ironica/themes/<name>.json`)

```json
{
  "theme": "dark",
  "name": "Dark",
  "palette": {
    "KEYWORD_COLOR": "#C586C0",
    "BUILTIN_COLOR": "#E06B96",
    "DEFINITION_COLOR": "#DCDCAA",
    "CLASS_COLOR": "#4EC9B0",
    "STRING_COLOR": "#CE9178",
    "NUMBER_COLOR": "#B5CEA8",
    "COMMENT_COLOR": "#898989",
    "DECORATOR_COLOR": "#D7BA7D",
    "ADDITIONAL_COLOR": "#569CD6",
    "OPERATOR_COLOR": "#D4D4D4",
    "BRACKET_COLOR": "#FFD700",
    "BRACKET2_COLOR": "#C678DD",
    "BRACKET3_COLOR": "#61AFEF",
    "EXCEPTION_COLOR": "#FF6B6B",
    "IMPORT_COLOR": "#82AAFF",
    "VARIABLE_COLOR": "#9CDCFE",
    "HEADER_COLOR": "#82AAFF",
    "PREPROC_COLOR": "#D7BA7D",
    "ERROR_COLOR": "#F14C4C",
    "WARNING_COLOR": "#FCC700",
    "CHECK_COLOR": "#C586C0",
    "TYPO_COLOR": "#3794FF",
    "INFO_COLOR": "#4EC9B0"
  }
}
```

All 23 keys are required — a missing key means the token falls back to a hard-coded default.

### 5.5 Runtime theming engine

`editor/Ironica/retheme.py`:

| Symbol | Purpose |
|---|---|
| `theme_palette(theme_name)` | Load and cache a theme JSON palette. |
| `RethemeEngine.current_theme(window)` | Resolve the active theme from the window. |
| `RethemeEngine.apply_current(window)` | Re-apply to every open editor. |
| `RethemeEngine._iter_editors(window)` | Walk the widget tree and find `CodeEditor` instances. |

---

## 6. How to Add UI Elements

### 6.1 A new toolbar button

1. Add an entry to `editor/base/json/optionbar.json` (or `leftbar.json` / `rightbar.json`).
2. Implement the method on the window (or in `EditorAPI` / `MenusAPI`), named exactly as the `callback` string.
3. Icons live under `assets/system/` (chrome) or `assets/menus/` (menu items).

### 6.2 A new menu item

1. Add an entry to `editor/base/json/menus.json` under the right top-level key, using `"action": "set_<name>"`.
2. Implement `set_<name>` on the window (usually in `editor/api/menus_api.py`).
3. If it should be state-dependent, extend `_editor_action_flags()` in `editor/base/titleBar.py:248`.

### 6.3 A new side panel

1. Subclass `PanelShell` (`editor/utils/panel_shell.py`) and emit `close_requested` on close.
2. Instantiate it in `WorkspaceContainer._populate_panels()` (`workspace_container.py:296`).
3. Register it in the table at `workspace_container.py:81-148` with a unique `panel_id`.
4. Add a toggle method (`_toggle_<panel>`) on the window and wire it into a bar JSON.

### 6.4 A new bottom-dock tab

1. Create the widget.
2. Add it to `UtilsContainer._stack` (`editor/Ironica/ui_build.py:130-137`).
3. Update `EditorAPI._toggle_lower_panel` if it needs a dedicated switch.

### 6.5 A new theme

1. `editor/qss/<name>.qss` — copy an existing theme and adjust the colors. **Keep the `QMainWindow, QWidget` and `UtilityTabBar::tab:selected` selectors.**
2. `editor/Ironica/themes/<name>.json` — copy an existing palette.
3. Add `_set_theme_<name>()` to `EditorAPI`.
4. Add a `Change Theme` entry in `editor/base/json/optionbar.json`.

---

## 7. QSS Conventions

- Style sheets are **global** (`QMainWindow.setStyleSheet`) and cascade to every child. Prefer setting a property on a specific widget class over a global `QPushButton` rule when you only want one widget affected.
- Widgets that need custom painting (title bar, tab bar, status bar, explorer tree) paint in `paintEvent` and read the theme colors from the palette, **not** from hard-coded hex values.
- Icons are resolved through `ResourceManager`, which also rewrites `url()` references for the frozen build (`sys._MEIPASS`).
- `editor/Ironica/inspector/binding.py` and other native-backed widgets need explicit background colors because QSS does not affect native child windows.

---

## 8. Responsive Behaviour

| Concern | Mechanism |
|---|---|
| Sidebar width | `_left_target_width` / `_right_target_width` = 235 (`workspace_container.py:36-37`); the actual widths are restored from user settings via `_restore_user_sizes` (249). |
| Minimum sizes | left/right ≥ 250 px, editor ≥ 300 px (`workspace_container.py:56-58`). |
| Splitter persistence | `_top_horizontal_splitter.splitterMoved` → `_on_splitter_moved` (76) saves sizes; they are restored when the window is minimized and restored. |
| Panel visibility | `VerticalMenusAPI` keeps the authoritative state; the splitter sizes are set to `[1, 0]` / `[0, 1]` when a side is hidden. |
| Editor zoom | `CodeEditor.set_font_size` / `DreamTabbedEditor.set_font_size` (319) with `Ctrl+`/`Ctrl-`; `set_editor_font_by_name` (326). |

---

## 9. Common UI Pitfalls

| Pitfall | Consequence | Prevention |
|---|---|---|
| Calling a widget method from a worker thread | Random crashes | Emit a signal; connect it on the GUI thread. |
| `setStyleSheet` on an individual widget after the global theme is applied | The global theme no longer cascades correctly | Route everything through `_apply_theme_content`. |
| Adding a QSS theme without the token selectors | Terminal and selection colors stay dark | Keep `QMainWindow, QWidget` + `UtilityTabBar::tab:selected`. |
| Adding a theme JSON with a missing palette key | Silent fallback to the default color | Copy an existing theme file wholesale. |
| Renaming a bar `callback` string | The button silently does nothing | The bar resolves the method by `getattr` — verify the name matches exactly. |
| Using `"callback"` in `menus.json` (instead of `"action"`) | The menu entry is ignored | Match the file's existing convention. |
| Reordering `UtilsContainer._stack` | The terminal/problems toggle breaks | Keep the terminal at index 0 and problems at index 1. |
| Forgetting to un-hide `_lower_widget` after a workspace change | The bottom dock stays collapsed | `_hide_show_terminal` manages the splitter sizes explicitly. |
