# Build & Test — DreamStudio IDE

> **Purpose**: the exact, verified commands to build, run, test, lint, and package this repository.
> **Status**: every command below was executed on this machine unless marked *(unverified)*.

---

## 1. Environment

| Item | Value | How it was confirmed |
|---|---|---|
| Python | **3.12.3** (`CPython`, GCC 13.3.0) | `./venv/bin/python -V` |
| Virtualenv | `./venv` (in-repo, gitignored) | `run.sh` creates it if missing |
| pytest | **9.1.1** | `./venv/bin/python -m pytest --version` |
| ruff | **0.16.10** | `./venv/bin/python -m ruff --version` |
| black | **24.10.0** | `./venv/bin/python -m black --version` |
| PyInstaller | **6.22.3** | `./venv/bin/python -m PyInstaller --version` |
| CMake | **3.28.3** | `cmake --version` |
| g++ / gcc | **13.3.0** | `g++ --version` |
| Qt platform | `offscreen` for all headless runs | `tests/conftest.py:17` (fixture at `:21`) |

> There is **no** `pyproject.toml`, `pytest.ini`, `setup.cfg`, or `ruff.toml` in this repo. Configuration is implicit — see §7.

---

## 2. Setup

```bash
cd /home/bahaa/Desktop/apps/EXcellent-TechStacks_Projects/Major-Software/DreamStudio-IDE/DreamStudio

python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
```

`requirements.txt` is **fully pinned** (exact `==` versions). Do not upgrade a pin without verifying the affected subsystem; `libclang`, `PyQt6-QScintilla`, and `PyQt6` are tightly coupled to the C++ provider and the editor widget.

---

## 3. Running the IDE

### 3.1 Interactive (with display)

```bash
./run.sh          # creates venv if missing, then launches startup.py
# or
./venv/bin/python startup.py
```

`run.sh` also invokes `./clear_cache.sh` on exit (removes `__pycache__` and `.pytest_cache`).

### 3.2 Opening a specific solution at launch

```bash
./venv/bin/python startup.py --project /path/to/workspace
# aliases: --solution, -p
```
Parsed by `startup.py::_parse_project_arg` (line 14). The path must contain a solution marker (`.ds/solution.yaml`), otherwise the solution prompt phase runs instead.

### 3.3 Headless smoke test

```bash
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -c "
import startup
print('startup module imports cleanly')
"
```
Do **not** call `startup.main()` headless — it opens an event loop and blocks.

---

## 4. Tests

### 4.1 Canonical invocation

```bash
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests -p no:cacheprovider -q
```

`-p no:cacheprovider` avoids writing `.pytest_cache` into the tree.

### 4.2 Run a subset (preferred during development)

```bash
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest \
    tests/test_bootstrap.py tests/test_solution_management.py \
    -p no:cacheprovider -q
```
Verified result: **`3 failed, 65 passed, 1 warning`** — all 3 failures are pre-existing (§4.4).

Other useful subsets:

```bash
# C++ intelligence
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_cpp_*.py -p no:cacheprovider -q

# Diagnostics / Problems panel
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest \
    tests/test_audit_problems_workflows.py tests/test_problem_*.py \
    tests/test_audit_live_diagnostics.py -p no:cacheprovider -q

# UI / menus
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest \
    tests/test_titlebar_menus.py tests/test_status_bar_debug.py -p no:cacheprovider -q
```

### 4.3 Baseline (measured on this machine, commit `da0eddd`)

**Collection** — the full run aborts during collection with **3 errors** and collects 655 tests:

| Error | Cause |
|---|---|
| `tests/test_analysis_scaling.py` | `ModuleNotFoundError: No module named 'editor.Ironica.plugins.clang'` |
| `tests/test_api_shared.py` | `ImportError: cannot import name 'fs' from 'editor.api'` |
| `tests/test_large_file_perf.py` | `ModuleNotFoundError: No module named 'editor.Ironica.plugins.clang'` |

The `clang` plugin directory does not exist in this tree (the C++ provider lives at `editor/Ironica/plugins/cpp/`), yet `packaging/DreamStudio.spec` still lists `editor.Ironica.plugins.clang.provider` in `hiddenimports`. Both are pre-existing inconsistencies.

**Full run excluding the three broken modules:**

```bash
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests \
    -p no:cacheprovider -q \
    --ignore=tests/test_analysis_scaling.py \
    --ignore=tests/test_api_shared.py \
    --ignore=tests/test_large_file_perf.py
```
Verified result: **`24 failed, 629 passed, 2 skipped, 2 warnings in 65.62s`**.

**The 24 known failures** (all pre-existing — do not "fix" them by weakening assertions unless asked):

```
tests/test_audit_problems_workflows.py::test_new_diagnostic_introduced_while_typing
tests/test_audit_problems_workflows.py::test_squiggles_painted_for_open_editor
tests/test_audit_prod_stability.py::TestAuditWorkspaceService::test_open_nonexistent_does_not_crash
tests/test_bootstrap.py::TestStartupOrder::test_dependency_flow_no_circular
tests/test_completion_lifecycle.py::test_c_completion_manager_request_after_editor_destroy_is_noop
tests/test_cpp_definition_diagnostics.py::test_diagnostics_painted
tests/test_cpp_hover.py::test_hover_details_on_function_call
tests/test_cpp_hover.py::test_hover_display_returns_markdown_tuple
tests/test_cpp_hover.py::test_hover_hint_returns_html
tests/test_cpp_hover.py::test_hover_returns_none_for_empty
tests/test_cpp_hover.py::test_hover_on_class
tests/test_lexer_checkpoints.py::test_semantic_batch_mapping
tests/test_minimap_theme.py::test_every_shipped_theme_matches_minimap_to_editor_paper
tests/test_minimap_theme.py::test_every_shipped_theme_scopes_editor_scrollbar_to_paper
tests/test_problem_checks_category.py::test_checks_are_squiggled_and_unused_is_not
tests/test_scaffold_failure.py::test_failed_scaffold_reports_and_refreshes
tests/test_solution_management.py::TestSolutionMarker::test_write_and_read_roundtrip
tests/test_solution_management.py::TestManifestScan::test_find_project_type
tests/test_status_bar_debug.py::TestStatusBarWorkspaceAndBranchGuard::test_set_workspace_disables_branch_action_without_repo
tests/test_titlebar_menus.py::TestFindReplaceInFiles::test_search_and_replace_touches_files_on_disk
tests/test_titlebar_menus.py::TestFindReplaceInFiles::test_missing_directory_reports_error
tests/test_titlebar_menus.py::TestCodeMenuCommands::test_comment_and_uncomment_selection
tests/test_titlebar_menus.py::TestCodeMenuCommands::test_duplicate_current_line
tests/test_titlebar_menus.py::TestMenuWiring::test_declared_editor_actions_are_registered_for_state_sync
```

Representative root causes:
- `test_solution_management.py` imports `SOLUTION_FILE` from `editor.utils.solution.solution_marker`, but the constant now lives in `editor.utils.solution.paths` (`paths.py:9`).
- `test_lexer_checkpoints.py` needs `editor.Ironica.plugins.clang` → `ModuleNotFoundError`.
- `test_titlebar_menus.py::test_declared_editor_actions_are_registered_for_state_sync` expects a `set_find_replace_in_files` action that is not tracked.

### 4.4 Failure policy

- Pre-existing failures are **reported, not fixed**, unless the user asks.
- A change is only "green" relative to the baseline above. Always state the delta: *"N passed, same 24 known failures."*
- `pytest --timeout=…` **does not work** — `pytest-timeout` is not installed. Use `timeout <seconds> pytest …` from the shell instead.

### 4.5 Test file conventions

| Convention | Detail |
|---|---|
| Location | `tests/test_<feature>.py` (`tests/` is gitignored via `**/tests/` — the tracked files are force-added) |
| Fixtures | `tests/conftest.py` provides a session-scoped `qapp` and forces `QT_QPA_PLATFORM=offscreen` |
| Qt import | `conftest.py` prefers `PySide6` and falls back to `PyQt6` — the project itself is **PyQt6**-only |
| Naming | Most files are `test_audit_<feature>_<letter>.py` (audit trail) or `test_<subsystem>_<behaviour>.py` |
| Benchmarks | `tests/bench_editor_typing.py` is a manual benchmark, not a pytest target |

---

## 5. Native builds (CMake)

There are **two** independent CMake projects. Neither is required to run the IDE from source; both are needed for full C++ and binary-inspection features.

### 5.1 `hex-editor` — native binary inspector (C17)

```bash
cd hex-editor
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
```

**Verified.** Output:

```
[ 50%] Building C object CMakeFiles/binary_inspector.dir/src/inspector.c.o
[100%] Linking C shared library .../native/build/lib/libinspector.so
[100%] Built target binary_inspector
```

> **Gotcha:** `hex-editor/CMakeLists.txt` sets `LIBRARY_OUTPUT_DIRECTORY` to `${CMAKE_CURRENT_SOURCE_DIR}/../native/build/lib`. The `.so` is therefore written to **`native/build/lib/libinspector.so`**, *not* into `hex-editor/build/`. The PyInstaller spec expects it there.
>
> **Gotcha:** the checked-in `hex-editor/build/` directory contains a **stale `CMakeCache.txt`** with a different absolute source path. Reconfiguring in place fails with:
> ```
> CMake Error: The current CMakeCache.txt directory ... is different than the directory ...
> ```
> Fix: `rm -rf hex-editor/build` (or configure into a fresh directory) and re-run. Same for `DreamCLI/build`.

### 5.2 `DreamCLI` — the `dscript` CLI (C++17)

```bash
cd DreamCLI
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
```

**Verified.** Targets:

| Target | Kind | Output |
|---|---|---|
| `dreamcli_lib` | static library | `libdreamcli_lib.a` (from `src/lexer.cpp`, `src/parser.cpp`, `src/token.cpp`, `commands/*.cpp`) |
| `dscript` | executable | `dscript` (from `src/main.cpp`) |

Compiler flags: `-Wall -Wextra -Wpedantic`, `CMAKE_CXX_STANDARD 17`, extensions **off**.

### 5.3 Native library loading at runtime

The inspector `.so` is loaded through `ctypes` (`editor/Ironica/inspector/binding.py`) with a fallback search order that includes `native/build/lib/`, `hex-editor/build/`, and `editor/Ironica/inspector/`. The PyInstaller spec copies the library to **all three** locations for exactly this reason.

---

## 6. Packaging

### 6.1 PyInstaller (single-file-per-app bundle)

```bash
./venv/bin/python -m PyInstaller packaging/DreamStudio.spec --noconfirm
```

Produces **two** executables in `dist/DreamStudio/`:

| Executable | Role | `console=` |
|---|---|---|
| `DreamStudio` | The IDE | `False` (windowed) |
| `DreamStudioAnalysisServer` | Out-of-process Python analysis server | `True` (needs stdio) |

The spec lives at `packaging/DreamStudio.spec` and resolves `PROJECT_ROOT` from its own location (`SPEC_DIR.parent`), so it must be run **as a spec**, not as a bare script.

Notable spec details:
- `datas` bundles `assets/`, `editor/qss/`, `editor/base/json/`, `editor/Ironica/{keywords,snippets,themes}/`, `fonts/`, `icon_src/`, `manifests/`, `editor/utils/tools/json/`, `editor/utils/explorer/{menu.json,assets/}`, `editor/Ironica/analysis_server.py`, and `editor/Ironica/plugins/`.
- `hiddenimports` lists the `importlib`-loaded bootstrap phases explicitly — **a new dynamically imported module must be added here or it will be missing in the frozen build.**
- `excludes` drops `debugpy` on purpose (it does `__file__`-relative filesystem access at import time and breaks inside the frozen archive) and `tkinter`, `matplotlib`, `PyQt5`, `PySide2`, `PySide6`.
- `libclang` is bundled only if the `clang` pip package is present; otherwise the build warns and C/C++ intelligence degrades at runtime.
- `copy_metadata("jupyter_client")` is required for `jupyter_client` kernel provisioners to work in the frozen console.

### 6.2 Linux distribution folder

`publish/DreamStudio-linux-x86_64/` holds the prepared release layout (`DreamStudio/` app dir, `icon/`, `install.sh`, `SHA256SUMS.txt`). It is **gitignored** (`publish/`).

---

## 7. Linting & formatting

There is **no lint configuration file**. Use the pinned tools with explicit options:

```bash
# syntax + common errors on the changed files
./venv/bin/python -m ruff check editor/bootstrap 2>/dev/null || \
./venv/bin/python -m ruff check editor bootstrap ui_build.py startup.py

# formatting check (line length per .agents/style_rules.md = 110)
./venv/bin/python -m black --check --line-length 110 <changed files>

# auto-format
./venv/bin/python -m black --line-length 110 <changed files>
```

> `black` is installed but **not** applied to the codebase as-is; running it across the whole tree would produce a huge unrelated diff. Format only the files you touched.
>
> `ruff` with no config uses its default rule set (E4, E7, E9, F) — useful as a syntax/undefined-name gate, not as a style gate.

### 7.1 Line length

The project standard is **110 columns** (`.agents/style_rules.md` §2), not black's default 88. Always pass `--line-length 110`.

---

## 8. Cache cleanup

```bash
./clear_cache.sh          # removes __pycache__ and .pytest_cache directories
```
Also: `./clear_cache.bat` on Windows. Both are gitignored paths, so a dirty `git status` after a test run is normal and should not be staged.

---

## 9. CI

`.github/workflows/static.yml` **does not run tests**. It only deploys `./public` to GitHub Pages on every push to `main`.

> There is **no** automated test/lint pipeline in this repository. The full-suite baseline in §4.3 is the only quality gate — run it yourself before handing off.

---

## 10. Quick Command Reference

```bash
# --- setup ---
python3 -m venv venv && ./venv/bin/python -m pip install -r requirements.txt

# --- run ---
./run.sh
./venv/bin/python startup.py --project /path/to/solution

# --- test (full) ---
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests -p no:cacheprovider -q

# --- test (green subset, ignores the 3 broken modules) ---
env QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests -p no:cacheprovider -q \
  --ignore=tests/test_analysis_scaling.py \
  --ignore=tests/test_api_shared.py \
  --ignore=tests/test_large_file_perf.py

# --- native ---
cd hex-editor && cmake -S . -B build && cmake --build build -j"$(nproc)"
cd DreamCLI  && cmake -S . -B build && cmake --build build -j"$(nproc)"

# --- package ---
./venv/bin/python -m PyInstaller packaging/DreamStudio.spec --noconfirm

# --- lint / format ---
./venv/bin/python -m ruff check editor bootstrap
./venv/bin/python -m black --line-length 110 <files>

# --- cleanup ---
./clear_cache.sh
```
