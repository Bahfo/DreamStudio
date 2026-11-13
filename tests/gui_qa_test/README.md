# GUI QA Suite (gui_qa)

## Overview
Live end-to-end quality-assurance walk of the real DreamStudio window: every widget, every service, and every code-editor feature is driven through QTest mouse/keyboard events in offscreen mode, and product bugs are reported as failing tests.

## Scope
- The real `DreamStudio` main window is built exactly the way startup phase 8 builds it (`config/phases.py::phase_main_window`): session `qapp` only, `ServiceRegistry` with `config`, `theme_content`, `resource_manager`, `base_dir`, and `WorkspaceService`, `setEnabled(True)`, `show()`, and one `ui_ready` emission after show.
- Each test class gets its own window so one crash cannot poison the next class.
- Coverage spans the shell chrome (title bar, options bar, sidebars, status bar), all registered side panels, the tab editor, the bottom dock (terminal / Problems), `menus.json` actions, find & replace, the source-control service against a real git repo in the temp workspace, every service on the registry, and the full code-editor feature surface (keys, dirty/save, zoom, breakpoints, debug markers, color swatches, occurrences, brace highlight, navigation, context menu, hover, snippets, completion stack, minimap, diagnostics ruler, folding, languages, retheme, analysis overlays).
- Every custom widget in `editor/widgets/` is built, painted, and driven through its public API.
- Adversarial combos and race probes (rapid toggles, typing while panels toggle, open/close storms, resize stress) assert consistent end states.

## Limitations (offscreen cursor)
- `QT_QPA_PLATFORM=offscreen` is forced by `tests/conftest.py`, so the operating-system pointer never moves and there are no screenshot diffs.
- Paint quality that only a person can see (repaint flicker, animation smoothness, exact pixel art) is out of scope for this suite.
- Native modal dialogs are never clicked raw; `harness.modal_guard` stubs `QFileDialog` / `QInputDialog` / `QColorDialog` getters locally per test.
- Menu popups with no offscreen geometry fall back to triggering their `QAction` directly; a missing popup geometry is not treated as a product failure.

## Rules
- Product bugs this suite finds stay as failing tests. They are not patched in the same change, and assertions are not weakened to hide them.
- No new packages; pytest-qt is not installed — the `qapp` fixture from `tests/conftest.py` is used.
- Bounded `processEvents()` loops (`harness.pump` / `pump_until`) only — never `time.sleep()`.
- App-quit actions (`set_exit`, `set_close_dreamstudio`, title-bar close) are never invoked.

## Phases
1. **Scaffolding** — `harness.py` primitives, suite `conftest.py` fixtures, window smoke tests.
2. **Shell & layout** — `test_shell_chrome.py`, `test_layout_glitches.py`.
3. **Panels, editor, dock, menus** — `test_side_panels.py`, `test_editor_interaction.py`, `test_bottom_dock.py`, `test_menus.py`.
4. **Services** — `test_services.py`, `test_search_service.py`, `test_source_control.py`, `test_explorer_flow.py`.
5. **Editor batteries** — `test_code_editor_core.py`, `test_code_editor_markers.py`, `test_code_editor_navigation.py`, `test_code_editor_completion.py`, `test_code_editor_dressing.py`.
6. **Races & widget battery** — `test_race_conditions.py`, `test_widget_battery.py`, README finalization.

## Latest Run

## Historical Runs

| Run ID | Timestamp | Verdict | Passed | Failed | Errors | Skipped | Blocked | Report |
|--------|-----------|---------|--------|--------|--------|---------|---------|--------|

## Known Product Findings
The failures below are real product defects. They are deliberately left as failing tests; the product code is **not** patched by this suite.

| Test | Area | Finding |
|------|------|---------|
| `test_menus.py::TestMenuActionContract::test_every_menu_action_exists_on_window` | Menus | 74 of 119 menu actions have no implementation on the window (66 of them fall back to `generic_callback`). |
| `test_menus.py::TestMenuActionContract::test_menu_qactions_are_connected` | Menus | Menu `QAction`s are created but left disconnected, so the menu entry does nothing when triggered. |
| `test_search_service.py::TestSearchEngine::test_glob_query` | Search | The search engine compiles glob queries and applies them to file *contents* instead of treating them as a file-path filter. |
| `test_search_service.py::TestSearchEngine::test_empty_query_returns_nothing` | Search | An empty query returns every line of every file instead of no results. |
| `test_search_service.py::TestFindReplaceWidget::test_ctrl_f_opens_popup` | Search | No `Ctrl+F` shortcut is registered anywhere in the IDE, so the find-and-replace popup cannot be opened with the keyboard. |
| `test_code_editor_core.py::TestZoomAndFonts::test_is_zoomed_reports_the_state` | Code editor | `CodeEditor.is_zoomed()` only assigns the private `_is_zoomed` flag and returns `None`, so no caller can detect a zoomed editor. |
| `test_side_panels.py::TestFileOutlinePanel::test_outline_title_is_human_readable` | Side panels | `file_outline` is missing from `VerticalMenusAPI._TITLES`, so the outline panel shows a machine key instead of a human-readable title. |
| `test_shell_chrome.py::TestOptionsBar::test_run_menu_actions_exist` | Shell chrome | The Run menu exposes `_run_and_debug_file`, which is not implemented on the window. |
| `test_shell_chrome.py::TestOptionsBar::test_find_in_file_button_opens_find_replace` | Shell chrome | The options-bar "Find in File" button calls `_toggle_nodes_editor` instead of opening find-and-replace. |
| `test_shell_chrome.py::TestSidebarToggles::test_panel_toggles_flip_visibility` | Shell chrome | The sidebar and status-bar toggles never hide an already-visible panel (`EditorAPI._toggle_panel` only ever shows). |
| `test_source_control.py::TestSourceControlPanel::test_clean_repo_reports_no_changes` | Source control | The source-control panel lists the IDE's own `.ds/` metadata as untracked "Added" files, so a clean repository is never reported as clean. |
| `test_source_control.py::TestSourceControlPanel::test_editor_edit_reaches_the_panel` | Source control | The source-control panel ignores unsaved editor buffers, so an edited-but-unsaved file never appears in the changes tree. |
| `test_widget_battery.py::TestSegmentedProgressBar::test_string_colours_are_rejected_by_the_paint_routine` | Widgets | `SegmentedProgressBar.paintEvent` hands the segment colour straight to `QPainter.fillRect`, which only accepts a `QColor`; a colour string raises a `TypeError` inside the paint event and aborts the whole IDE process. |

## Failure Reproduction
Run the whole suite:
```bash
./tests/run_tests.sh --suite gui_qa
```

Or a single module / test directly with pytest:
```bash
QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/gui_qa_test/test_menus.py -v --tb=long
QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest "tests/gui_qa_test/test_menus.py::TestMenuActionContract::test_every_menu_action_exists_on_window" -v --tb=long
```
