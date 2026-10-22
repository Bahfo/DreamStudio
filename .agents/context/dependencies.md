# Dependencies — DreamStudio IDE

> **Purpose**: what each dependency is for, which ones are load-bearing, which are optional, and how to add or replace one safely.

---

## 1. The Dependency Contract

`requirements.txt` is **fully pinned** with `==`. Every version below is the pinned version.

Two rules govern every dependency:

1. **A missing dependency must disable a feature, never the IDE.** Optional integrations are imported inside `try/except` or resolved at runtime (`shutil.which`, `importlib.util.find_spec`) and degrade gracefully.
2. **Never add a module-scope import of a heavy or optional package** in a module that is imported during startup. Heavy imports go inside functions so a missing package cannot break the boot sequence.

---

## 2. Runtime Tiers

| Tier | Packages | Loaded when |
|---|---|---|
| **T0 — Hard requirement** | `PyQt6`, `PyQt6-QScintilla`, `PyQt6-Qt6`, `PyQt6_sip` | Startup, always. Without these the IDE does not start. |
| **T1 — Core functionality** | `PyYAML`, `parso`, `pythran`*(transitive)*, `packaging`, `platformdirs`, `typing_extensions` | Startup / first use of the affected feature. |
| **T2 — Language intelligence** | `jedi`, `libclang`, `parso`, `asttokens` | On demand, when a Python/C++ file is opened. |
| **T3 — Optional analyzers** | `ruff` (CLI), `basedpyright` (CLI — **not in requirements.txt**) | Only when the user enables the corresponding Problems group. |
| **T4 — Optional integrations** | `GitPython`, `qtconsole`, `jupyter_client`, `ipykernel`, `psutil`, `pyte`, `pyqtgraph`, `debugpy`, `pexpect`, `ptyprocess`, `prompt_toolkit` | On demand. Each has a graceful "not available" path. |
| **T5 — Tooling only** | `pytest`, `ruff`, `black`, `pyinstaller`, `pyinstaller-hooks-contrib`, `altgraph` | Development / packaging. Not needed to run the IDE. |

---

## 3. T0 — Hard Requirements

| Package | Pinned | Used in | Notes |
|---|---|---|---|
| `PyQt6` | 6.11.0 | 49 files | The Qt binding. `QtCore`, `QtGui`, `QtWidgets`, `QtSvg`. |
| `PyQt6-QScintilla` | 2.14.1 | 12 files | Scintilla widget binding (`PyQt6.Qsci`). Provides `QsciScintilla`, `QsciLexerCustom`. |
| `PyQt6-Qt6` | 6.11.2 | (transitive) | Qt 6 runtime binaries. Must match the `PyQt6` major/minor. |
| `PyQt6_sip` | 13.11.1 | (transitive) | SIP runtime. Required by PyQt6 itself. |
| `QScintilla` | 2.14.1 | (transitive) | QScintilla library; keep in lockstep with `PyQt6-QScintilla`. |

> The editor's entire rendering, folding, diagnostics painting, breakpoint margins, and minimap are built on Scintilla. Changing the QScintilla version is the single highest-risk dependency bump in this project.

---

## 4. T2 — Language Intelligence

| Package | Pinned | Used in | Fallback when missing |
|---|---|---|---|
| `jedi` | 0.20.0 | `editor/Ironica/plugins/python/` (`jedi_worker.py`, `provider.py`), `editor/Ironica/analysis_worker.py` | Python hover / completion / go-to-definition are disabled; the AST walker still provides diagnostics. |
| `parso` | 0.8.7 | (jedi's parser) | Bundled with jedi; pinned separately because jedi depends on it. |
| `asttokens` | 3.0.2 | (jedi's) | Same. |
| `libclang` | 18.1.1 | `editor/Ironica/plugins/cpp/` — `intellisense/engine.py`, `intellisense/index.py`, `intellisense/sysindex.py`, `intellisense/pch.py`, `autocompletion/callsite.py` | C++ hover / completion / definition / folding are disabled. The provider still loads and reports the missing capability. |

### How libclang is located

- **Dev:** the `clang` pip package ships `native/libclang.so`; `clang.cindex` finds it via `CDLL` search paths.
- **Frozen:** `packaging/DreamStudio.spec` locates the library via `importlib.util.find_spec("clang")` and copies it to **`clang/native/`** inside the bundle, where `ClangAdapter` looks for it. If the `clang` package is absent, the build prints a warning and C/C++ degrades — it does **not** fail the build.

### C++ system headers

`editor/Ironica/plugins/cpp/intellisense/sysindex.py` builds a system include index from the compiler's default include paths plus `compile_commands.json` / `compile_flags.txt` generated under `.ds/cpp/`. Without a system index, project-local definitions still work, but standard-library symbols will not resolve.

---

## 5. T3 — Optional Analyzers (external CLIs)

These are **not** Python packages — they are executables found at runtime.

| Analyzer | Resolution order | Source bucket | Notes |
|---|---|---|---|
| **ruff** | `shutil.which("ruff")` → `python -m ruff` (if importable) | `disk_external:ruff` | `editor/analysis/ruff_provider.py:81-89`. The pip package `ruff` **is** pinned in `requirements.txt`, so `python -m ruff` works. |
| **basedpyright** | `shutil.which("basedpyright")` → `shutil.which("pyright")` → `<root>/node_modules/.bin/basedpyright` → `python -m basedpyright` | `disk_external:pyright` | `editor/analysis/pyright_provider.py:63-86`. **Not in `requirements.txt`** — install separately (`pip install basedpyright` or `npm i -g basedpyright`). |
| **pyright** | same as above | `disk_external:pyright` | Alias. |

Both providers return a **structured "unavailable" reason** instead of raising:
- `ruff`: `not installed (ruff executable not found)`, `ruff timed out`, `ruff returned invalid JSON output`
- `basedpyright`: `not installed (basedpyright executable not found)`, `basedpyright returned invalid JSON output`, `basedpyright CLI has no stdin mode`

The built-in AST walker (`editor/analysis/walker.py`) is the **baseline** and never depends on an external tool.

---

## 6. T4 — Optional Integrations

| Package | Pinned | Used in | When missing |
|---|---|---|---|
| `GitPython` (+ `gitdb`, `smmap`) | 3.1.57 | `editor/utils/git_control/git_control.py` (`try: from git import Repo except Exception: Repo = None`) | Source-control panel shows an "unavailable" state; the IDE is unaffected. |
| `qtconsole` (+ `jupyter_client`, `ipykernel`, `traitlets`, `pyzmq`, `tornado`, `jupyter_core`) | 5.7.2 | `editor/terminal/PythonConsole/console.py` | The Python console tab shows "Python console unavailable: install qtconsole + jupyter to enable." |
| `psutil` | 7.2.2 | Process management in the terminal / run controller | Process listing degrades; process **kill** still works via the OS. |
| `pyte` (+ `wcwidth`) | 0.8.2 | `editor/terminal/Emulator/` — terminal screen emulation | The terminal falls back to raw output. |
| `pyqtgraph` | 0.14.0 | `editor/widgets/QPlotWidget.py` | Plot widgets are unavailable. |
| `debugpy` | 1.8.22 | *Not imported anywhere in the tree.* The Python debugger uses a custom pipe protocol (`editor/debugger/std_pipe.py`). | — **Excluded from the PyInstaller build on purpose:** `debugpy` performs `__file__`-relative filesystem access at import time, which cannot work inside a frozen archive. `ipykernel` treats a missing `debugpy` as "debug adapter unavailable" and starts the kernel without it. |
| `pexpect`, `ptyprocess`, `prompt_toolkit` | 0.9.0 / 0.7.0 / 3.0.53 | Transitive for `ptyprocess`-based PTY handling; `prompt_toolkit` is pulled in by `ipykernel`/`qtconsole`. | Native PTY path uses `pty`/`pexpect` on POSIX and `pywinpty` on Windows. |
| `playwright` | 1.63.0 | Not imported in the IDE tree. | — |
| `numpy` / `matplotlib` | 2.5.3 / (excluded) | `numpy` is a `pyqtgraph` dependency. `matplotlib` is **excluded** from packaging. | — |
| `pywinpty` | *not pinned* | Windows terminal. Referenced in `packaging/DreamStudio.spec` `hiddenimports`. | On POSIX it is not needed; on Windows install it manually. |

---

## 7. T5 — Tooling

| Package | Pinned | Purpose |
|---|---|---|
| `pytest` | 9.1.1 | Test runner. `pytest-timeout` is **not** installed — use the shell `timeout` command. |
| `ruff` | 0.16.10 | Linter + the external Ruff analyzer backend (same binary). |
| `black` | 24.10.0 | Formatter. Apply with `--line-length 110` and only to files you touched. |
| `pyinstaller` (+ `pyinstaller-hooks-contrib`, `altgraph`) | 6.22.3 | Packaging via `packaging/DreamStudio.spec`. |

---

## 8. The Unified Import Hub

`editor/__init__.py` is the project's import hub. It re-exports:

- **Stdlib subset** (lines 6-49): `ast`, `os`, `sys`, `re`, `json`, `pathlib`, `logging`, `subprocess`, `threading`, `traceback`, `tempfile`, `shutil`, `pickle`, `struct`, `ctypes`, `importlib`, `inspect`, `textwrap`, `weakref`, … plus `typing.*`.
- **collections / dataclasses / enum / itertools** (lines 51-58): `deque`, `ThreadPoolExecutor`, `as_completed`, `dataclass`, `field`, `asdict`, `Enum`, `IntEnum`, `islice`, `Path`.
- **`from typing import *`** (line 58).
- **PyQt6** (lines 60-64): `QtCore`, `QtGui`, `QtWidgets`, `QtSvg`, `Qsci` — all via `*`.

Consequences:

```python
from editor import *          # brings in os, sys, Path, QWidget, QsciScintilla, ...
from editor import *          # is the FIRST import in most editor modules
```

**Rules for the hub:**
- Add a new stdlib/3rd-party symbol to `editor/__init__.py` only if **many** modules need it. Otherwise import it locally.
- The hub is imported by `bootstrap`? **No.** `bootstrap/` must never import `editor/` (see `invariants.md` L1). The hub is for the `editor/` package only.
- Removing a name from the hub can break dozens of modules at once. Grep before you touch it.

---

## 9. Native (non-Python) Dependencies

| Artifact | Built from | Loaded via | Location |
|---|---|---|---|
| `libinspector.so` | `hex-editor/src/inspector.c` (C17) | `ctypes` in `editor/Ironica/inspector/binding.py` | `native/build/lib/libinspector.so` |
| `libbinary_inspector.so` | same target, alternate name | same | `hex-editor/build/` (bundled for the frozen build) |
| `dscript` | `DreamCLI/` (C++17) | standalone CLI, not loaded by the IDE | `DreamCLI/build/dscript` |
| `libclang` | `clang` pip wheel | `clang.cindex` | `venv/.../clang/native/libclang.so`, bundled to `clang/native/` |

Build commands: see `build-and-test.md` §5.

---

## 10. System Dependencies (not installable via pip)

| Need | Used for | Missing → |
|---|---|---|
| A C++17 compiler (`g++`/`clang++`) | Building `DreamCLI`, `hex-editor` | No native features |
| `cmake` ≥ 3.16 | Both CMake projects | No native features |
| `libclang` headers / system headers | C++ IntelliSense completeness | Reduced C++ symbol resolution |
| `git` binary | Richer Source Control UI (GitPython shells out for some ops) | Reduced VCS features |
| `ruff` binary | Fast Python linting in the Problems panel | Ruff diagnostics unavailable |
| `basedpyright` binary | Type-aware Python diagnostics | Pyright diagnostics unavailable |

---

## 11. Adding a Dependency — Checklist

1. **Is a Python package really needed?** Most "dependencies" here are better implemented with the stdlib.
2. **Pin it exactly** in `requirements.txt` (`name==X.Y.Z`).
3. **Import it lazily** — inside the function, not at module scope — unless it is T0.
4. **Handle the missing case explicitly** and surface it through the notification manager, not a traceback.
5. **If it is loaded via `importlib`** (bootstrap phases, plugin factories), add it to `hiddenimports` in `packaging/DreamStudio.spec` — otherwise the frozen build breaks silently.
6. **If it is a native library**, add it to the spec's `binaries` and to the runtime fallback search list.
7. **If it is an external CLI**, resolve it with `shutil.which` → `python -m <tool>` and return a structured "unavailable" reason.
8. **Update this document** and, if it changes a subsystem boundary, `architecture.md` too.

---

## 12. Removing a Dependency — Checklist

1. Grep the whole tree for the import name, **including** `packaging/DreamStudio.spec` (`hiddenimports`, `datas`, `binaries`, `excludes`).
2. Check `tests/` for tests that skip when the dependency is missing (`pytest.importorskip`) — those become failures, not skips.
3. Verify the frozen build still starts.
4. Remove the pin from `requirements.txt` and update this document.
