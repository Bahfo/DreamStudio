# Architecture — DreamStudio IDE

> **Purpose**: explain how the pieces fit together, which direction dependencies flow, what the public interfaces are, and how data moves at runtime.
> **Audience**: an agent that must modify the IDE without breaking it.

---

## 1. Architectural Style

DreamStudio is a **layered, event-driven desktop application** in the classic Qt sense, with three deliberate departures from stock Qt:

1. **A unified import hub.** `editor/__init__.py` re-exports the stdlib subset and PyQt6 via star-imports; nearly every module begins with `from editor import *`. This is the project's central convention — *not* an accident to be cleaned up.
2. **A mixin-based main window.** `DreamStudio` composes behaviour through `MenusAPI` and `EditorAPI` mixins rather than inheritance chains.
3. **A manifest-driven plugin system.** Language intelligence is loaded from `plugin.json` manifests at runtime, not wired at import time.

**Two-process topology.** The IDE runs as one process; Python whole-document analysis runs in a **second process** (`analysis_server.py`, frozen as `DreamStudioAnalysisServer`). See §7.

---

## 2. Dependency Direction (the layering rule)

```
                        ┌──────────────────────────┐
                        │  startup.py  (entry)     │
                        └────────────┬─────────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │  bootstrap/  (kernel)    │   no static import of editor.*
                        └────────────┬─────────────┘
                                     │  (dynamic importlib only)
                        ┌────────────▼─────────────┐
                        │  ui_build.py (window)    │
                        │  + editor/api/* mixins   │
                        └────────────┬─────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
┌───────▼────────┐        ┌──────────▼─────────┐        ┌─────────▼─────────┐
│ editor/base/   │        │ editor/workspace_  │        │ editor/api/       │
│ shell chrome   │        │ container.py       │        │ vertical_menus_   │
└────────────────┘        │  (hero assembly)   │        │ api.py            │
                          └──────────┬─────────┘        └───────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
┌───────▼─────────┐      ┌───────────▼──────────┐     ┌────────▼─────────┐
│ editor/Ironica/ │      │ editor/utils/        │     │ editor/terminal/ │
│ (code editor)   │      │ (panels & utilities) │     │ editor/debugger/ │
└───────┬─────────┘      └──────────────────────┘     │ editor/analysis/ │
        │                                             └──────────────────┘
┌───────▼──────────────────────────────┐
│ editor/Ironica/plugins/  (providers) │
│  → third-party libs (jedi, libclang) │
└──────────────────────────────────────┘
```

**Rules that follow from this shape:**

| Rule | Enforcement |
|---|---|
| `bootstrap/` must not statically import `editor/` | `bootstrap/phases.py:18-40` uses `importlib.import_module` inside `_get_notification_manager()` specifically to avoid a static `bootstrap → editor` dependency. |
| `editor/` must not import `bootstrap/` at module scope | `editor/api/editor_api.py:340-345` reaches the `ResourceManager` through the `ServiceRegistry` injected into the window, never by importing `bootstrap.resources`. |
| Third-party libraries are imported **lazily inside functions** wherever the import is expensive or optional | e.g. `editor/utils/git_control/git_control.py:9` imports `git` at module scope (cheap), but `libclang`/`jedi` are imported inside plugin factories. |
| `editor/api/*` may import from any `editor/*` package; nothing may import from `editor/api/*` except `ui_build.py` | Keeps the mixins leaf-most. |

---

## 3. Component Responsibilities

### 3.1 `bootstrap/` — Startup Kernel

| Component | Responsibility | Does NOT |
|---|---|---|
| `BootstrapManager` (`manager.py:46`) | Orchestrate the phase pipeline, convert exceptions into `StartupResult`, own the retry path. | Touch widgets. |
| `ServiceRegistry` (`registry.py:9`) | Lazy/eager service container keyed by string name (`"config"`, `"theme_content"`, `"resource_manager"`, `"workspace"`, `"main_window"`, `"app"`, `"base_dir"`, `"config_service"`). | Know about services' types. |
| `ConfigurationService` (`config.py:40`) | Load/validate/migrate/repair `.configs/config.json` (schema v2). | Write to `~/.dreamstudio`. |
| `ResourceManager` (`resources.py:37`) | Load themes, resolve icon paths, verify asset dirs, rewrite QSS `url()` for frozen builds. | Cache-bust across themes. |
| `SplashController` (`splash.py:154`) | Show the branded splash with fade-in and a minimum visible duration. | Block startup. |
| `RecoveryWindow` (`recovery.py:34`) | Render a crash screen when a fatal `StartupError` occurs. | Retry by itself — it emits a request that `BootstrapManager._retry()` (line 183) handles. |

### 3.2 `ui_build.py` — The Main Window

`DreamStudio(MenusAPI, EditorAPI, QMainWindow)` is the **only** top-level window.

| Concern | Where |
|---|---|
| Widget tree assembly | `setup_layout()` (line 51) → `_build_main_layout` / `_build_title_bar` / `_build_hero` / `_build_status_bar` |
| Theme application | `EditorAPI._apply_theme_content` (`editor/api/editor_api.py:216`) |
| Menus | `MenusAPI` (`editor/api/menus_api.py`) |
| Panel toggles | `EditorAPI._toggle_*` (`editor/api/editor_api.py:43-90`) |
| Run/debug commands | `EditorAPI._run_current_file`, `_debug_current_file`, `_stop_debug`, … |
| Outline sync | `_wire_outline_panel` (line 175) + 600 ms debounce timer |
| Workspace fan-out | `_set_initial_workspace()` (line 109) — pushes the workspace root into every panel that accepts one |

The window owns exactly one signal: `ui_ready = pyqtSignal()` (line 22), emitted after the window is revealed (`startup.py:80`).

### 3.3 `editor/workspace_container.py` — Hero Assembly

`WorkspaceContainer` (line 28) is the **panel registry**. It:
- builds the splitter tree (`_main_vertical_splitter` → `_top_horizontal_splitter` → left / center / right),
- instantiates every side panel (`_populate_panels()`, line 296),
- registers each panel with `VerticalMenusAPI` (registration table, lines 81-148),
- routes `problemActivated` → `_goto_problem` (line 165),
- remembers user splitter widths across minimize/restore (`_restore_user_sizes`, line 249).

### 3.4 `editor/Ironica/` — The Code Editor

| Layer | Class | Responsibility |
|---|---|---|
| Widget | `CodeEditor(QsciScintilla)` (`code_editor.py:26`) | The Scintilla surface: lexing, folding, diagnostics painting, minimap, hover, breakpoints, binary/ELF mode. |
| Facade | `EditorAPI` (`api.py:13`) | A **per-tab** facade over one `CodeEditor`. Menu commands call this, never the raw widget. |
| Container | `DreamTabbedEditor(QDreamTabEditor)` (`tab_editor.py:28`) | Tab lifecycle: open/close/save/reorder, dirty markers, per-tab provider wiring. |
| Shell | `EditorContainer` (`ui_build.py:44`) | `QStackedWidget` of `QuickStartMenu` (0 tabs) vs `DreamTabbedEditor` (≥1 tab). |
| Registry | `LanguageRegistry` (`language_engine.py:225`) | Maps file extensions → language config + lexer + provider. |

**Key architectural decision**: `EditorContainer.current_editor()` (`ui_build.py:87`) returns `EditorAPI` only when the current widget is a `MiniMapHostWidget`; the minimap host *wraps* the `CodeEditor`, and `EditorAPI` unwraps it. All editor commands therefore go through one stable interface regardless of whether the minimap is enabled.

### 3.5 `editor/Ironica/plugins/` — Language Intelligence

```
registration.py ──discovers──▶ plugin.json / provider.py
       │                              │
       │                        create_provider()
       ▼                              ▼
LanguageRegistry.register_language(json_path, provider)
       │
       ├──▶ LanguageLexer (QsciLexerCustom)      syntax highlighting
       ├──▶ BaseLanguageProvider subclass        IDE services
       ├──▶ register_parser(lang, provider.get_outline)  → outline backend
       └──▶ register_snippet_path(lang, snippets_path)
```

**The provider contract** (`editor/Ironica/language_engine.py:166`, `BaseLanguageProvider`):

*Abstract (must implement):*
- `get_hover_hint(text, line, col)` (line 170)
- `get_definition_location(text, line, col)` (line 175)
- `format_source(source_code)` (line 182)

*Optional capabilities (default no-op / `False`):*
`get_hover_display` (186), `get_declaration_location` (190), `get_implementation_location` (197), `find_references` (204), `find_usages` (211), `get_counterpart_file` (218), `present_navigation_results` (222), `get_semantic_highlights` (235), `has_folding` (240), `get_fold_regions` (244), `has_diagnostics` (248), `create_diagnostic_manager` (252), `has_outline` (257), `get_outline` (261), `post_fold_setup` (265).

*Optional duck-typed flags (read via `getattr`):*
| Flag | Set by | Meaning |
|---|---|---|
| `wants_file_path` | `cpp/provider.py:32` | Provider accepts `file_path=` kwarg — changes the call shape in `analysis_worker.py:71-79`. |
| `remote_analysis` | `python/provider.py:214` | Whole-document analysis runs in the out-of-process server. |
| `remote_kind` | `python/provider.py:216` | Expected response tag. |
| `slash_snippets_only` | `cpp/provider.py:29` | Restrict slash-command snippets. |
| `cpp_member_triggers` | `cpp/provider.py:30` | Enable `.`/`->` member completion. |
| `suppress_token_fallback` | `cpp/provider.py:31` | Disable token-based fallback completion. |

### 3.6 `editor/analysis/` — Diagnostics

```
walker.analyze_source (built-in AST)  ─┐
ruff_provider.RuffProvider (optional)  ─┼─▶ providers.merge_problems ─▶ Problem objects
pyright_provider.BasedPyrightProvider  ─┘            │
                                                       ▼
                                          DiagnosticStore (bucketed)
                                                       │
                                     ┌─────────────────┴──────────────────┐
                                     ▼                                    ▼
                              ProblemsWidget                       editor squiggles
```

**Bucket model** (`editor/analysis/diagnostic_store.py`):
- `disk_builtin` — the AST walker's output for a file on disk.
- `disk_external:<source>` — Ruff / Pyright workspace scans.
- `live:<source>` — diagnostics for an **unsaved** buffer.

**Merge policy** (`problems_for(path)`, line 263):
- Buffer **dirty** → show **live only** (stale on-disk results must not fight the buffer).
- Buffer **clean** → show live + builtin disk + all external disk buckets.

### 3.7 `editor/debugger/`, `editor/terminal/` — Runtime

- `RunMenuController` resolves an interpreter (`python_resolver.resolve_project_python`), builds an argv (`ConfigRun.build_command`), and opens a **terminal session** (`TerminalWorkspace.open_command_session`, `terminal_workspace.py:376`) — it never spawns the process itself.
- `ShellEmulator` (`terminal/Emulator/emulator.py:355`) owns one PTY (`UnixPty` / `WinPty`) plus a daemon `PtyReader` thread. Output is coalesced by a 15 ms GUI-thread timer.
- `ProblemsWidget` drives four `QThread` workers (`_IndexThread`, `_BatchThread`, `_LiveParseThread`, `_WorkspaceProviderThread`) and marshals results back through Qt signals.

---

## 4. Key Interfaces & Public Entry Points

### 4.1 `ServiceRegistry` keys (the bootstrap contract)

| Key | Registered in | Type |
|---|---|---|
| `"config_service"` | `phases.py:121` | `ConfigurationService` |
| `"resource_manager"` | `phases.py:122` | `ResourceManager` |
| `"config"` | `phases.py:211` | `dict` |
| `"theme_content"` | `phases.py:265` | `str` (QSS) |
| `"base_dir"` | `phases.py:273` | `str` |
| `"app"` | `phases.py:274` | `QApplication` |
| `"workspace"` | `phases.py:280` | `WorkspaceService` |
| `"main_window"` | `phases.py:433` | `DreamStudio` |

### 4.2 `WorkspaceService` (`editor/utils/solution/workspace_service.py:29`)

| Member | Line | Purpose |
|---|---|---|
| `workspace_changed = pyqtSignal(str)` | 32 | Emitted when the active solution changes. |
| `attach_window(window)` | 42 | Binds the service to the main window. |
| `open_workspace(path)` | 66 | Public entry point used by the bootstrap phase and the File menu. |
| `reset_workspace(path)` | 76 | Re-points every subsystem at a new root. |
| `_repoint_panels(hero, path)` | 155 | Re-points explorer, source control, TODO search, properties, server explorer. |
| `_defer_problems_analysis(window, path)` | 194 | Defers a workspace re-analysis to the next event-loop turn. |
| `_start_cpp_index(path, gen)` | 205 | Kicks the C++ symbol indexer. |

### 4.3 `TabEditor` public surface (`editor/Ironica/tab_editor.py`)

`add_new_tab(widget, title)` (354) · `add_new_editor(...)` (466) · `add_binary_editor(...)` (384) · `diffed_tab(...)` (361) · `open_file()` (796) · `open_file_by_path(path)` (816) · `open_file_at_line(path, line)` (844) · `get_editor_for_path(path)` (867) · `save_current_file()` (919) · `save_current_file_as()` (940) · `save_all_files()` (973) · `close_editor(index)` (691) · `close_tab()` (785) · `set_language(lang)` (890) · `set_language_for_file(path)` (897) · `open_new_workspace(path)` (903) · `_make_file_readonly()` (1033) · `open_free_trial_tab()` (603) · `open_welcome_window()` (617).

### 4.4 `EditorAPI` (per-tab facade, `editor/Ironica/api.py:13`)

Every menu command in `editor/api/menus_api.py` calls one of these. The full list of *editor* operations the UI can trigger:

`cut` · `copy` · `copy_as_plain_text` · `paste` · `delete` · `undo` · `redo` · `select_all` · `select_none` · `indent` · `unindent` · `format_code` · `comment_line` · `comment` · `uncomment_line` · `uncomment` · `duplicate_line` · `duplicate_selection` · `goto_definition` · `goto_declaration` · `goto_implementation` · `goto_usage` · `goto_reference` · `find_usages` · `goto_implementation_file` · `expand_current` · `expand_all` · `collapse_current` · `smart_collapse` · `collapse_includes`.

### 4.5 `ProblemsWidget` public surface (`editor/debugger/problems_widget.py:336`)

`set_problems(problems, skipped=0)` (508) · `add_problem(problem)` (519) · `clear()` (526) · `get_problems()` (553) · `problem_count()` (557) · `problem_counts()` (561) · `analyze_workspace()` (566) · `refresh()` (584) · `request_file(path)` (588) · `stop_scanning()` (603) · `expand_all()` / `collapse_all()` (630/634) · `enabled_groups()` (644) · `set_enabled_groups(groups)` (652) · `set_group_enabled(group, enabled)` (659) · `filter_by_severity(severities)` (671) · `show_group(group)` (675) · `show_all_groups()` (683) · `filter_group()` (687) · `set_underlined_groups(groups)` (714) · `set_group_underlined(group, underlined)` (720) · `underline_all_groups()` (732) · `reset_display_options()` (736) · `run_workspace_analysis(root)` (784) · `track_tabs(tabs)` (1135) · `problems_for(path)` (1387).

---

## 5. Signal & Slot Map

### 5.1 Signals declared in the shell

| Signal | Owner | File:line |
|---|---|---|
| `ui_ready` | `DreamStudio` | `ui_build.py:22` |
| `panel_visibility_changed(str, bool)` | `VerticalMenusAPI` | `editor/api/vertical_menus_api.py:10` |
| `panel_changed(str)` / `panel_close_requested(str)` | `UtilityTabManager` | `editor/utils/utils_tabmanager.py:65-66` |
| `close_requested()` | `PanelShell` | `editor/utils/panel_shell.py:7` |
| `close_requested()` | `TerminalPanel` | `editor/terminal/Emulator/terminal_ui.py:333` |
| `bootstrap_done(bool)` | `StatusBar` | `editor/base/statusBar.py:54` |
| `symbol_clicked(int)` | `TreeOutline` | `editor/utils/file_properties/tree_outline.py:34` |
| `problemActivated(object)` / `problemClicked(object)` / `countsChanged(int,int,int)` | `ProblemsWidget` | `editor/debugger/problems_widget.py:339-341` |
| `indexing_started(int)` / `indexing_progress(int,int)` / `indexing_finished()` | `ProblemsWidget` | `editor/debugger/problems_widget.py:343-345` |
| `notification_added(object)` / `notification_removed(int)` / `notifications_cleared()` | `NotificationManager` | `editor/utils/notifications/notification_manager.py:50-52` |
| `solution_selected(object)` / `prompt_cancelled()` | `SolutionStartWindow` | `editor/utils/solution/startup_window.py:42-43` |
| `workspace_changed(str)` | `WorkspaceService` | `editor/utils/solution/workspace_service.py:32` |
| `session_started()` / `session_paused(int,str)` / `session_ended()` / `session_error(str)` | `DebugSession` | `editor/debugger/python_debug.py:82-85` |
| `position_changed(int,int)` / `dirty_state_changed(bool)` / `analysis_started()` / `analysis_finished()` / `diagnostic_ticks_changed(list)` | `CodeEditor` | `editor/Ironica/code_editor.py:29-33` |
| `statuses_updated(str, dict)` | `GitStatusService` | `editor/utils/git_control/status_service.py:129` |
| `patterns_updated(list)` | `GitIgnoreService` | `editor/utils/explorer/gitignore.py:119` |
| `changed(object)` | `DiagnosticStore` | `editor/analysis/diagnostic_store.py:49` |

### 5.2 Signal wiring (who listens to what)

```
tab_editors.currentChanged ──┬─▶ _sync_menu_state          (ui_build.py:88)
                              ├─▶ _sync_outline             (ui_build.py:89)
                              └─▶ RunMenuController.refresh_state (ui_build.py:94)

vertical_menus_api.panel_visibility_changed ─┬─▶ _on_panel_visibility_changed (ui_build.py:107)
                                            └─▶ _on_outline_visibility_changed (ui_build.py:189)

editor.textChanged ─▶ _on_outline_text_changed ─▶ [600 ms QTimer] ─▶ _refresh_outline_for_current_editor

problems.countsChanged ─▶ _on_problem_counts_changed ─▶ status_bar.set_problem_counts
problems.problemActivated ─▶ WorkspaceContainer._goto_problem ─▶ tabs.open_file_at_line
problems.indexing_* ─▶ IndexingCoordinator.start/advance/finish

editor.dirty_state_changed ─┬─▶ tabBar().mark_dirty(i, is_dirty)
                             ├─▶ DiagnosticStore.mark_dirty(path)
                             └─▶ GitStatusService.request_scan("editor:dirty_true")

notification_manager.notification_added ─▶ NotificationsPanel._on_notification_added
git_status_service.statuses_updated ─▶ ExplorerFilterProxy.apply_vcs_index
gitignore_service.patterns_updated ─▶ ExplorerFilterProxy.apply_gitignore_patterns

solution_start_window.solution_selected ─▶ phase_solution_prompt._complete_selection
solution_start_window.prompt_cancelled ─▶ QEventLoop.quit
```

### 5.3 Threading map

| Work | Mechanism | Thread |
|---|---|---|
| Python whole-doc highlight/fold | `AnalysisProcess` subprocess (`analysis_bridge.py:137`) | separate **process** |
| Python diagnostics / completion | `threading.Thread` workers (`plugins/python/jedi_worker.py:110`, `:366`) | daemon thread → Qt signal |
| C++ completion | `_CppCompletionWorker` (`plugins/cpp/autocompletion/completion.py:38`) | daemon thread → Qt signal |
| C++ workspace index | `CppIndexer(QObject)` (`plugins/cpp/intellisense/index.py:105`) | worker |
| Workspace AST scan | `_IndexThread` / `_BatchThread` (`problems_widget.py:180`, `:205`) | `QThread` |
| Live buffer parse | `_LiveParseThread` (`problems_widget.py:239`) | `QThread` |
| External providers (Ruff/Pyright) | `_WorkspaceProviderThread` (`problems_widget.py:308`) | `QThread` |
| Terminal PTY reads | `PtyReader` (`terminal/Emulator/emulator.py:277`) | daemon thread → Qt signal |
| Git status scan | `_ScanWorker` (`git_control/status_service.py:26`) | worker |
| **C++ navigation (go-to-definition, references)** | **synchronous clang parse** | **GUI thread (blocking)** |

---

## 6. Data Flow

### 6.1 Startup

```
startup.py:main()
 └─ QApplication(Fusion, AA_ShareOpenGLContexts)
 └─ SplashController().show()
 └─ BootstrapManager(base_dir, project_dir).run(splash)
     └─ phase 1..10 (bootstrap/phases.py)
         └─ phase 7 → SolutionStartWindow in a nested QEventLoop
             └─ user picks / creates a solution
                 └─ ctx.workspace_path, ctx.pending_scaffold
         └─ phase 8 → DreamStudio(registry, current_workspace) — hidden + disabled
             └─ WorkspaceService.attach_window + open_workspace(path)
     └─ StartupResult
 └─ _reveal_result(result, splash)
     └─ QTimer.singleShot(0):
         ├─ splash.close()
         ├─ window.setEnabled(True); window.showMaximized()
         └─ window.ui_ready.emit()
             └─ _on_ui_ready → problems.run_workspace_analysis(root)
                            → get_cpp_indexer().run(root)
     └─ (if scaffold) QTimer.singleShot(0) → ScaffoldController.run_blocking()
```

### 6.2 Opening a file

```
explorer.tree_view.doubleClicked
 └─ WorkspaceContainer / ui_build._on_explorer_double_click
     └─ proxy.mapToSource(index) → base_model.filePath(index)
         └─ tabs.open_file_by_path(path)
             ├─ if a tab already holds that path → select it
             └─ else:
                 ├─ code_editor = CodeEditor(language=..., file_path=path)
                 │   └─ load_from_file → utf-8 → utf-8-sig → latin-1 fallback
                 │                   → setReadOnly if file mode lacks write bits
                 ├─ provider = LanguageRegistry.get_provider(lang)
                 ├─ provider.create_diagnostic_manager(editor, file_path, parent)
                 ├─ provider.create_completion_manager(editor, file_path, parent)
                 └─ tabBar().mark_dirty / rebuild_dirty_indices
```

### 6.3 Typing → diagnostics

```
keystroke
 └─ CodeEditor.textChanged
     ├─ _on_text_changed → _is_dirty = True; dirty_state_changed.emit(True)
     │   └─ GitStatusService.request_scan("editor:dirty_true")
     ├─ _handle_text_modification
     ├─ completion_profile.mark(self, "hl-sched") → [300 ms adaptive] → _apply_semantic_indicators
     └─ [if provider.has_folding()] → [500 ms] → _recompute_folds

ProblemsWidget._on_buffer_changed (via editor.textChanged)
 └─ store.note_buffer_change(path) + store.mark_dirty(path)
 └─ _schedule_live_reparse()
     └─ _LiveParseThread → analyze_buffer_fast (AST + Ruff)
         └─ live_done signal → store.set_live_results(path, revision, problems)
             └─ store.changed → ProblemsWidget._on_store_changed
                 └─ _paint_editor(editor, problems)
                     ├─ set_diagnostic_ranges(...)   ← squiggles
                     ├─ set_deemphasized_ranges(...) ← unused (dimmed, not squiggled)
                     └─ set_diagnostic_labels(...)
```

### 6.4 Theme switch

```
EditorAPI._set_theme_by_name(name)
 └─ ResourceManager.load_theme(name)          # cached per path; falls back to dark.qss
     └─ _apply_theme_content(qss)
         ├─ _inject_font_family(qss, configured_family)
         ├─ self.setStyleSheet(qss)           # cascades to all children
         ├─ _qss_bg  ← QSS "QMainWindow, QWidget" → background-color   (default #1E1E1E)
         ├─ _qss_fg  ← QSS "QMainWindow, QWidget" → color               (default #CCCCCC)
         ├─ _qss_sel ← QSS "UtilityTabBar::tab:selected" → background-color
         ├─ current_theme = "dark" if lightness(bg) < 128 else "light"
         ├─ _apply_custom_theme() → hero_window.set_theme(bg, fg, sel) + terminal_window.set_theme(...)
         └─ _retheme_editors() → RethemeEngine.apply_current(self)
                                  → per-editor retheme() → palette from editor/Ironica/themes/<name>.json
```

### 6.5 Workspace switch

```
WorkspaceService.open_workspace(path)
 └─ reset_workspace(path)
     ├─ _reload_solution_marker()               # .ds/solution.yaml
     ├─ _repoint_containers(hero, path)
     │   └─ _repoint_panels(hero, path)
     │       ├─ _source_control.set_workspace(path)
     │       ├─ _solution_explorer.set_workspace(path)
     │       ├─ _todo_search.set_base_dir(path)
     │       ├─ _properties_explorer.set_workspace(path)
     │       └─ _server_explorer.set_workspace(path)
     ├─ _defer_problems_analysis(window, path)  → QTimer.singleShot(0) → run_workspace_analysis
     ├─ _start_cpp_index(path)                  → CppIndexer.run(root)
     └─ workspace_changed.emit(path)
```

---

## 7. The Two-Process Analysis Subsystem

```
┌─ IDE process ────────────────────┐        ┌─ Analysis server process ────┐
│ AnalysisProcessManager           │        │ analysis_server.py            │
│  set_active(owner_id) / release  │        │  reads framed payloads       │
│  request(owner_id, payload)      │        │  from stdin, writes to stdout│
│        │                         │        │                              │
│        ▼                         │        │                              │
│ AnalysisProcess ─── stdin/stdout ┼────────┼─▶ (length-prefixed pickle)    │
│  _FRAME_HEADER = struct("<Q")   │        │                              │
│  _MAX_FRAME_BYTES = 20_000_000   │        │                              │
│  _REQUEST_TIMEOUT_S = 15.0       │        │                              │
│  spill_large_strings()          │        │                              │
└─────────────────────────────────┘        └──────────────────────────────┘
```

- **Focus routing**: `AnalysisProcessManager.set_active(owner_id)` marks the focused editor as the only one allowed to submit. Non-focused editors get `None` back immediately (`analysis_bridge.py`).
- **Pipe locking**: access is guarded by `_pipe_lock` **with a timeout**, so a stuck server raises `AnalysisProcessError("analysis subprocess busy (lock timeout)")` instead of deadlocking the GUI.
- **Large payloads**: strings over ~333 KB are spilled to `<tempdir>/dreamstudio_analysis/` and rehydrated on the other side (`editor/analysis/wire.py`).
- **Shutdown**: `shutdown()` sends a zero-length frame, waits 5 s, then kills — on a dedicated `analysis-server-reaper` thread.
- **Frozen builds**: the server ships as a separate EXE (`DreamStudioAnalysisServer`); in dev it runs as `python editor/Ironica/analysis_server.py`.

---

## 8. Plugin Loading Detail

```
registration.register_all_languages()
 ├─ load_plugins_config()                    # ~/.dreamstudio/plugins/plugins.json
 │    ├─ missing/corrupt → regenerate from disk discovery
 │    └─ merge: discovery is authoritative; only `enabled` is taken from the file
 ├─ _plugin_roots()                          # DS_PLUGIN_PATH → ~/.dreamstudio/... → bundled
 ├─ for each root: _plugin_directories()     # dirs containing plugin.json OR provider.py
 ├─ _manifest_language_spec()  / _legacy_language_spec()
 ├─ _scan_keywords()                         # editor/Ironica/keywords/*.json → keywords-only langs
 ├─ _select_plugins()                        # dependency order, cycle detection, version gate
 └─ _register_one(spec)
     ├─ _prepare_plugin_environment()         # vendor dirs → sys.path; native_libraries → ctypes.CDLL
     ├─ _import_factory()                     # synthetic package "dreamstudio_plugin_<id>"
     ├─ create_provider()                     # zero-arg factory
     ├─ LanguageRegistry.register_language(json_path, provider)
     ├─ _register_snippets() / _register_outline_parser()
     └─ notify "<Display> Support Loaded"
```

**Two loading paths coexist.** `cpp/` and `cmake/` have a `plugin.json` and use the file-based loader. `python/` has **no** manifest and uses the legacy dotted-path loader (`editor.Ironica.plugins.python.provider.create_provider`). Both are supported; do not "fix" one by breaking the other.

---

## 9. Where the Extension Points Are

| Need | Extension point | File |
|---|---|---|
| New menu item | `menus.json` + `set_<x>` on the window | `editor/base/json/menus.json`, `editor/api/menus_api.py` |
| New bar button | `optionbar.json` / `leftbar.json` / `rightbar.json` + callback on the window | `editor/base/json/*.json` |
| New side panel | subclass `PanelShell`; register in `WorkspaceContainer` | `editor/utils/panel_shell.py`, `editor/workspace_container.py:81` |
| New bottom tab | add to `UtilsContainer._stack` | `editor/Ironica/ui_build.py:130` |
| New language | `plugin.json` + `provider.py::create_provider()` | `editor/Ironica/plugins/<lang>/` |
| New theme | `<name>.qss` + `<name>.json` + `_set_theme_<name>()` | `editor/qss/`, `editor/Ironica/themes/` |
| New diagnostic rule | extend `walker.analyze_source` | `editor/analysis/walker.py` |
| New startup phase | `BootstrapManager.add_phase(name, fn, after=...)` | `bootstrap/manager.py:77` |
| New project template | `manifests/projects/<name>.yaml` | `manifests/projects/` |
| New reusable widget | `editor/widgets/Q<Name>.py` | `editor/widgets/` |

---

## 10. Architectural Anti-Patterns Present (read before "fixing")

These are **deliberate or load-bearing**. Changing them breaks the IDE.

1. **`from editor import *` everywhere.** The hub re-export is intentional; adding a module to it is how new modules become available.
2. **String-keyed service registry.** `registry.get("theme_content")` is untyped by design — it keeps `bootstrap/` free of `editor/` imports.
3. **Two plugin loading paths.** See §8.
4. **`_toggle_lower_panel` reaching into `container._stack`** (`editor/api/editor_api.py:23`). The bottom dock has no public API yet; changing the internals of `UtilsContainer._stack` breaks the toggle.
5. **`self.hero_window._<private>` access from the mixins.** `EditorAPI` and `MenusAPI` deliberately reach into `WorkspaceContainer` privates; the window and hero are a single coupled unit.
6. **Scintilla style backgrounds cannot be alpha-blended.** The folded-import "ghost text" is rendered by matching the paper colour exactly (`SCI_STYLESETBACK`), not with transparency. See `CHANGELOG.md` (FOLD_GHOST_BG).
7. **C++ navigation is synchronous.** Making it async is a real improvement but changes the contract of `provider.get_definition_location`; coordinate before touching it.
