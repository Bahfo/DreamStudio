# Invariants — DreamStudio IDE

> **Purpose**: the rules that must hold true after every change. Break one and you have broken the IDE, not just a test.
> **How to use**: before editing, read the relevant section. After editing, re-check it. If a change *requires* breaking an invariant, stop and ask the user first.

---

## 1. Global Repository Invariants

| # | Invariant | Where it comes from |
|---|---|---|
| G1 | The IDE is **Python + PyQt6 + QScintilla**. C++/C only for native helpers (`hex-editor`, `DreamCLI`, `native/`). | `AGENTS.md` |
| G2 | **`.poly` files are build files.** Do not modify them unless explicitly instructed. (Currently none exist in the tree.) | `AGENTS.md` |
| G3 | Tests are `tests/test_*.py`; they run headless with `QT_QPA_PLATFORM=offscreen`. | `tests/conftest.py:17` |
| G4 | Every new Python file starts with the copyright header from `.agents/style_rules.md`. | `.agents/style_rules.md` §1 |
| G5 | **Max line length is 110 columns** — code, comments, and docstrings alike. | `.agents/style_rules.md` §2 |
| G6 | Every class and every public function has a docstring (`Args:` / `Returns:` Google-style). | `.agents/style_rules.md` §3 |
| G7 | Explicit type hints on all function parameters and return types. | `.agents/style_rules.md` §5 |
| G8 | Files end with a trailing newline; code is auto-formatted before hand-off. | `AGENTS.md` §Mandatory Rules |
| G9 | Absolute imports preferred; import order is stdlib → third-party → local. | `.agents/style_rules.md` §5 |
| G10 | Never commit secrets, tokens, or credentials. | system policy |

---

## 2. Layering & Import Invariants

| # | Invariant | Enforcement / proof |
|---|---|---|
| L1 | **`bootstrap/` must never statically import `editor/`.** The kernel may not know the UI exists. | `bootstrap/phases.py:18-40` deliberately uses `importlib.import_module` inside `_get_notification_manager()` with the comment "avoid static import cycle". |
| L2 | **`editor/` must not import `bootstrap/` at module scope.** Services reach the kernel only through the injected `ServiceRegistry`. | `editor/api/editor_api.py:340-345` resolves `ResourceManager` via `registry.get("resource_manager")`. |
| L3 | **`editor/api/*` mixins may import anything in `editor/`, but only `ui_build.py` may import the mixins.** The mixins are the leaf of the dependency graph. | `ui_build.py:16-17` |
| L4 | **`from editor import *` is the project convention**, not a smell to fix. New shared modules become available by being re-exported from `editor/__init__.py`. | Nearly every module header |
| L5 | `ui_build.py` (root) and `editor/Ironica/ui_build.py` are **different files** with different purposes. Never conflate them. | root = main window; Ironica one = `EditorContainer`/`UtilsContainer` |
| L6 | Third-party imports that are slow or optional (jedi, libclang, ruff, pyright) are **function-local**, so a missing package degrades one feature instead of breaking startup. | `editor/Ironica/plugins/python/provider.py`, `editor/analysis/ruff_provider.py` |

---

## 3. Startup Invariants

| # | Invariant | Detail |
|---|---|---|
| S1 | The **phase order** is fixed and meaningful: `application_startup → bootstrap_init → user_home_setup → configuration → resources → core_services → solution_prompt → main_window → language_plugins → finish`. | `bootstrap/manager.py:49-60` |
| S2 | Custom phases are inserted with `add_phase(name, fn, after=...)`; the default list is never mutated in place. | `bootstrap/manager.py:77` |
| S3 | Every phase receives the **same `PhaseContext`** and mutates it in place; the context is the only channel between phases. | `bootstrap/manager.py:106-109` |
| S4 | A phase failure is caught, recorded in `StartupResult.failed_phase` + `errors`, and routed to `RecoveryWindow` — it must never escape as an unhandled exception. | `bootstrap/manager.py:97+` |
| S5 | **Service registry keys are a stable contract.** Do not rename: `config_service`, `resource_manager`, `config`, `theme_content`, `base_dir`, `app`, `workspace`, `main_window`. | `bootstrap/phases.py` |
| S6 | `ConfigurationService` owns `.configs/config.json` (**schema v2**) and is the only writer. `~/.dreamstudio` is the user home for IDE state; `.configs` is the project-local config dir. | `bootstrap/config.py:15` |
| S7 | The window is constructed **hidden and disabled**, then enabled and shown on the next event-loop turn. Startup work must not flash an unusable window. | `startup.py` `_reveal_result` |
| S8 | `window.ui_ready` is the single signal that means "the IDE is interactive". Long-running work (workspace analysis, C++ indexing) is triggered from its handler, never from a phase. | `ui_build.py:22`, `startup.py` |
| S9 | Scaffolding a new solution runs **after** the window is visible, on a `QTimer.singleShot(0)`. | `startup.py` `_reveal_result` → `ScaffoldController.run_blocking()` |

---

## 4. UI Composition Invariants

| # | Invariant | Detail |
|---|---|---|
| U1 | There is exactly **one** top-level window: `DreamStudio`. Dialogs are transient children. | `ui_build.py:19` |
| U2 | `WorkspaceContainer` is the **single panel registry**. A new panel is registered there, not by a second registry. | `editor/workspace_container.py:81-148` |
| U3 | Every side panel is a `PanelShell` subclass and exposes `close_requested`. | `editor/utils/panel_shell.py:7` |
| U4 | The bottom dock is `UtilsContainer._stack` (a `QStackedWidget`). `EditorAPI._toggle_lower_panel` reaches into it directly — **this private access is load-bearing** until a public API exists. | `editor/api/editor_api.py:23` |
| U5 | `VerticalMenusAPI` owns the "which panel is visible" state and emits `panel_visibility_changed(str, bool)`. | `editor/api/vertical_menus_api.py:10` |
| U6 | Toolbar/menu items are declared in JSON (`editor/base/json/*.json`) and resolved to `set_<name>` callbacks on the window. Adding a menu item means editing JSON, not code. | `editor/base/json/menus.json` |
| U7 | Widgets that need to be reusable across panels live in `editor/widgets/Q<Name>.py` with a `Q` prefix. | `editor/widgets/` |
| U8 | The UI must not block the GUI thread on I/O or heavy compute. Everything slow goes to a worker (thread or subprocess). | §6 below |
| U9 | Theme application is a **single funnel**: `_apply_theme_content(qss)` → stylesheet + token extraction + `RethemeEngine.apply_current(window)`. Do not set stylesheets ad hoc in widgets. | `editor/api/editor_api.py:216` |

---

## 5. Editor & Document Model Invariants

| # | Invariant | Detail |
|---|---|---|
| E1 | **One `CodeEditor` per tab.** `EditorAPI` is a per-tab facade; `EditorContainer.current_editor()` returns `None` when the current tab is not a code tab (e.g. the preview tab). | `editor/Ironica/ui_build.py:87-93` |
| E2 | The **dirty flag is owned by `CodeEditor._is_dirty`** and is the single source of truth. Tab markers are a *mirror* of it, rebuilt via `tabBar().rebuild_dirty_indices()`. | `editor/Ironica/code_editor.py:81`, `editor/widgets/QDreamTabEditor.py:361` |
| E3 | Loading a file **resets** the dirty flag, clears save indicators, invalidates the provider cache, and re-runs folding. | `code_editor.py:2203-2222` |
| E4 | Encoding fallback order is fixed: `utf-8` → `utf-8-sig` → **platform default** (`None`) → `utf-8` with `errors="replace"`. Never raise on a decode failure. | `code_editor.py:2182-2193` |
| E5 | A file with **no write bits** opens read-only and the tab shows a lock indicator. | `code_editor.py:2224-2238`, `QDreamTabEditor.mark_readonly` (338) |
| E6 | `setText()` during load is done with `blockSignals(True)` so the dirty flag is not spuriously set. | `code_editor.py:2204-2208` |
| E7 | Language resolution is **by file extension** through `LanguageRegistry`; `set_language(lang)` is only for manual overrides. | `editor/Ironica/language_engine.py` |
| E8 | **Never call `Scintilla` APIs that assume a specific lexer** after a language change — always `setLanguage` first so `current_language` and the lexer agree. | `code_editor.py:2003` |
| E9 | The minimap wraps the editor in `MiniMapHostWidget`; code must unwrap via `_unwrap_code_editor` / `EditorAPI` rather than casting to `CodeEditor`. | `editor/Ironica/tab_editor.py:682` |

---

## 6. Threading Invariants

| # | Invariant | Detail |
|---|---|---|
| T1 | **All widget access happens on the GUI thread.** Workers never touch Qt widgets; they emit signals. | Qt rule, enforced by convention |
| T2 | Background work returns to the GUI thread via **Qt signals** (preferred) or `QMetaObject.invokeMethod`. Do not call widget methods from a worker. | e.g. `ProblemsWidget` worker→signal pattern |
| T3 | The Python whole-document analysis runs in a **separate process**, not a thread, so a runaway analysis cannot freeze the IDE. | `editor/Ironica/analysis_bridge.py:137` |
| T4 | The analysis subprocess has a **hard 15 s request timeout** and a **lock timeout**; it must never block startup indefinitely. | `analysis_bridge.py` (`_REQUEST_TIMEOUT_S = 15.0`) |
| T5 | Only the **focused** editor may submit analysis requests (`AnalysisProcessManager.set_active`). | `analysis_bridge.py` |
| T6 | Terminal PTY reads happen on a daemon thread and are **coalesced into the GUI thread** by a ~15 ms timer; raw socket/pty reads must never touch widgets. | `editor/terminal/Emulator/emulator.py:277` |
| T7 | Long, user-visible operations (workspace analysis, C++ index) run **in workers** and report progress through `indexing_started` / `indexing_progress` / `indexing_finished`. | `editor/debugger/problems_widget.py:343-345` |
| T8 | Python `threading.Thread` workers are used where a `QThread` is overkill (jedi, C++ completion). They must marshal results via a Qt signal on a `QObject` holder (`DiagnosticManager`, `CompletionManager`). | `plugins/python/jedi_worker.py:110`, `:192`, `:499` |

---

## 7. Plugin Invariants

| # | Invariant | Detail |
|---|---|---|
| P1 | A provider **must** implement `get_hover_hint`, `get_definition_location`, `format_source`. Everything else is optional with a documented default. | `editor/Ironica/language_engine.py:166-265` |
| P2 | Optional capabilities are declared by **presence of the method**, not by a config flag. `has_diagnostics` / `has_outline` / `has_folding` gate the rest. | same |
| P3 | Duck-typed flags (`wants_file_path`, `remote_analysis`, `remote_kind`, `slash_snippets_only`, `cpp_member_triggers`, `suppress_token_fallback`) are read via `getattr(provider, flag, default)`. Add a new flag **only** as a `getattr` default so old providers keep working. | `analysis_worker.py:71-79`, `cpp/provider.py:29-32` |
| P4 | **Both plugin loading paths must keep working**: manifest-based (`plugin.json`) and legacy dotted-path (`python/`). | `editor/Ironica/plugins/registration.py` |
| P5 | Plugin discovery is authoritative over `~/.dreamstudio/plugins/plugins.json`; the file only carries the `enabled` flag. | `registration.py::load_plugins_config` |
| P6 | Plugin directories added to `sys.path` and native libraries loaded with `ctypes.CDLL` are prepared by `_prepare_plugin_environment` and must be reversible on reload. | `registration.py` |
| P7 | A plugin that fails to load must **not** abort startup. It is logged and skipped. | `registration.py` |
| P8 | Plugin roots, in order: `$DS_PLUGIN_PATH` → `~/.dreamstudio/plugins/packages` → bundled `editor/Ironica/plugins`. | `registration.py::_plugin_roots` |

---

## 8. Diagnostics Invariants

| # | Invariant | Detail |
|---|---|---|
| D1 | `DiagnosticStore` is the **single source of truth** for diagnostics. Widgets never cache problem lists independently. | `editor/analysis/diagnostic_store.py` |
| D2 | Buckets are keyed `disk_builtin`, `disk_external:<source>`, `live:<source>`. Do not invent new bucket names without updating the merge policy. | `diagnostic_store.py` |
| D3 | **Dirty buffer ⇒ live diagnostics only.** Stale on-disk results must never be shown against an unsaved buffer. | `diagnostic_store.py::problems_for` (263) |
| D4 | Clean buffer ⇒ live + builtin disk + all external disk buckets. | same |
| D5 | Every buffer write carries a **revision counter**; results from a stale revision are discarded, not painted. | `diagnostic_store.py::set_live_results` |
| D6 | A diagnostic has a stable **identity** (rule id + message + range). Re-painting must not duplicate entries. | `diagnostic_store.py` |
| D7 | The editor paints problems as squiggles via `set_diagnostic_ranges`; "de-emphasised" problems use a **separate** dimmed range set, not a second squiggle. | `code_editor.py` |
| D8 | The builtin walker is the **baseline**; Ruff/Pyright are additive and optional. Removing an external provider must not remove baseline diagnostics. | `editor/analysis/walker.py` |

---

## 9. Solution / Workspace Invariants

| # | Invariant | Detail |
|---|---|---|
| W1 | A workspace is identified by the marker file **`<root>/.ds/solution.yaml`**. | `editor/utils/solution/paths.py:9,49` |
| W2 | All per-workspace metadata lives under `.ds/`: `run/`, `cpp/`, `cpp/index/`, `compile_commands.json`, `compile_flags.txt`, `stable.pch`. | `paths.py` |
| W3 | `DEFAULT_EXCLUDES` (`.git`, `venv`, `node_modules`, `build`, `dist`, …) must stay in sync with the explorer's exclusion logic. | `paths.py:21-41` |
| W4 | Switching workspaces **re-points every panel** through `WorkspaceService._repoint_panels` — no panel may keep a stale root. | `workspace_service.py:155` |
| W5 | Workspace analysis and C++ indexing are **deferred to the next event-loop turn** so the switch is not blocked by indexing. | `workspace_service.py:194` |
| W6 | A workspace change emits `workspace_changed(str)`; panels subscribe to it rather than polling. | `workspace_service.py:32` |
| W7 | Scaffolding failures must be **reported, not swallowed** — the user sees the failure and the IDE stays alive. | `tests/test_scaffold_failure.py` |
| W8 | Never create a `.ds` directory outside the workspace root, and never write into a user's project without an explicit user action. | `paths.py` |

---

## 10. Configuration & Path Invariants

| # | Invariant | Detail |
|---|---|---|
| C1 | **User state** (`~/.dreamstudio/`) and **project config** (`.configs/config.json`) are separate. Never mix them. | `bootstrap/config.py` |
| C2 | `config.json` is schema **v2**; migrations must be additive and idempotent. | `bootstrap/config.py` |
| C3 | A corrupt config is **repaired**, not fatal. | `bootstrap/config.py` |
| C4 | `SOLUTION_FILE`, `DS_DIR`, and the other filename constants live in `editor/utils/solution/paths.py` — import them, do not re-declare string literals. | `paths.py:8-19` |
| C5 | Paths are built with `os.path` helpers in `paths.py`/`editor/utils/workspace.py`; use them instead of ad-hoc joins so Windows separators stay correct. | `paths.py` |
| C6 | Resource lookups go through `ResourceManager`, which resolves both dev paths and `sys._MEIPASS` (frozen) paths. | `bootstrap/resources.py:37` |

---

## 11. Error Handling Invariants

| # | Invariant | Detail |
|---|---|---|
| E-1 | **Never let an exception escape into the Qt event loop.** Wrap risky calls; log with `logger.<level>`; degrade the feature. | Project-wide convention |
| E-2 | Optional integrations (git, ruff, pyright, clang, pywinpty) are wrapped so an **ImportError disables the feature, not the IDE**. | e.g. `editor/utils/git_control/git_control.py` |
| E-3 | `except Exception` is used at integration boundaries; **never** swallow `KeyboardInterrupt` / `SystemExit`. | Project-wide convention |
| E-4 | User-visible failures go through the **notification manager**, not a bare `print`. | `editor/utils/notifications/notification_manager.py` |
| E-5 | Startup failures are routed through `RecoveryWindow`; runtime failures through notifications; only unrecoverable crashes may show a traceback. | `bootstrap/recovery.py:34` |
| E-6 | Logging uses the module-level `logger = logging.getLogger(__name__)` idiom, never the root logger directly. | Project-wide convention |

---

## 12. Testing Invariants

| # | Invariant | Detail |
|---|---|---|
| T-1 | New behaviour ships with a test named `tests/test_<feature>.py`. | `AGENTS.md` §Tests |
| T-2 | Tests must run headless: `QT_QPA_PLATFORM=offscreen`. The session fixture already forces this. | `tests/conftest.py:17`, fixture at `:21` |
| T-3 | Widget tests reuse the **session-scoped `qapp` fixture**; never create a second `QApplication`. | `tests/conftest.py:21` |
| T-4 | Prefer pure-logic tests (no Qt) for algorithms; they run far faster and are less brittle. | — |
| T-5 | **Known-failing tests are pre-existing** and must be reported, not silently "fixed" by weakening the assertion. | See `build-and-test.md` §Baseline |
| T-6 | Tests must not require network access, a real git server, or a writable home directory outside `tmp_path`. | — |

---

## 13. Change-Safety Checklist

Run through this before declaring any change done:

- [ ] Did I change a **public interface** (method signature, signal name, registry key, JSON schema)? → Update the consumers *and* the docs in `.agents/context/`.
- [ ] Did I introduce a **module-scope import** of a heavy/optional package? → Move it inside the function.
- [ ] Did I touch the **dirty flag**? → Verify the tab marker mirrors it and `rebuild_dirty_indices()` is called.
- [ ] Did I add a **signal**? → Connect it on the GUI thread and disconnect on teardown.
- [ ] Did I add a **provider capability**? → Use `getattr` defaults so old providers keep working.
- [ ] Did I add a **panel**? → Register it in `WorkspaceContainer` *and* in `VerticalMenusAPI`.
- [ ] Did I add a **menu/button**? → Declare it in `editor/base/json/*.json` and implement `set_<name>` on the window.
- [ ] Did I change a **theme**? → Update both the `.qss` and the matching `editor/Ironica/themes/<name>.json`.
- [ ] Did I change **startup**? → Keep phase order intact and keep `bootstrap/` free of `editor/` imports.
- [ ] Did I touch `.poly` files? → **Do not**, unless explicitly told to.
- [ ] Are lines ≤ 110 chars, docstrings present, type hints present, trailing newline present?
- [ ] Did I run the relevant tests and report the result, including pre-existing failures?
