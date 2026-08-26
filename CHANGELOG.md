# Version 1.0.0: 
First release of DreamStudio. This version was implemented firstly in Tkinter and its family. 

# Version 1.0.1: 
Refactored implementation into standard PyQt-6 Framework.

# Version 1.1.0: 
Major Refactoring to take the standard form of DreamStudio required. 

#### Changes in Fix
#### (FOLD_GHOST_BG)
- `_setup_folding_display_text()` now applies the theme paper colour as the background of `STYLE_FOLDDISPLAYTEXT` via `SCI_STYLESETBACK`, removing the white box behind folded import ghost text.
- Added `CodeEditor._apply_folding_display_colors()`; `retheme()` calls it so ghost text stays blended with the paper after every theme switch.

#### Notes: Scintilla style backgrounds do not support alpha, so matching the paper colour is the correct way to render the label transparently.

#### (PORTS_TAB_EMPTY)
- Ports tab gained a "Service Name" column resolved through `socket.getservbyport` with safe fallback.
- `psutil.net_connections` failures (`AccessDenied`) no longer blank the table; the widget falls back to parsing `ss -tulnpH`.
- Only processes owning sockets are listed; search now matches ports, services, names and PIDs; process names are guarded against `None`; status filter combo is functional.

#### Notes: Verified live: port owners list with populated Port Number and Service Name cells.

#### (AUTOCOMPLETE_FIX)
- Providers (analysis server, jedi adapter, jedi fallback) now insert jedi's full name instead of its suffix (`c.complete`), fixing "imp"+Enter producing "impt"/"importt"/blank.
- `_insert_completion` recomputes word anchors from the live document at commit time, making commits immune to stale async results.
- Debounce reduced to a single 40 ms stage (was stacked 120 ms + 150 ms); while the popup is open every keystroke re-filters cached items synchronously for instant feedback.
- `_coerce_items` discards suffix-style insert payloads defensively.

#### Notes: Tests added in tests/test_completion_insert.py covering commit correctness, stale-anchor safety and cache filtering.

#### (PORTS_SYSTEM_MONITOR)
- Extracted socket discovery into shared `editor/utils/tools/port_info.py` (`fetch_pid_to_ports`, `service_name`).
- Ports tab defaults to **Listening only** sockets, so listed ports/PIDs match `ss -tlnp` ground truth instead of surfacing ephemeral outbound ports that looked like wrong attributions; a checkbox toggles full socket view.
- Repaired the previously broken `SystemMonitor` widget: implemented the missing `_apply_tab_styling()` and `_apply_table_styling()` methods (instantiation raised `AttributeError`).
- Embedded the SystemMonitor utility inside the Ports tab as a lazy-created "System Monitor" inner tab.
- Wired SystemMonitor's dead "Internet" column to display each process's listening ports with resolved service names.
- Ports table now sources CPU/RAM/IO through one `process_iter` call, removing the stale PID cache.

#### Notes: Live-verified rows against `/proc` and `ss -tlnpH`; only real PIDs owning real listeners are shown.

#### Changes in Fix - (ISLANDS_DARK_THEME)
- Added `editor/qss/islands_dark.qss`: full UI stylesheet adapting the JetBrains IntelliJ IDEA "Islands Dark" look — dark island surfaces (`#191A1C`) floating on a lighter canvas (`#2B2D30`, meeting JetBrains' 1.20:1 island/canvas contrast guideline), raised popups/menus (`#33353B`), editor-attached popups (`#27282B`), azure accent (`#3871E1`) and soft blue selection (`#233558`); borderless islands per the original design.
- Added `editor/Ironica/themes/islands_dark.json`: syntax palette taken from the authentic `IslandSchemeDark.xml` editor scheme — keywords `#CF8E6D`, strings `#6AAB73`, numbers/builtins `#2AACB8`, comments `#7A7E85`, function declarations `#56A8F5`, decorators `#B3AE60`, exceptions `#F75464`.
- Registered "Islands Dark" in the Change Theme menu (`editor/base/json/optionbar.json`) with a matching `_set_theme_islands_dark()` API method in `editor/api/editor_api.py`.

#### Notes: Theme satisfies all shipped contracts — minimap background equals editor paper, editor scrollbar track equals paper, `UtilityTabBar::tab:selected` feeds the runtime selection colour (`#233558`), and both theme engines plus ResourceManager discover it automatically.

Date of Change: 08/26/2026
