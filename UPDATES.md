## Changes on 3/8/2026
### Additions
- (ADD_001) Created `.github/ISSUE_TEMPLATE.md` with structured sections for Bug Reports and Feature Requests; documented 10 known bugs from the `editor/` module with severity, file, line numbers, and descriptions
- (ADD_002) Added `editor/utils/explorer/collapsable_menu.py` with `ExplorerOptionsMenu` class and `SortMode` enum; added "Sort by" submenu with five sorting strategies, "Show Hidden Files" toggle, "Copy Solution Path" action, `...` button; updated `ExplorerFilterProxy` with `set_sort_mode()`/`sort_mode()` and `lessThan()` for all five modes; wired through `SolutionExplorer._setup_options_menu()`
- (ADD_003) Dynamic font loading system: auto-discovers `.ttf`/`.otf`/`.woff`/`.woff2` from `fonts/` recursively; added `Fonts.available_families()`, `ui_families()`, `ensure_font()`, `make_font()`; fixed font application in `_apply_theme_content()` and `set_global_font()`; added `_get_configured_font_family()` and `_inject_font_family()` helpers; updated all 11 QSS theme files and `QToolTip.py` to prefer Inter over Segoe UI
- (ADD_004) Title bar gradient applied across all 12 QSS theme files; dark/light use blue gradient (`#3C3C3C → #1B4F72` / `#E0E0E0 → #5B9BD5`), others blend from their title bar color; horizontal via `qlineargradient(x1:0, y1:0, x2:1, y2:0)`
- (ADD_005) Added `editor/Ironica/retheme.py` (`RethemeEngine`) for dynamic theme toggling; added 12 per-theme syntax palettes in `editor/Ironica/themes/*.json`; refactored `python.json` styles to symbolic colour names; `editor_colors(theme)` derives from QSS; added `CodeEditor.retheme()` + `_active_theme()`; `IronicaLexer.retheme()` re-applies styles and recolours document; wired through `EditorAPI._apply_theme_content()`; made "Search Everywhere" QLineEdit transparent in all themes

### Fixes
- (FIX_001) Fixed "Show Hidden Files" toggle by toggling `QDir.Filter.Hidden` on `QFileSystemModel`; removed redundant proxy-level filtering
- (FIX_002) Fixed title bar gradient not rendering: reverted to `background-color: qlineargradient(...)` (Qt only renders gradients on `background-color`, not `background-image`); fixed `_inject_font_family()` formatting
- (FIX_003) Reworked title bar gradient to paint in Python via `paintEvent()` with `QLinearGradient`; added `_title_bar_base_color()` and `_title_bar_gradient_end()` for automatic per-theme gradient endpoints; verified across 8 themes
- (FIX_004) Anchored dark/light gradient left colour to sidebar (`#1C1C1C`/`#F3F3F3`); updated blue endpoints to `#0048BC`/`#006FCD`; `_title_bar_base_color()` extracts from `QFrame#VerticalSidebar`
- (FIX_005) Fixed white viewport behind lexer: `IronicaLexer.retheme()` now sets `setDefaultPaper(bg)`/`setDefaultColor(fg)`; fixed white boxes behind tokens via explicit `setPaper(bg, style)` across all indices; fixed stale syntax overlays after theme switch; added 12 tests in `test_retheme.py`
- (FIX_006) Fixed fold-margin and minimap colours not following theme switches: added `FoldManager.retheme(bg)` and `VirtualMinimap.retheme()`; fixed variable/class tokens too light on white themes; added `"variable"` style entry to all 12 palettes; 3 new tests (15 total)
- (FIX_007) Replaced blocky fold-margin markers with VS Code-style chevron arrows (`FoldManager._arrow_pixmap()`); fixed chevron geometry (up/down orientation); replaced box/corner tail markers with `VerticalLine`; darkened light-mode syntax palettes for contrast; 2 new tests (17 total)

### Notes:
Bugs documented: BUG-001 through BUG-010. Explorer module has no tests yet. Font runtime change via `window.set_global_font("Font Name")`. QSS `background-color` is the only reliable way to render gradients in this Qt build. Full suite: 298 passed (3 pre-existing plugin failures remain).


## Changes on 4/8/2026

### Additions
- (ADD_006) Wired fold display-text APIs into Python plugin: collapsed import blocks render gray `(... +N imports)` labels; added `CodeEditor._setup_folding_display_text()` and `set_custom_import_fold_text()`; fixed `SCI_SETDEFAULTFOLDDISPLAYTEXT` constant (2723→2722); added 7 tests in `test_folding.py`; 305 passed
- (ADD_007) Added unified cross-platform process monitor at `editor/debugger/monitor/` (merged nt/posix into single codebase with `#ifdef` blocks); `ProcessMonitor` class snapshots memory/CPU/disk/state per PID; `Processor` class reads CPU vendor/brand/cores/frequency; `SystemMonitor` reads memory/uptime; `main.cpp` accepts PID and outputs JSON to stdout; `CMakeLists.txt` + `Makefile` for builds
- (ADD_008) Rewrote `system.h`/`system.cpp` from Linux-only stubs to cross-platform: `SystemInfo` struct (total/available memory, uptime, OS name); NT uses `GlobalMemoryStatusEx`+`GetTickCount64`, Linux uses `/proc/meminfo`+`/proc/uptime`; integrated into `main.cpp` JSON output with `"system"` section

### Fixes
- (FIX_008) Fixed semantic overlay tokens keeping previous theme's colours after switch: added `invalidate_cache()`/`invalidate_semantic_cache()`; fixed first-editor theme detection fallback; darkened definition/class/import/variable colours across light themes; fixed minimap painting default palette on new files; made fold-indicator arrow smaller/smoother (12×12, 4× supersampled); 351 tests passed

### Notes:
Process monitor built as `DreamStudioProcessManager`. Port-based IPC with the Python IDE not yet implemented. Verified: JSON output includes `"system"` block with correct memory and uptime values. Full suite: 351 passed (3 pre-existing plugin failures remain).

- (ADD_009) Added `editor/debugger/tests/` test suite for `std_pipe.py` and the C++ monitor binary: 20 tests covering `handle_metrics` parsing (6 unit tests), `launch_monitor` subprocess lifecycle (6 mocked tests), C++ binary validation (5 integration tests including multi-snapshot, invalid PID, no-args usage), `launch_monitor` integration with real binary, and PyQt6 dummy-app integration (widget receives monitor data, error dialog for missing binary)
- (FIX_009) Fixed `std_pipe.py` JSON buffering bug: replaced `line.strip() == "}"` check with brace-depth tracking — the old check matched indented `}` lines (e.g. `"  }"`) too early, causing incomplete JSON parse failures; also fixed `json.load(buffer)` → `json.loads(buffer)` (load expects file-like, loads accepts string)
---

## Changes on 7/8/2026

### Additions
- (ADD_010) Added go-to-definition navigation on double-click of a search result in `FindReplace`: double-clicking a match opens the file and jumps to the exact line via `DreamTabbedEditor.open_file_at_line()`; filepath and line number stored as `UserRole` data on each `QListWidgetItem`
- (ADD_011) Added clear (X) button to `FindReplace` popup: cancels running search worker, clears all input fields (search, replace, include, exclude), clears results list, resets tip label, and hides the results panel
- (ADD_012) Redesigned `QListWidget` in `FindReplace` with IntelliJ-style appearance: disabled horizontal scroll bar, dark background (`#2B2B2B`), blue selection highlight (`#214283`), hover state (`#333333`), uniform item sizes, min-height 120px / max-height 320px for vertical expansion

### Fixes
- (FIX_010) Fixed `FindReplace` goto navigation: changed `self.window()` to `self._parent` because `self.window()` returns the popup itself (top-level `Popup` window), not the main window with `tab_editors`
- (FIX_011) Fixed `DEFAULT_IGNORED_DIRS` in `search_engine.py`: removed glob pattern `*.egg-info` (incompatible with `fnmatch` on directory basenames), added explicit `.egg-info` suffix check; added `.nox`, `__pypackages__`, `.ruff_cache`, `.hypothesis`, `covhtml`, `.scannerwork`

### Notes:
Navigation uses `itemDoubleClicked` signal on plain `QListWidget` (no subclass). `_SearchResultList` subclass removed. `self._parent` is the main window (EditorAPI mixin) passed during `FindReplace.__init__`.

---
## Changes on 7/8/2026 (Bug Fix)

### Fixes
- (FIX_012) Fixed `_minimap_toggle` corner widget misbehaving and losing its position on click: removed explicit parent from `QPushButton()` constructor so `setCornerWidget` can properly reparent and position the button; added `QTimer.singleShot(0, self.updateGeometry)` after visibility changes to force layout recalculation
- (FIX_013) Fixed crash on startup (`AttributeError: '_base_tab_style'`): moved `setStyleSheet(corner-widget)` call after `_base_tab_style` is defined, preventing `StyleChange` event from firing before the attribute exists

### Notes:
Root cause (FIX_012): creating the button with `self` as parent conflicted with `setCornerWidget`'s reparenting logic. Additionally, the tab widget layout was not recalculated when the corner widget's visibility changed, causing position drift.
Root cause (FIX_013): `setStyleSheet()` triggers a synchronous `StyleChange` event; when called before `_base_tab_style` was set, `changeEvent` → `_apply_tab_style` crashed.

---
## Changes on 10/8/2026

### Additions
- (ADD_013) Added `editor/api/menus_api.py` with `MenusAPI` mixin class: implements all File-menu callbacks (`set_new_file`, `set_open_file`, `set_save_current_file`, `set_save_file_as`, `set_save_all_files`, `set_save_all_and_close`, `set_close_editor`, `set_close_dreamstudio`, `set_open_settings`); stubs for `set_new_project`, `set_new_window`, `set_open_recent_project`, `set_import_configurations`, `set_export_configurations`; mixed into `DreamStudio` via `ui_build.py`
- (ADD_014) Added `UnsavedChangesDialog` to `editor/widgets/QExitDialog.py`: frameless dialog listing dirty files with Save All / Don't Save / Cancel buttons; used by `set_close_editor` for batch-close dirty check
- (ADD_015) Wired `show_welcome` action on `DreamStudioTitleBar` for Help > Welcome menu; opens `IDEStartPage` from `editor/base/user/whats_new.py` as a standalone window

### Fixes
- (FIX_014) Save menu items (`set_save_current_file`, `set_save_file_as`, `set_save_all_files`, `set_save_all_and_close`) now gracefully no-op when no editor tabs are open instead of raising errors
- (FIX_015) Close Editor (`set_close_editor`) is now a no-op when no tabs are open and prompts for unsaved changes when dirty files exist

### Notes:
`MenusAPI` is mixed into `DreamStudio` before `EditorAPI` in the MRO so menu actions resolve on `MenusAPI` first. All new functions follow the existing `getattr()` callback pattern used by `titleBar.py`. No changes to `menus.json` were needed — the existing action strings already matched the new method names.

---
## Changes on 10/8/2026 (Bug Fixes)

### Fixes
- (FIX_016) Fixed Exit menu action closing titlebar instead of app: changed `menus.json` action from `"close"` (resolves to `QWidget.close()` on titlebar) to `"set_exit"`; added `MenusAPI.set_exit()` that calls `QApplication.quit()`
- (FIX_016) Added editor-dependent menu action tracking: `DreamStudioTitleBar` now stores `QAction` references for save/close actions in `_menu_actions` dict; `_update_menu_state(has_tabs)` enables/disables them; wired via `currentChanged` signal and deferred sync after tab add/remove/close operations
- (FIX_017) Tab close X button now prompts for unsaved changes: `_on_close_requested()` checks `CodeEditor.isModified()` and shows `UnsavedChangesDialog` with the dirty file listed; Cancel aborts close, Save writes to disk then closes, Don't Save discards and closes

---
#### Changes in Fix - (FIX_018)
- Fixed segfault caused by `NotificationManager.__new__()` overriding `QObject.__new__()` — sip/shiboken C++ binding requires `QObject` construction to go through its own `__new__`
- Removed `_instance` class variable and `__new__` override from `NotificationManager`
- Moved singleton management to module-level `_instance` variable in `get_notification_manager()`
- Updated `NotificationsPanel.__init__()` to use `get_notification_manager()` instead of direct `NotificationManager()` instantiation

#### Notes:
Overriding `__new__` on any `QObject` subclass in PyQt6 causes a segfault because the sip/shiboken C++ layer manages `QObject` construction internally. Confirmed through isolated test cases that even without `pyqtSignal`, the `__new__` override alone triggers the crash. The singleton pattern must be managed outside the QObject class hierarchy.

Date of Change: 10/8/2026
---
