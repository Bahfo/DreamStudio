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
