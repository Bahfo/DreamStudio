
---
#### Changes in Addition - (ADD_001)
- Created `.github/ISSUE_TEMPLATE.md` with structured sections for Bug Reports and Feature Requests
- Documented 10 known bugs from the `editor/` module with severity, file, line numbers, and descriptions

#### Notes:
Bugs documented: BUG-001 through BUG-010, covering critical (NameError, infinite self-reference, missing return), moderate (silent failures, unimplemented functions), and low severity (magic numbers, typos) issues.

Date of Change: 3/8/2026
---
#### Changes in Addition - (ADD_002)
- Added `editor/utils/explorer/collapsable_menu.py` with `ExplorerOptionsMenu` class and `SortMode` enum
- Added "Sort by" submenu to Solution Explorer with five sorting strategies: Extension, Alphabetical (A-Z), Alphabetical (Z-A), Last Modified, Oldest Modified
- Added "Show Hidden Files" toggleable action wired to proxy model
- Added "Copy Solution Path" action that copies workspace root to clipboard
- Added `...` button beside the status label under the search bar
- Updated `ExplorerFilterProxy` in `proxy.py` with `set_sort_mode()` and `sort_mode()` methods
- Updated `lessThan()` in proxy to support all five sort modes
- Wired all new actions through `SolutionExplorer._setup_options_menu()`

#### Notes:
No tests exist for the explorer module yet. All existing tests pass (pre-existing test_lambda_params failure unrelated).

Date of Change: 3/8/2026
---
#### Changes in Fix - (FIX_001)
- Fixed "Show Hidden Files" toggle not working by toggling `QDir.Filter.Hidden` on the `QFileSystemModel` source filter
- Removed redundant proxy-level hidden filtering of `.` and `..` (already handled by `NoDotAndDotDot`)

#### Notes:
The `QFileSystemModel.setFilter()` was missing `QDir.Filter.Hidden`, so hidden files were never supplied to the proxy model.

Date of Change: 3/8/2026
---
#### Changes in Addition - (ADD_003)
- Dynamic font loading system: fonts are now discovered and registered from the `fonts/` directory recursively at startup
- `Fonts.init()` now auto-discovers all `.ttf`/`.otf`/`.woff`/`.woff2` files instead of a hardcoded list
- Added `Fonts.available_families()` to list all registered font families
- Added `Fonts.ui_families()` to list non-monospace families for UI font selection
- Added `Fonts.ensure_font(family)` to dynamically load a font at runtime by name
- Added `Fonts.make_font(family, size, **kwargs)` generic factory for any registered font
- Fixed font application: `_apply_theme_content()` now injects the configured `font_family` from config into the QSS before applying, so the setting survives theme switches
- Fixed `set_global_font()` to re-apply the current theme with the new font (preserves colours/borders) instead of replacing the entire stylesheet
- Added `_get_configured_font_family()` and `_inject_font_family()` helpers to `EditorAPI`
- Added `_current_theme_name` tracking on `DreamStudio` so `set_global_font` can reload the correct theme
- Removed hardcoded `Fonts.inter()` stylesheet from `ui_build.py` constructor (was immediately overwritten)
- Updated all 11 QSS theme files to prefer Inter over Segoe UI in the font-family fallback chain
- Updated `QToolTip.py` commit tooltip to prefer Inter over Segoe UI

#### Notes:
To change the font at runtime, call `window.set_global_font("Font Name")`. The font must be installed on the system or present in the `fonts/` directory. The config value `editor.font_family` in `.configs/config.json` persists the choice across restarts.

Date of Change: 3/8/2026
---
#### Changes in Addition - (ADD_004)
- Title bar gradient applied across all 12 QSS theme files
- Dark and Light themes use a blue gradient: `#3C3C3C → #1B4F72` (dark) and `#E0E0E0 → #5B9BD5` (light)
- All other themes use a gradient from their current title bar color to a lighter shade of the same color
- Gradient is horizontal (left to right) via `qlineargradient(x1:0, y1:0, x2:1, y2:0)`

#### Notes:
Each theme's title bar gradient preserves the original left-side color for visual continuity while adding depth on the right.

Date of Change: 3/8/2026
---
#### Changes in Fix - (FIX_002)
- Fixed title bar gradient not rendering in any theme: reverted the broken `background-image: qlineargradient(...)` + `background-color: transparent` combo back to a single `background-color: qlineargradient(...)` declaration
- Verified via offscreen pixel rendering that `background-color` and the `background:` shorthand support `qlineargradient()` in this Qt build, while `background-image` does not render gradients
- Fixed `_inject_font_family()` formatting: now inserts `font-family` on its own indented line instead of concatenating onto the opening brace

#### Notes:
Qt's stylesheet engine in this project renders `qlineargradient()` only when assigned to `background-color` (or the `background` shorthand). Assigning it to `background-image` produced a solid/garbled fill, which is why earlier attempts failed.

Date of Change: 3/8/2026
---
#### Changes in Fix - (FIX_003)
- Reworked title bar gradient to be painted in Python instead of relying on QSS: added `paintEvent()` to `DreamStudioTitleBar` that fills the bar with a horizontal `QLinearGradient`
- Added `_title_bar_base_color()` which reads the base colour automatically from the active stylesheet's `QWidget#DreamStudioTitleBar` rule (falls back to the parent's `_qss_bg`, then the palette)
- Added `_title_bar_gradient_end()` which picks blue (`#1B4F72` dark / `#5B9BD5` light) for the built-in dark/light themes and an automatic lighter shade (blend toward white) for every other theme
- Repaints the bottom border as a darkened base colour to preserve the previous QSS `border-bottom` look
- Verified via offscreen pixel sampling across 8 themes that the gradient now renders reliably (previously invisible in the running IDE)

#### Notes:
The QSS title bar rules keep their solid `background-color` — the stylesheet is now the source of the base colour, while the gradient itself is drawn by `paintEvent`, so theme switches restyle the bar without further code.

Date of Change: 3/8/2026
---
#### Changes in Fix - (FIX_004)
- Anchored the dark/light title bar gradient's left colour to the vertical sidebar colour (`#1C1C1C` dark, `#F3F3F3` light) instead of the title bar's own QSS background
- Updated the dark/light gradient blue endpoints to `#0048BC` (dark) and `#006FCD` (light)
- `_title_bar_base_color()` now extracts the `QFrame#VerticalSidebar` background colour from the stylesheet for the dark/light themes, keeping the value automatic
- Verified via offscreen pixel sampling that the left edge matches the sidebar colour exactly and the right edge reaches the new blue endpoints

#### Notes:
Only the built-in dark and light themes use the sidebar anchor + blue endpoint; every other theme still blends from its own title bar colour toward white.

Date of Change: 3/8/2026
---
#### Changes in Addition - (ADD_005)
- Added `editor/Ironica/retheme.py`: a module-level retheme engine (`RethemeEngine`) that toggles the IDE theme dynamically and applies the matching syntax palette to every open editor
- Added `editor/Ironica/themes/*.json` — 12 per-theme syntax palettes (`dark`, `light`, `dark_hc`, `light_hc`, `tokyonight`, `monokai`, `moses`, `davy`, `coffee_dark`, `coffee_light`, `solarized_dark`, `solarized_light`) as the single source of truth for token colours
- Refactored `editor/Ironica/keywords/python.json` styles to symbolic colour names (e.g. `"keyword": "KEYWORD_COLOR"`) with an identical `"palette"` fallback dict, preserving style-index order so existing style ids stay stable
- `editor_colors(theme)` now derives base editor colours from the QSS (source of truth): `QWidget#CodeEditor` background/foreground/selection, with derived caret-line and edge colours
- Added `CodeEditor.retheme(theme_name)` + `_active_theme()` so editors recolour (paper, foreground, caret, caret line, margins, selection, edge, indent guides) and rebuild lexer colours on theme switch; `setLanguage()` resolves its config through the active theme
- `IronicaLexer.retheme()` re-applies lexer styles and updates the DEFAULT style (0) paper/foreground so the document background follows the theme even while a lexer is attached, then recolours the visible document via `SCI_COLOURISE`
- `LanguageLexer`, `highlighting_api.styles_from_config`, and the Python semantic provider now resolve symbolic colours through the theme palette
- Wired `EditorAPI._apply_theme_content()` to retheme all open editors (`_retheme_editors()`) after applying a theme, so switching themes in the IDE recolours editors live
- Made the "Search Everywhere" `QLineEdit` transparent (`DreamStudioTitleBarSearch` object name) in all 12 QSS theme files

#### Notes:
The QSS files remain the single source of truth for the base editor colours; the `themes/*.json` palettes drive token-level highlighting. `resolve_colour`/`styles_from_config` fall back to each config's inline `"palette"` so existing per-config hex styles and tests keep working. Verified offscreen: `editor_colors` returns correct per-theme values, raw style-0 follows the theme across switches, and `RethemeEngine.toggle` cycles themes. Full suite: 293 passed, only the 3 pre-existing plugin failures remain.

Date of Change: 3/8/2026
---
#### Changes in Fix - (FIX_005)
- Fixed the editor rendering with a plain white viewport whenever a lexer was attached: `IronicaLexer.retheme()` now calls `setDefaultPaper(bg)`/`setDefaultColor(fg)` on the lexer (which drive QScintilla's document background/foreground) instead of only the per-style `setPaper(c, 0)`/`setColor(c, 0)` that never reached the viewport
- Fixed white boxes behind every styled token (keyword/string/comment/number/operator/bracket): each used style's background is now explicitly set to the theme's editor background via `setPaper(bg, style)` across all style indices 0..comment-style, so tokens no longer render on QScintilla's default white
- Fixed stale syntax overlays after a theme switch: `CodeEditor.retheme()` now re-applies the semantic `INDIC_TEXTFORE` overlays after invalidating the provider cache, and syncs the module-level active theme so indicator colours match the newly applied palette
- Added `editor/Ironica/tests/test_retheme.py` (12 tests) covering `editor_colors`, `resolve_language_config`, lexer/editor background+foreground retheme, and `RethemeEngine` iteration/toggle

#### Notes:
Root cause was confirmed by offscreen pixel rendering: with a lexer attached, `QsciScintilla` paints the document using the lexer's default paper (white by default), and per-style backgrounds default to white independently of style 0. Full suite: 293 passed, only the 3 pre-existing plugin failures remain.

Date of Change: 3/8/2026
---
#### Changes in Fix - (FIX_006)
- Fixed the fold-margin colour not following theme switches: added `FoldManager.retheme(bg)` which recomputes the gutter shade (`bg.lighter(130)` dark / `bg.darker(115)` light) from the active theme and re-applies it to the fold-margin background and markers; `CodeEditor.retheme()` now calls it. Fold-margin colours were previously derived once from the widget palette at `FoldManager` construction, so they froze at the first theme
- Fixed the minimap colours not following theme switches: `VirtualMinimap` now stores its background, overlay, default-line and per-token line colours as instance attributes derived from the active theme palette via a new `_apply_theme()` helper, with a new `retheme(theme_name, bg)` entry point; `CodeEditor.retheme()` invokes it through the wrapping `MiniMapHostWidget`. The minimap previously computed its colours once in `__init__` and painted every line from a fixed palette lookup
- Fixed variable/class tokens rendering too light on white themes: variables were always falling back to the hard-coded `#9CDCFE` light-blue because python.json had no `variable` style entry; added `"variable": "VARIABLE_COLOR"` to `keywords/python.json` and a `VARIABLE_COLOR` entry to all 12 theme palettes (light themes now use a dark blue `#001080`/`#0000A0`/`#5D4A36`; dark themes keep a light blue). Darkened `CLASS_COLOR` on the pure-light themes (`light` → `#005F8B`, `coffee_light` → `#6E4A2E`) for stronger contrast
- Added 3 tests to `editor/Ironica/tests/test_retheme.py` (15 total) covering per-theme variable-colour resolution, minimap retheme, and fold-margin pixel colour across dark/light

#### Notes:
Verified offscreen that the fold gutter pixel colour changes with the theme (`#272727` dark vs `#dedede` light) and that minimap background/line colours re-derive from each theme palette. Full suite: 296 passed, only the 3 pre-existing plugin failures remain.

Date of Change: 3/8/2026
---
#### Changes in Fix - (FIX_007)
- Replaced the blocky fold-margin markers with VS Code-style chevron arrows: added `FoldManager._arrow_pixmap(color, up)` which paints a 14×14 antialiased two-line chevron (`ARROW_SIZE = 14`, 2.2px round-cap pen, 4.5px arm), and `_apply_theme_colours(e, bg)` which derives the arrow/gutter colours from the editor background (dark: arrow `#C5C5C5`, line `#808080`; light: arrow `#505050`, line `#A0A0A0`; gutter `bg.lighter(130)` dark / `bg.darker(115)` light) and defines the pixel markers via `SCI_MARKERDEFINEPIXMAP` for `SC_MARKNUM_FOLDER`/`FOLDEROPEN`/`FOLDEREND`/`FOLDEROPENMID`
- Fixed the chevron geometry to match its intent: `up=True` now renders an up-pointing chevron (collapsed `FOLDER`/`FOLDEREND` lines) and `up=False` renders a down-pointing chevron (expanded `FOLDEROPEN`/`FOLDEROPENMID` lines) — previously the flag drew the mirror image, so expanded folds pointed up and collapsed folds pointed down, opposite of the VS Code convention
- Replaced the box/corner tail markers with a single `VerticalLine` for `FOLDERSUB`/`FOLDERMIDTAIL`/`FOLDERTAIL`, removing the old `BottomLeftCorner` tail
- Darkened the light-mode syntax palettes for readable contrast on white papers: `light.json` (BUILTIN `#005F8B`, DEFINITION `#5A3E00`, NUMBER `#006B42`, COMMENT `#005F00`, DECORATOR/BRACKET2 `#8A00A8`, BRACKET3 `#006B42`, IMPORT `#005F00`), `coffee_light.json` (15 keys darkened, e.g. KEYWORD `#8A3E0F`, STRING `#6E3A05`, COMMENT `#6F6459`, VARIABLE/ADDITIONAL/IMPORT/BRACKET3 `#4A3A2A`), and `solarized_light.json` (KEYWORD/BRACKET `#6C7A00`, BUILTIN/STRING/BRACKET3 `#1C7A74`, COMMENT `#657B83`, CLASS/DECORATOR `#8A6D00`)
- Added 2 tests to `editor/Ironica/tests/test_retheme.py` (17 total): `test_fold_arrow_pixmaps` (up/down chevrons differ by apex/base orientation) and `test_fold_arrows_render` (chevron arrows paint in the fold gutter); updated `test_minimap_retheme` for the darkened `#005F00` light comment colour

#### Notes:
Verified offscreen: expanded fold headers render a down chevron and collapsed headers render an up chevron, recolouring across dark/light rethemes; light themes render the darkened tokens (keywords/comments/strings/functions). Full suite: 298 passed, only the 3 pre-existing plugin failures remain.

Date of Change: 3/8/2026
---
