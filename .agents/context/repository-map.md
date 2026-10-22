# Repository Map — DreamStudio IDE

> **Purpose**: single entry point for agents/LLMs. Answers "where do I look?" before any code is written.
> **Verified against**: commit `da0eddd` (branch `main`), version 1.1.0 "Quiet Vally Release".

---

## 1. Quick Orientation

| Question | Answer |
|---|---|
| What is this? | A cross-platform IDE written in Python with PyQt6 + QScintilla. Ships its own code editor ("Ironica"), terminal, debugger, explorer, and language-intelligence plugin framework. |
| Main entry point | `startup.py` → `bootstrap/manager.py` → `ui_build.py::DreamStudio` |
| Main window class | `ui_build.py:19` — `class DreamStudio(MenusAPI, EditorAPI, QMainWindow)` |
| Code editor class | `editor/Ironica/code_editor.py:26` — `class CodeEditor(QsciScintilla)` |
| Test location | `tests/` (git-ignored — local-only working artifacts) |
| Style rules | `.agents/style_rules.md` + `.agents/style_rules.yaml` |
| Language mix | Python (IDE), C++17 (`DreamCLI/`), C17 (`hex-editor/`), QSS, JSON, YAML, HTML |

---

## 2. Top-Level Directory Map

```
DreamStudio/
├── startup.py              ← PRIMARY ENTRY POINT (PyQt6 app bootstrap)
├── ui_build.py             ← MAIN WINDOW (DreamStudio class)
├── run.sh / run.bat        ← dev launcher (creates venv, runs startup.py, purges caches)
├── clear_cache.sh / .bat   ← post-run __pycache__ / .pytest_cache purge
├── requirements.txt        ← pinned Python dependencies (60 entries)
├── AGENTS.md               ← root agent contract (this folder extends it)
│
├── .agents/                ← AGENT DOCUMENTATION (this folder)
│   ├── style_rules.md      ← mandatory coding style
│   ├── style_rules.yaml    ← agent behaviour config
│   ├── context/            ← architecture & codebase knowledge
│   └── skills/             ← task-specific playbooks
│
├── bootstrap/              ← STARTUP KERNEL (phased, service-registry based)
├── editor/                 ← THE IDE ITSELF (core, plugins, panels, widgets)
├── docs/                   ← in-app documentation pages + viewer
├── DreamCLI/               ← DreamScript C++17 engine + `dscript` CLI + DayDream UI
├── hex-editor/             ← C17 ELF inspector shared library (source)
├── native/                 ← build OUTPUT only (native/build/lib/libinspector.so)
├── node_editor/            ← node-graph canvas prototype (pure PyQt6)
├── manifests/              ← declarative menus + 8 project scaffold templates
├── packaging/              ← PyInstaller .spec + Windows .ico
├── publish/                ← prebuilt Linux bundle (git-ignored output)
├── public/                 ← GitHub Pages static site
├── assets/ fonts/ icon_src/← icons, TTF fonts, logos
├── tests/                  ← 69 pytest files (git-ignored)
├── .configs/               ← runtime config (.configs/config.json, schema v2)
├── .ds/                    ← solution marker + C++ index/PCH cache (git-ignored)
├── .github/workflows/      ← Pages deploy only (NO test CI)
├── venv/                   ← local virtualenv (git-ignored)
```

---

## 3. Entry Points

| File | Role | Key detail |
|---|---|---|
| `startup.py` | App entry | Detects `sys.frozen`/`sys._MEIPASS` → sets `_PROJECT_ROOT` and inserts into `sys.path` (lines 4-9). Parses `--project`/`--solution`/`-p` (line 12). Creates `QApplication` (Fusion style, `AA_ShareOpenGLContexts`, line 98). Shows `SplashController`, runs `BootstrapManager.run(splash)` (line 116), then `_reveal_result()` on `QTimer.singleShot(0)` (line 86) → closes splash, `showMaximized()`, emits `window.ui_ready`. |
| `ui_build.py` | Main window | `DreamStudio(MenusAPI, EditorAPI, QMainWindow)`. Frameless (`Qt.WindowType.FramelessWindowHint`, line 32). Builds title bar / options bar / sidebars / hero / status bar. |
| `run.sh` | Linux dev launcher | Creates `venv` if missing, runs `./venv/bin/python startup.py`, then `./clear_cache.sh`. |
| `run.bat` | Windows dev launcher | Same flow with `venv\Scripts\python.exe`. |
| `editor/Ironica/analysis_server_entry.py` | Subprocess entry | Second PyInstaller EXE (`DreamStudioAnalysisServer`); out-of-process analysis server for frozen builds. |
| `DreamCLI/src/main.cpp` | `dscript` executable | DreamScript REPL/driver `main()`. |
| `node_editor/preview.py` | Dev preview | Standalone `QApplication` showing `NodeBuilder`. |

---

## 4. `bootstrap/` — Startup Kernel (8 modules)

Ordered phase pipeline defined in `bootstrap/manager.py:49-60`, implemented in `bootstrap/phases.py`.

| # | Phase | Implementation | Responsibility |
|---|---|---|---|
| 1 | `application_startup` | `phases.py:90` | Configure `QApplication` metadata, set up root logging (`_configure_logging`, line 473). |
| 2 | `bootstrap_init` | `phases.py:106` | Create `ServiceRegistry`, `ConfigurationService`, `ResourceManager`, `SplashController`; register the first two. |
| 3 | `user_home_setup` | `phases.py:127` | Ensure `~/.dreamstudio/{remote,settings,plugins}` exist with default JSON. |
| 4 | `configuration` | `phases.py:205` | Load/validate/repair `.configs/config.json` → register as `"config"`. |
| 5 | `resources` | `phases.py:225` | Load theme QSS, verify asset dirs, register bundled fonts (`fonts/font_strapper.py`). |
| 6 | `core_services` | `phases.py:269` | Register `base_dir`, `app`, `WorkspaceService`. |
| 7 | `solution_prompt` | `phases.py:296` | Show `SolutionStartWindow` in a nested `QEventLoop` (`_run_start_window`, line 354). Persist choice. |
| 8 | `main_window` | `phases.py:406` | Create `DreamStudio` hidden + disabled; attach workspace. |
| 9 | `language_plugins` | `phases.py:442` | `registration.register_all_languages()`. |
| 10 | `finish` | `phases.py:460` | `processEvents`, notify "Startup Complete". |

| Module | Key API |
|---|---|
| `bootstrap/manager.py` | `BootstrapManager(base_dir, project_dir)`, `BootstrapManager.run(splash) -> StartupResult` (`manager.py:97`), `add_phase(name, fn, after=None)` (line 77). `StartupResult` dataclass at `manager.py:33`. |
| `bootstrap/registry.py` | `ServiceRegistry` — `register(name, instance)`, `register_factory(name, fn)`, `get(name)`, `has(name)`. |
| `bootstrap/config.py` | `ConfigurationService(base_dir)` — `load()`, `save()`, `get(key)`, `set(key, value)`. `CONFIG_VERSION = 2` (line 17). |
| `bootstrap/resources.py` | `ResourceManager(base_dir)` — `load_theme(name)`, `available_themes()`, `get_icon_path()`, `verify_assets()`. Rewrites relative `url(assets/...)` → absolute for frozen builds (`_rewrite_qss_urls`, line 18). |
| `bootstrap/splash.py` | `SplashController` — `show()`, `update_status(text, step)`, `close()`. 690×450, min 5 s visible, 550 ms fade-in. |
| `bootstrap/recovery.py` | `RecoveryWindow` — crash screen rendering `assets/error_crash.svg`. |

**Error taxonomy** (`bootstrap/phases.py:52-72`): `StartupError` (fatal → recovery window), `RecoverableError` (logged, pipeline continues), `SolutionPromptCancelled` (user closed the start window → clean exit).

---

## 5. `editor/` — The IDE (12 subpackages, 257 files, ~52k LOC)

### 5.1 `editor/__init__.py` — THE IMPORT HUB

`editor/__init__.py` re-exports a curated stdlib subset + PyQt6 (`QtCore`, `QtGui`, `QtWidgets`, `QtSvg`, `Qsci`) via star-imports. **Every module in `editor/` starts with `from editor import *`.** Do not remove names from this file — it is a de-facto public surface.

> Note: the QScintilla import is `from PyQt6.Qsci import *` — **not** `PyQt6.QScintilla`.

### 5.2 `editor/api/` — Public Facades (3 modules)

| Module | Class | Purpose |
|---|---|---|
| `editor/api/editor_api.py` | `EditorAPI` | Mixin: panel toggles, theme setters (`_set_theme_*`), file ops, clipboard, run/debug commands, `set_global_font`. |
| `editor/api/menus_api.py` | `MenusAPI` | Mixin: every File/Edit/View/Code menu callback (`set_new_file`, `set_undo`, `set_goto_definition`, …). |
| `editor/api/vertical_menus_api.py` | `VerticalMenusAPI(QObject)` | Panel activation manager. `panel_visibility_changed = pyqtSignal(str, bool)` (line 10). `register_panel`, `activate_panel`, `deactivate_panel`, `is_visible`. |
| `editor/api/file_search.py` | — | Extension-filtered file search used by the run menu. |

### 5.3 `editor/base/` — Shell Chrome

| Module | Class | Object name | Notes |
|---|---|---|---|
| `editor/base/titleBar.py` | `DreamStudioTitleBar(QWidget)` | `DreamStudioTitleBar` | Height 40. Loads menus from `editor/base/json/menus.json`. `_ACTION_REQUIREMENTS` map (line 35) drives menu enable/disable. Custom frameless drag in `mousePressEvent`/`mouseMoveEvent`. |
| `editor/base/optionsBar.py` | `OptionsMenu(QFrame)` | `OptionsMenu` | Height 35. Built from `editor/base/json/optionbar.json`. `_validate_config` (line 52) enforces `max_items=30`. |
| `editor/base/verticalBar.py` | `VerticalSidebar(QFrame)` | `VerticalSidebar` | Width 45. Built from `leftbar.json` / `rightbar.json`. |
| `editor/base/statusBar.py` | `StatusBar(QFrame)` | `StatusBar` | Height 25. Warning/error/check buttons, `lines_and_cols`, `EOL`, indexing progress, branch menu. |
| `editor/base/menus.py` | — | `MenuBar` | Shared menu-bar styling helper. |
| `editor/base/user/` | `QuickStartMenu`, `ShortCutLabel`, `FreeTrialWindow`, `IDEStartPage`, `GradientBanner` | — | Onboarding surfaces. |
| `editor/base/json/` | `menus.json`, `optionbar.json`, `leftbar.json`, `rightbar.json` | — | Declarative manifests — see `ui-layout.md`. |

### 5.4 `editor/Ironica/` — The Code Editor Engine (16 modules + 7 subpackages)

| Module | Key class / function | Line |
|---|---|---|
| `code_editor.py` | `CodeEditor(QsciScintilla)` | 26 |
| `tab_editor.py` | `DreamTabbedEditor(QDreamTabEditor)` | 28 |
| `api.py` | `EditorAPI` (per-tab facade over one `CodeEditor`) | 13 |
| `language_engine.py` | `LanguageRegistry`, `BaseLanguageProvider`, `LanguageLexer` | 270 / 166 |
| `retheme.py` | `RethemeEngine`, `theme_palette`, `diagnostic_palette`, `editor_colors` | 289 |
| `regex.py` | `IronicaLexer(QsciLexerCustom)` | 101 |
| `ui_build.py` | `EditorContainer`, `UtilsContainer` | 44 / 121 |
| `debounce.py` | `adaptive_delay_for_editor` | — |
| `completion_profile.py` | `mark()` cost profiling for adaptive debounce | — |
| `right_click.py` | `RightClickMenu` | — |
| `process_manager.py` | `AnalysisProcessManager` (singleton `process_manager`) | 12 |
| `analysis_bridge.py` | `AnalysisProcess` — subprocess client, length-prefixed pickle frames | 137 |
| `analysis_server.py` | IPC server loop | — |
| `analysis_server_entry.py` | Frozen-build subprocess entry | — |
| `analysis_worker.py` | `_AnalysisWorker(threading.Thread)` — latest-wins analysis | 29 |
| `inspector/binding.py` | `Inspector` — ctypes bridge to `libinspector.so` | 139 |
| `inspector/hex_view.py` | `generate_hex_dump`, `is_elf_file` | 12 / 61 |
| `inspector/popup.py` | `ElfInfoPopup(QFrame)` | 15 |
| `utils/` | `completion.py`, `minimap.py`, `folding.py`, `diagnostics_ruler.py`, `documentation_flayout.py`, `highlighting_api.py`, `hover_controller.py`, `debug_frame.py` | — |
| `keywords/` | `bash.json`, `cmd.json`, `css.json`, `html.json`, `python.json`, `sql.json` | — |
| `snippets/` | `html.json`, `python.json` | — |
| `themes/` | 15 palette JSON files (`dark.json`, `light.json`, `tokyonight.json`, …) | — |
| `plugins/` | Language plugin framework — see §5.5 | — |

### 5.5 `editor/Ironica/plugins/` — Language Plugin Framework

Three tiers: **discovery** (`registration.py`) → **runtime registry** (`language_engine.py::LanguageRegistry`) → **provider packages** (`python/`, `cpp/`, `cmake/`).

| Path | Contents |
|---|---|
| `plugins/registration.py` | `register_all_languages()`, `_plugin_roots()`, `_manifest_language_spec()`, `_legacy_language_spec()`, `_scan_keywords()`, `_select_plugins()` (dependency ordering + cycle detection + version gate), `load_plugins_config()`. |
| `plugins/python/` | Jedi-based provider: `provider.py` (`create_provider()` at 485), `jedi_adapter.py`, `jedi_worker.py`, `cache.py`, `folding.py`, `outline_parser.py`, `semantic_highlights.py`, `domain_models.py`, `interfaces.py`. **No `plugin.json` — legacy path.** |
| `plugins/cpp/` | libclang-based provider (largest subsystem): `provider.py` (`create_provider()` at 370), `models.py`, `intellisense/` (`engine.py`, `index.py`, `pch.py`, `args.py`, `sysindex.py`, `headers.py`), `navigation/` (10 modules: `clang_support.py`, `definition.py`, `references.py`, `symbols.py`, `project.py`, `session.py`, `results.py`, `models.py`, `headers.py`, `__init__.py`), `autocompletion/` (8 modules), `highlighting/tokens.py`, `folding/regions.py`, `errors_detection/` (reserved package). |
| `plugins/cmake/` | `cmake/scanner.py` (`scan_project`), `cmake/generator.py` (`generate`), `provider.py` (`create_provider()` at 100). |

Plugin roots, in precedence order (`registration.py:41`):
1. `$DS_PLUGIN_PATH` (os.pathsep-separated)
2. `~/.dreamstudio/plugins/packages`
3. `<repo>/editor/Ironica/plugins` (bundled)

Persistence: `~/.dreamstudio/plugins/plugins.json` — the saved file owns **only** the `enabled` flag; all other fields are re-derived from disk discovery on every start.

### 5.6 `editor/analysis/` — Workspace Diagnostics

| Module | Key API |
|---|---|
| `types.py` | `ProblemSeverity` enum (`error/warning/check/typo/info`), `Problem` dataclass, `ProblemSeverity.coerce`, `Problem.range_1based` / `range_0based`, `ProviderResult`, `ProblemProvider` (ABC). |
| `diagnostic_store.py` | `DiagnosticStore(QObject)` — bucketed merge of `disk_builtin` / `disk_external:*` / `live:*` results. `changed = pyqtSignal(object)`. `problems_for(path)` implements the merge policy (dirty buffer ⇒ live only). |
| `providers.py` | `analyze_buffer`, `analyze_buffer_fast`, `analyze_buffer_semantic`, `analyze_saved_file`, `scan_workspace`, `scan_external_workspace`, `merge_problems`, `AnalysisOutcome`, `diagnostic_category`. |
| `ruff_provider.py` | `RuffProvider`, `ruff_command()`, `find_ruff()`. **Optional** — missing tool ⇒ note, not error. |
| `pyright_provider.py` | `BasedPyrightProvider`, `basedpyright_command()`, `supports_stdin()`. **Optional** — missing tool ⇒ note, not error. |
| `walker.py` | `analyze_source()` — built-in AST provider (syntax errors, long lines, TODO/FIXME markers). `index_python_files()`. |
| `wire.py` | `spill_large_strings()`, `resolve_spills()`, `discard_spills()` — keeps the analysis IPC payload small. |

### 5.7 `editor/debugger/` — Debugging, Problems, Run

| Module | Key API |
|---|---|
| `problems_widget.py` | `ProblemsWidget(QWidget)` — signals `problemActivated(object)`, `problemClicked(object)`, `countsChanged(int,int,int)`, `providerError(str)`, `indexing_started/progress/finished`. `run_workspace_analysis(root)` (line 784), `track_tabs(tabs)` (line 1135), `problem_counts()`, `show_group()`, `show_all_groups()`, `filter_group()`. |
| `python_debug.py` | `DebugSession(QObject)` — `session_started/session_paused/session_ended/session_error`. `resolve_breakpoints()`. |
| `std_pipe.py` | `show_error_message()`, `handle_metrics()`, `launch_monitor()`. |
| `run/run_menu.py` | `RunMenuController` — `refresh_state()`, `run_current_file()`, `open_config_dialog()`, `run_configuration(path)`. |
| `run/config_run.py` | `ConfigRun` — `save_config`, `load_config`, `build_command(cwd)`, `run()`. |
| `run/run_config_dialog.py` | `RunConfigDialog(QDialog)` — `get_config()`. |
| `run/python_resolver.py` | `find_venv_python()`, `find_global_python()`, `resolve_project_python()`, `resolve_workspace_dir()`. |

### 5.8 `editor/terminal/` — Terminals & Consoles

| Module | Key API |
|---|---|
| `Emulator/emulator.py` | `BasePty` (ABC), `UnixPty`, `WinPty` (needs `pywinpty`), `PtyReader(QObject)` (daemon thread), `ShellEmulator(QObject)` — `raw_output_received`, `process_started/finished/errored`. |
| `Emulator/terminal_display.py` | pyte-backed screen buffer. |
| `Emulator/terminal_ui.py` | `TerminalPanel` — tab constants `TAB_SYSTEM_SHELL=0`, `TAB_PROMPTX=1`, `TAB_OUTPUT=2`, `TAB_PORTS=3`; `set_theme(bg,fg,sel)`, `set_workspace()`, `close_requested`. |
| `Emulator/terminal_workspace.py` | `TerminalWorkspace` — multi-session shell. |
| `DayDream/daydream.py` + `daydream_commands.py` | DreamScript console UI. |
| `PythonConsole/console.py` | `PythonShell` — qtconsole/IPython kernel. |
| `OutputsWidget/output_widget.py` | Captured stdout/stderr view. |
| `ProcessesViewer/ports_widget.py` | Ports table (psutil + `ss` fallback). |

### 5.9 `editor/utils/` — Panels & Utilities (10 subpackages)

| Subpackage | Key classes |
|---|---|
| `explorer/` | `SolutionExplorer(PanelShell)` (`explorer.py:75`), `ExplorerAPI` (`api.py:14`), `ExplorerFilterProxy` (`proxy.py:9`), `ExplorerDelegate` (`proxy.py:204`), `DreamTreeView` (`proxy.py:228`), `GitIgnoreService` (`gitignore.py:118`), `ExplorerClickMenu` (`menu.py:184`), `DreamStudioIconProvider` (`icons.py:5`), `DependenciesView` (`packages.py:7`), `menu.json`. |
| `solution/` | `SolutionStartWindow(QMainWindow)` (`startup_window.py:39`), `ScaffoldController` (`QScafoldController.py:19`), `WorkspaceService` (`workspace_service.py:29`), `paths.py` (`.ds/` layout), `solution_marker.py`, `manifests_scanner.py`, `recent_projects_scanner.py`, `theme.py`, `dialogs.py`, `project_card.py`, `QDreamDialog.py`. |
| `git_control/` | `GitVersionControl(PanelShell)` (`source_control.py:172`), `GitCommitHistory` (`source_control.py:13`), `git_control.py` (GitPython wrappers), `status_service.py` (`GitStatusService`, `_ScanWorker`). |
| `file_properties/` | `TreeOutline(PanelShell)` (`tree_outline.py:29`), `outline.py` (`build_outline`, `register_parser`, `SymbolKind`). |
| `properties/` | `PropertiesExplorer(PanelShell)` (`properties.py:16`), `properties_dialog.py`, `env.py`, `project_data_engine.py`. |
| `notifications/` | `NotificationManager(QObject)` (`notification_manager.py:47`), `NotificationsPanel` (`notifications_panel.py:101`). |
| `find_replace/` | `FindReplace(QFrame)` (`find_replace.py:13`), `SearchWorker(QThread)` (`search_engine.py:36`). |
| `tools/` | `TODOSearch(PanelShell)`, `CommandWindow(QMenu)`, `port_info.py`, `system_monitor.py` (`SystemMonitor`). |
| `server_explorer/` | `ServerExplorer`. |
| `etherAI/` | `EtherAI`. |
| — | `panel_shell.py` (`PanelShell` base for every side panel), `utils_tabmanager.py` (`UtilityTabManager`, `UtilityTabBar`), `theme.py`, `resource_path.py`, `icons.py`, `workspace.py`, `io.py`, `process.py`. |

### 5.10 `editor/widgets/` — Reusable Widgets (17 files)

File names carry a `Q` prefix (legacy Designer export convention); **class names do not** — e.g. `QToolButton.py` defines `ToolbarButton`.

| File | Class |
|---|---|
| `QToolButton.py` | `ToolbarButton(QPushButton)` — the flat icon button used by every bar. |
| `QOptionsMenu.py` | `ToolbarMenuButton(QPushButton)` — dropdown with arrow indicator. |
| `QSeparator.py` | `Separator(QFrame)` |
| `QDreamTabEditor.py` | `DreamStudioIDETabBar(QTabBar)` — fully custom-painted tab bar; `QDreamTabEditor(QTabWidget)`. |
| `QIndexingProgress.py` | `IndexingProgress(QWidget)` |
| `QIndexingCoordinator.py` | `IndexingCoordinator(QObject)` — multiplexes indexers onto one progress bar. |
| `QErrorMessage.py` | `QErrorMessage(QWidget)` — in-editor diagnostic bubble. |
| `QExitDialog.py` | `ExitDialog`, `ConfirmDialog`, `RenameDialog`, `ErrorDialog`, `UnsavedChangesDialog`. |
| `QToolBox.py` | `ExplorerToolbar(QHBoxLayout)` |
| `QToolTip.py` | `ToolTip(QFrame)` |
| `QCustomLabels.py` | `AnimatedGradientLabel(QLabel)` |
| `QSegmentedProgressBar.py` | `SegmentedProgressBar(QWidget)`, `FlowLayout(QLayout)` |
| `QSystemGraphWidget.py` | `SystemGraphUtil(QWidget)` |
| `QPlotWidget.py` | `PlotWidget(QWidget)` (pyqtgraph), `MainWindow(QMainWindow)` (demo host). |
| `QTitleBar.py` | `TitleBar` — legacy/unused; the live one is `editor/base/titleBar.py`. |
| `tab_manager.py` | Compatibility shim re-exporting `editor.utils.utils_tabmanager`. |

### 5.11 Other `editor/` subpackages

| Path | Purpose |
|---|---|
| `editor/promptx/` | `engine.py` (`CommandLine(cmd.Cmd)`, `HELP`, `ALL_COMMANDS`), `highlight.py` (`PromptXHighlighter`). |
| `editor/qss/` | 17 QSS files: 14 IDE themes + `startup_dark.qss`, `startup_light.qss`, `create_dialog.qss` + `README.md`. |
| `editor/init/` | `initialize.py` (stub), `project_bootstrap.py` (`ProjectBootstrapWorker`, `ProjectBootstrap`). |
| `editor/dreamstudio/` | `configs.py`. |

---

## 6. `DreamCLI/` — DreamScript Engine (C++17)

```
DreamCLI/
├── CMakeLists.txt          ← cmake 3.16, CMAKE_CXX_STANDARD 17, -Wall -Wextra -Wpedantic
├── dreamscript.grammar     ← grammar spec
├── core/fs.cpp             ← filesystem ops
├── include/                ← ast.hpp, fs.hpp, lexer.hpp, parser.hpp, token.hpp
├── src/                    ← lexer.cpp (396), parser.cpp (309), token.cpp (47), main.cpp (59)
│   └── commands/handler.cpp
├── ui/                     ← DayDream.py, DayTerminal.py (PyQt6)
└── build/                  ← CMake artifacts + `dscript` binary + libdreamcli_lib.a
```

Targets: static lib `dreamcli_lib` + executable `dscript`.

---

## 7. `hex-editor/` — ELF Inspector (C17)

```
hex-editor/
├── CMakeLists.txt   ← C17, OUTPUT_NAME "inspector", output → ../native/build/lib
├── include/inspector.h   ← extern "C" API (83 lines)
├── src/inspector.c       ← ELF parsing (399 lines)
└── build/                ← libinspector.so + libbinary_inspector.so
```

`native/` is a **pure output directory** — it contains no sources.

---

## 8. `manifests/`

- `manifests/menus.json` — declarative File/Edit/Run command manifests with `when` clauses.
- `manifests/projects/*.yaml` — 8 scaffold templates: `cpp_console_application`, `cpp_desktop_application`, `cpp_static_library`, `python_console_application`, `python_data_project`, `python_desktop_application`, `python_machine_learning`, `python_web_project`.
  - Required keys: `project_type`, `display_name`, `description`, `initialization`.
  - `initialization` = `{directories: [...], files: [...], templates: [{target, contents}]}`.
  - Optional `post_lifecycle: [{step, desc, unix, wind}]`.

---

## 9. `docs/`

6 numbered markdown chapters (`1_introduction.md` … `6_usefulUtilities.md`) + `doc_panel.py` (`DocPage`, `VerticalTabBar`).

---

## 10. Data / Config / Cache Layout

| Path | Written by | Purpose |
|---|---|---|
| `.configs/config.json` | `ConfigurationService` | Schema v2: `general_info`, `editor` (theme/font), `workspace.last_directory`. |
| `~/.dreamstudio/settings/user_settings.json` | `phase_user_home_setup` | Editor prefs + `solutions.recent`. |
| `~/.dreamstudio/plugins/plugins.json` | `registration.py` | Plugin specs (only `enabled` is user-owned). |
| `~/.dreamstudio/remote/configs.json` | `phase_user_home_setup` | Remote connection list (schema v1). |
| `<root>/.ds/solution.yaml` | `solution_marker.py` | Solution marker: `{version, name, project_type, manifest, created_at}`. |
| `<root>/.ds/run/*.json` | `ConfigRun.save_config` | Saved run configurations. |
| `<root>/.ds/cpp/index/*.json` | `CppIndexer` | Per-file C++ symbol index (version 3, invalidated by mtime). |
| `<root>/.ds/cpp/stable.pch` + `.key` | `pch.py` | libclang precompiled-header cache. |
| `~/.dreamstudio/cpp-sysindex/` | `sysindex.py` | Persistent system-header symbol index. |

---

## 11. Where to Look for Common Tasks

| Task | Start here |
|---|---|
| Add a top-level menu item | `editor/base/json/menus.json` → implement `set_<x>` in `editor/api/menus_api.py` |
| Add an options-bar button | `editor/base/json/optionbar.json` → implement callback in `editor/api/editor_api.py` |
| Add a side panel | `editor/utils/panel_shell.py` subclass → `editor/workspace_container.py:_populate_panels()` (line 296) + registration table (line 81) + `VerticalMenusAPI._TITLES` (line 12) |
| Add a new theme | `editor/qss/<name>.qss` + `editor/Ironica/themes/<name>.json` + `_set_theme_<name>()` in `editor/api/editor_api.py` + `optionbar.json` "Change Theme" menu |
| Add a language | `editor/Ironica/plugins/<lang>/plugin.json` + `provider.py::create_provider()` |
| Change syntax colours | `editor/Ironica/themes/*.json` (`palette` keys) |
| Change chrome colours | `editor/qss/*.qss` (all themes) |
| Add a diagnostic rule | `editor/analysis/walker.py` (`analyze_source`) |
| Change the startup sequence | `bootstrap/phases.py` + `bootstrap/manager.py:_DEFAULT_PHASES` (line 49) |
| Change tab behaviour | `editor/Ironica/tab_editor.py` |
| Change the editor itself | `editor/Ironica/code_editor.py` |
| Add a run configuration kind | `editor/debugger/run/config_run.py` + `run_config_dialog.py` |
| Add a project scaffold template | `manifests/projects/<name>.yaml` |
| Change packaging | `packaging/DreamStudio.spec` |

---

## 12. Things That Do **Not** Exist (do not look for them)

- **No `.poly` build files.** The root `AGENTS.md` mentions them; none exist in this tree.
- **No D-language source.** `AGENTS.md` lists `D-language`; there are zero `.d` files. D appears only as an icon mapping (`editor/utils/explorer/icons.py`) and a README prerequisite note.
- **No QML / JavaScript.** `node_editor/` is pure PyQt6 (`QPainter` canvas). `node_editor/node/json/package.json` is a *node-definition schema*, not an npm manifest.
- **No `setup.py`, `pyproject.toml`, root `Makefile`, `*.pro`, `*.qrc`.**
- **No `editor/api/fs.py`** — `tests/test_api_shared.py` imports it and fails at collection (known failure).
- **No `editor/Ironica/plugins/clang/`** — `tests/test_analysis_scaling.py` and `tests/test_large_file_perf.py` import from it and fail at collection (known failures).
- **No CI that runs tests.** `.github/workflows/static.yml` only deploys `public/` to GitHub Pages.
