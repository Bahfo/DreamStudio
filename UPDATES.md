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

#### Changes in Fix - (FIX_019)
- Fixed notification panel text visibility: replaced hardcoded colors and `palette()` role references with proper theme-adaptive styling using `QApplication.palette()`
- Added theme propagation from `UtilityTabManager` to child panels — `set_theme()` now iterates stacked widgets and calls `set_theme()` on panels that support it
- Added `set_theme(bg, fg, sel)` method to `NotificationsPanel` to receive theme updates from the tab manager
- Restored left border on notification cards (4px solid colored border by notification type)
- Made all notification card text use `palette(window-text)`, `palette(text)`, `palette(mid)` with `background: transparent` for proper theme adaptation
- Changed "Clear All" button and source labels to use `palette(mid)` / `palette(highlight)` for theme-adaptive colors
- Ensured notification card background uses `palette.color(QPalette.ColorRole.Window)` for consistent bg

#### Notes:
Date of Change: 10/8/2026
---

#### Changes in Fix - (FIX_020)
- Removed notifications button from `rightbar.json` — the status bar already has a notifications button
- Wired status bar `notificationBtn.clicked` to `_toggle_notifications` in `ui_build.py`
- Fixed notification card background to use `palette(window)` role reference instead of baking in a hardcoded color at creation time — now updates dynamically on theme toggle
- Fixed card hover to use `palette(mid)` for theme-adaptive hover effect
- Changed timestamp, source label, and "Clear All" button colors to `#5B9BD5` (blue accent) so they are visually distinct and visible in both dark and light themes
- Removed unused `QApplication`/`QPalette` imports from notifications panel
- Removed unused `_bg`/`_fg` instance variables from `NotificationsPanel`

#### Notes:
The previous implementation captured `QApplication.palette().color(QPalette.ColorRole.Window).name()` at card creation time and baked it into the stylesheet string. When the theme changed, the baked-in hex value didn't update. Using `palette(window)` as a QPalette role reference in the QSS string lets Qt resolve the color dynamically at render time.

Date of Change: 10/8/2026
---

#### Changes in Refactor - (REF_001)
- Replaced hardcoded per-language registration functions with a dynamic plugin discovery system
- Added `create_provider()` factory function to `editor/Ironica/plugins/python/provider.py`
- Rewrote `editor/Ironica/plugins/registration.py`: added `_auto_discover()`, `load_plugins_config()`, `_register_one()`, `register_all_languages()`; kept `register_python_language()`/`unregister_python_language()` for test compatibility; removed `register_bash_plugin()` and `register_cmd_plugin()`
- Simplified `bootstrap/phases.py:phase_language_plugins()` from 40 lines to 12 lines — single call to `register_all_languages()`
- Plugin registry stored at `~/.dreamstudio/plugins/plugins.json`; auto-generated by scanning `keywords/*.json` + `plugins/*/provider.py` when missing or corrupt
- Adding a new language now requires only dropping a JSON file in `keywords/` (and optionally a `provider.py` in `plugins/`); no code changes needed

#### Notes:
Languages are loaded alphabetically. `plugins.json` schema: `{"version": 1, "plugins": {"<lang>": {"keywords": "<path>", "provider": "<dotted.path.create_provider>"}}}`. Provider field is optional — languages without it get syntax highlighting only.

Date of Change: 11/8/2026
---

#### Changes in Fix - (FIX_021)
- Fixed non-portable absolute paths in auto-generated `plugins.json`: `_scan_keywords()` now stores paths relative to the Ironica directory via `os.path.relpath()` instead of absolute filesystem paths

#### Changes in Refactor - (REF_002)
- Added provider capability flags to `BaseLanguageProvider`: `has_folding()`, `get_fold_regions()`, `has_diagnostics()`, `create_diagnostic_manager()` — all return safe defaults
- Implemented capability methods in `PythonLanguageProvider`: `has_folding()` returns `True`, `get_fold_regions()` delegates to `compute_fold_regions()`, `has_diagnostics()` returns `True`, `create_diagnostic_manager()` creates a `DiagnosticManager`
- Generalized `code_editor.py` hardcoded `== "python"` checks (lines 215, 230) to use `provider.has_folding()` capability flag instead of language name comparison
- Generalized `tab_editor.py` hardcoded `== "python"` diagnostic attachment (line 265) to use `provider.has_diagnostics()` and `provider.create_diagnostic_manager()` — any provider can now supply background diagnostics without editor core changes
- Added `create_provider` to `plugins/python/__init__.py` exports

#### Notes:
The three hardcoded `== "python"` checks that gated folding and diagnostics have been replaced with generic capability queries. Adding a new language plugin with folding and/or diagnostics now requires zero changes to `code_editor.py` or `tab_editor.py`. The `_import_highlight_timer` debounce now triggers for any provider that overrides `get_semantic_highlights`, not just Python.

Date of Change: 11/8/2026
---

#### Changes in Fix - (FIX_022)
- Fixed import fold ghost text `(... +N imports)` broken by REF_002 refactor: added `post_fold_setup(editor, regions)` method to `BaseLanguageProvider` (default no-op) and overrode it in `PythonLanguageProvider` to call `_apply_import_fold_text()`; `code_editor._recompute_folds()` now calls `post_fold_setup()` after pushing regions to `FoldManager`
- Fixed semantic indicator refresh only working for Python: `_on_text_changed()` now checks if the provider overrides `get_semantic_highlights` (via method identity check against `BaseLanguageProvider`) instead of hardcoding `== "python"`; any provider with semantic highlights now gets debounced refresh on text changes
- Added `BaseLanguageProvider` import to `code_editor.py` for the method identity check

Date of Change: 11/8/2026
---

#### Changes in Add - (ADD_007)
- Added `editor/Ironica/analysis_worker.py`: `_AnalysisWorker` (QThread) + `AnalysisManager` + `_AnalysisRequest` + `_AnalysisResult` + `_PROVIDER_LOCK`
- Moved semantic-highlight + fold-region computation off the UI thread; the worker runs providers (via `BaseLanguageProvider.get_semantic_highlights`/`get_fold_regions`) under a global reentrant lock and posts results back to the UI thread
- Added `analysis_started` / `analysis_finished` Qt signals and `_analysis_active` state to `CodeEditor`; `_recompute_folds()` now kicks off a debounced threaded analysis whenever the language provider overrides `get_semantic_highlights`; `_apply_results()` renders highlights + folds on the UI thread and drops stale requests
- `CodeEditor.deleteLater()` now shuts the analysis worker down cleanly before the editor is destroyed
- Wired the spinner into the status bar: `DreamTabbedEditor` connects each editor's `analysis_started`/`analysis_finished` to `StatusBar.start_analysis_spinner()`/`stop_analysis_spinner()` when a real status bar exists

#### Changes in Add - (ADD_008)
- Added `CircularProgressBar.start()`/`stop()`/`is_spinning()` to `editor/widgets/QCircularProgressBar.py` for indefinite (spin) progress mode
- Added `StatusBar.analysis_progress_container`, `analysis_spinner`, `analysis_label`, `_analysis_active_count` and reference-counted `start_analysis_spinner()`/`stop_analysis_spinner()`; the container is hidden by default so the status bar layout is unchanged when idle
- Fixed `StatusBar.__init__` crash when `master` has no `main_window` attribute (repo lookup now falls back to the configured project directory)

#### Changes in Test - (TEST_007)
- Added `editor/Ironica/tests/test_analysis_worker.py` (10 tests): `CircularProgressBar` spin start/stop and fixed size, `StatusBar` spinner show/hide + ref counting, `_AnalysisWorker._analyze` for supported/unsupported providers, `AnalysisManager` stale-result dropping, `CodeEditor` end-to-end started/finished signals + overlay/fold application, no-analysis-without-provider, and tab-editor spinner wiring (with and without a status bar)

#### Notes:
All 234 `editor/Ironica/tests` pass. The 5 `plugins/python/tests/test_semantic_highlights.py` failures (jedi version-dependent token diffs + cross-file ordering sensitivity) also fail identically on clean `main` and are unrelated. `tests/test_bootstrap.py::test_dependency_flow_no_circular` also fails on clean `main` (pre-existing).

Date of Change: 13/8/2026
---

#### Changes in Fix - (FIX_023)
- Fixed UI freeze when opening large files (e.g. a ~9000-line PyQt6 stub): fold-display-text application blocked the UI thread for ~8.7s
- Root cause: `set_custom_import_fold_text` sends Scintilla message `SCI_TOGGLEFOLDSHOWTEXT`, which toggles the fold, and the restore re-toggles it. Each toggle costs an O(document) fold recalculation when fold levels are active → O(import_regions × lines) total
- `_apply_fold_regions` now calls `provider.post_fold_setup()` (fold display text) *before* `FoldManager.set_fold_regions()` (fold levels) — Scintilla's per-line fold-display-text message is cheap when levels are not yet active (~12ms vs ~8.7s on a 7200-line buffer)
- Added `CodeEditor._fold_display_text_cache` (line → import count) so identical `set_custom_import_fold_text` calls are skipped entirely; repeated analysis applies (typing debounce, retheme, import-highlight timer) no longer re-send the message or re-toggle folds. Cache is cleared on `load_from_file`
- Applied the same display-text-before-levels ordering to `compute_folds_for_editor` in `editor/Ironica/plugins/python/folding.py`

#### Changes in Test - (TEST_008)
- Added `TestFoldDisplayTextCache` to `test_analysis_worker.py`: unchanged fold-text calls are skipped (SendScintilla call count stays flat) and `_apply_fold_regions` orders display-text before fold levels

#### Notes:
Verified end-to-end on a 5400-line buffer: `_apply_fold_regions` dropped from ~8.7s to ~13ms (repeat apply ~14ms); `load_from_file` UI-thread cost is ~3ms; first analysis (~4.4s) runs off-thread with the UI responsive and the spinner animating.

Date of Change: 13/8/2026
---

#### Changes in Fix - (FIX_024)
- Fixed the O(n²) first-analysis freeze in `editor/Ironica/plugins/python/semantic_highlights.py`: the raw token stream was rescanned from byte 0 on every AST node (`_tokenize`), making whole-document analysis cost ~nodes × document; a tokenized buffer is now built once per analysis, line numbers are precomputed once, and helper functions consume it via a token-stream pointer + per-line cursor instead of rescanning
- `_process_node` now receives a shared `TokenStream` context; helpers (`_find_next_name_after_token`, `_find_importfrom_module_span`, and the AST-walk line-skipping logic) no longer re-tokenize per node
- Removed `editor/Ironica/analysis_worker.py` (`_AnalysisWorker` QThread + `AnalysisManager`) per the no-threading directive; `CodeEditor` now runs `get_semantic_highlights` / `get_fold_regions` synchronously on the UI thread with identical results
- `_request_analysis()` is replaced by synchronous `_apply_semantic_indicators()`; `_recompute_folds()` computes folds inline. Both still guard on `_analysis_active` and emit `analysis_started` / `analysis_finished` so the status-bar spinner shows during analysis (`QApplication.processEvents()` lets the spinner paint before the synchronous work runs)
- Removed `CodeEditor._analysis_manager` and the `deleteLater()` override (no worker to shut down); `_apply_semantic_overlays` / `_apply_fold_regions` unchanged and still called on the UI thread

#### Changes in Test - (TEST_009)
- Updated `test_analysis_worker.py` to the synchronous pipeline: dropped `TestAnalysisWorker` / `TestAnalysisManager` (module removed); `TestCodeEditorAnalysisSignals` now asserts `analysis_started`/`analysis_finished` are emitted synchronously around `_apply_semantic_indicators()` and `_recompute_folds()`

#### Notes:
Verified on a real 8909-line PyQt6 stub: `get_semantic_highlights` dropped from ~18.4s to ~1.14s (16×) with byte-identical output (16697 highlights); `compute_fold_regions` ~105ms. All 10 `test_analysis_worker.py` tests pass. Full-suite diff vs clean `main`: no new failures (pre-existing failures in `test_python_plugin_integration`, `test_retheme`, `test_bootstrap`, and 3 `test_semantic_highlights` cases fail identically on `main`).

Date of Change: 13/8/2026
---

#### Changes in Add - (ADD_009)
- Re-added `editor/Ironica/analysis_worker.py` with the O(n) analysis now in place (supersedes FIX_024's threading removal): typing in large files was still blocking the UI thread because each debounced analysis ran `get_semantic_highlights` (~1.3s on a 8910-line buffer) synchronously on the UI thread
- `_AnalysisWorker` (QThread, latest-wins) + `AnalysisManager` follow the existing `jedi_worker.py` pattern: `request_analysis(text)` snapshots the provider on the UI thread, the worker computes `get_semantic_highlights` + `get_fold_regions` off-thread under a module-level `_PROVIDER_LOCK`, and results are queued back to `_apply_results` (UI thread) which drops out-of-order results via a request counter and paints overlays/folds
- `CodeEditor` re-gains `_analysis_manager`, `_request_analysis()` (with `analysis_started` / `analysis_finished` for the status-bar spinner), `_on_analysis_finished()`, and a `deleteLater()` override that shuts the worker down
- `_recompute_folds()` / `_apply_semantic_indicators()` now both delegate to `_request_analysis()`; a single worker pass computes highlights + folds, and Scintilla is only touched on the UI thread

#### Changes in Test - (TEST_010)
- Reverted `test_analysis_worker.py` to the threaded pipeline (13 tests): restored `TestAnalysisWorker._analyze` and `TestAnalysisManager` stale-result dropping; `TestCodeEditorAnalysisSignals` now waits on `analysis_finished` via `QSignalSpy.wait(5000)` and stops the debounce timers for determinism

#### Notes:
Probe on `venv/lib/python3.13/site-packages/PyQt6/QtWidgets.pyi` (467122 chars, 8910 lines): `_apply_semantic_indicators()` returns in ~3ms (was a ~1.3s UI-thread freeze) and `analysis_finished` arrives ~1.3s later with all 400 fold regions applied. Full-suite diff vs clean `main`: no new failures; all 237 `editor/Ironica/tests` pass.

Date of Change: 13/8/2026
---

#### Changes in Fix - (FIX_026)
- Fixed the remaining typing freeze: with analysis threaded, the UI thread still blocked per keystroke because `IronicaLexer.styleText` (called synchronously by QScintilla on every edit) copied the whole document and rebuilt the bracket-depth stack from byte 0 each time — ~77ms per keystroke near the end of a 467KB buffer, of which ~63ms was the O(cursor position) rescan
- `styleText` now caches the bracket-depth stack (`_bracket_cache = [position, stack]`); when the new style start is at/after the cache position (normal typing, since Scintilla restyles from the edit point), it only re-scans the segment between the cache and the new start instead of the whole prefix. An edit before the cache point (start < cache) still falls back to a correct full rebuild
- The stack scan was also rewritten from a per-character Python loop to a C-compiled `_BRACKET_REGEX` over bracket characters only (`_scan_bracket_depth`) — ~6x faster on full-prefix rebuilds with identical output
- Result on the 467KB worst case: per-keystroke `styleText` dropped from ~77ms to ~2.5ms (steady state) / ~10ms (first keystroke after jumping to a new location), i.e. well under one 60fps frame; full post-load restyle ~240ms

#### Changes in Test - (TEST_011)
- Added `editor/Ironica/tests/test_regex_lexer.py` (13 tests): `_scan_bracket_depth` segment identity (a+b == ab) across nested/unbalanced brackets and brackets inside strings/comments; cached (incremental) `styleText` producing per-character-identical styles to a cold full rebuild for split-at-half and sequential-edit scenarios; and mid-file edits correctly falling back to a full rebuild

#### Notes:
Verification probe on `QtWidgets.pyi` (467122 chars): styleText at end/90%/start = 2.5/2.7/2.4ms steady state after cache warm-up. Full-suite diff vs clean `main`: no new failures; all 250 `editor/Ironica/tests` pass (13 new). UI-thread typing isolation + threaded analysis worker both active.

Date of Change: 13/8/2026
---
