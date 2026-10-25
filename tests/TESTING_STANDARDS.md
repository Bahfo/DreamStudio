# Testing Standards — DreamStudio IDE

> **Purpose**: Authoritative reference for repository-specific test architecture, conventions, and rules.
> **Status**: Mandatory for all testing work on this repository.

---

## 1. Repository-Specific Test Architecture

### 1.1 Test Location & Organization
```
tests/
├── run_tests.sh              # Sole user-facing TUI entry point
├── test_runner.py            # Shared Python test runner
├── conftest.py               # Pytest configuration & fixtures
├── TESTING_STANDARDS.md      # This document
├── support/                  # Shared test utilities, fixtures, helpers
├── reports/
│   ├── HISTORY.md            # Global historical index (version-controlled)
│   ├── history/              # Compact machine-readable per-run records
│   └── runs/                 # Per-run artifacts (detailed, not version-controlled)
├── bootstrapping_test/       # Startup/kernel tests
│   ├── README.md
│   └── test_*.py
├── editor_test/              # Editor/Ironica tests
│   ├── README.md
│   └── test_*.py
└── navigation_test/          # Navigation/go-to-definition tests
    ├── README.md
    └── test_*.py
```

**Rules:**
- Every independently tested feature/subsystem gets its own `<feature>_test/` directory
- Suite directories created **only when tests exist** — no empty placeholder directories
- Shared fixtures/utilities go in `support/`, not duplicated across suites

### 1.2 Virtual Environment
- **Always** use the project's existing virtual environment: `./venv/bin/python`
- Never create a second virtual environment
- Never fall back to system Python
- Never modify `requirements.txt` or install packages without explicit authorization
- Run tests with: `QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest ...`

### 1.3 Test Framework
- **pytest** is the test framework (v9.1.1, pinned in requirements.txt)
- **pytest-qt** is NOT installed — use the `qapp` fixture from `conftest.py`
- **pytest-timeout** is NOT installed — use shell `timeout` command if needed
- All tests run headless with `QT_QPA_PLATFORM=offscreen` (enforced by `conftest.py`)

---

## 2. Test Naming & Organization

### 2.1 File Naming
- Test files: `tests/<suite>/test_<feature>_<behaviour>.py`
- Examples: `test_bootstrap_phases.py`, `test_editor_dirty_state.py`, `test_navigation_goto_def.py`

### 2.2 Test Function Naming
- `test_<what>_<condition>_<expected>`
- Examples: `test_load_file_utf8_succeeds`, `test_goto_definition_missing_returns_none`

### 2.3 Test Classes
- Group related tests in classes: `TestBootstrapPhases`, `TestEditorDirtyState`
- Use descriptive class names matching the feature under test

---

## 3. Anti-Cheating & No-Fix Rules

### 3.1 Prohibited Actions (NEVER DO)
| Action | Why It's Prohibited |
|--------|---------------------|
| Delete/weaken a test to make it pass | Hides real defects |
| Remove assertions, boundary checks, error checks | Reduces test value |
| Replace meaningful tests with smoke tests | False confidence |
| Change expected results to match broken implementation | Encodes bugs as spec |
| Add unjustified `@pytest.mark.skip`/`xfail` | Avoids finding problems |
| Mock the behavior being tested | Tests the mock, not the code |
| Catch/suppress exceptions in tests | Hides failures |
| Alter production code to make tests pass | Changes product, not test |
| Report passing when tests failed/skipped/blocked | Dishonest reporting |
| Invent/falsify test evidence | Integrity violation |

### 3.2 Testing-Only Scope
**Permitted changes during testing phase:**
- Testing infrastructure (runner, fixtures, reporters)
- New, appropriately scoped tests
- Testing documentation
- Result-reporting utilities
- Minimal infrastructure changes to execute/report tests

**NOT permitted:**
- Fixing product bugs
- Refactoring application code
- Implementing missing features
- Unrelated improvements

### 3.3 Pre-Existing Failures
- Known failures are **documented, not fixed**
- The old `build-and-test.md` baseline (24 failures / 3 collection errors) predates the
  removal of the previous `tests/` tree and is **not** a baseline for this framework.
- Current baseline (2026-10-25, run `20261025T165632Z-7c47925-dirty`):
  106 tests — 98 passed, 7 failed, 1 skipped.
- The 7 failures are deliberate contract-gap evidence:
  - `EditorAPI` is missing documented `goto_usage`, `goto_reference`,
    `find_usages`, `goto_implementation_file`, and `set_language`.
  - `EditorAPI.goto_declaration()` / `goto_implementation()` incorrectly reuse
    the go-to-definition handler instead of their distinct `CodeEditor` handlers.
- Do not weaken assertions to "fix" pre-existing failures. If the count changes,
  record the delta in the run history and update this baseline only with evidence.

---

## 4. TUI Execution & Exit Codes

### 4.1 Runner Entry Points
```bash
# Interactive TUI (default)
./tests/run_tests.sh

# Run single suite
./tests/run_tests.sh --suite bootstrapping

# Run all suites (CI mode)
./tests/run_tests.sh --all

# List suites
./tests/run_tests.sh --list
```

### 4.2 Exit Codes
| Code | Meaning |
|------|---------|
| 0 | All selected tests passed |
| 1 | Test failures detected (product defects) |
| 2 | Infrastructure/error (not a test failure) |
| 3 | Interrupted by user (SIGINT/SIGTERM) |
| 4 | No tests found/executed |

### 4.3 Progress & Reporting
- Live progress updates during execution (not just at end)
- JUnit XML is the **authoritative** result source; terminal output is used only
  for live progress so traceback text can never be mis-counted as test results
- Distinguish product-test failures from infrastructure failures
- Save run records even on failure/interruption
- Unique run IDs: `YYYYMMDDTHHMMSSZ-gitrev[-dirty]`, with `-2`, `-3`, … suffixes
  if a run starts in the same second; existing run directories are never reused
- Per-run directory: `tests/reports/runs/<run_id>/`
- `blocked` status is reserved for environment/infrastructure constraints; a
  skip reason beginning with `blocked:` is reported as blocked, not passed
- Reporting uses only the project venv and Python standard library (no `jq`
  dependency)

---

## 5. GUI & E2E Testing Conventions

### 5.1 Qt Testing
- Use session-scoped `qapp` fixture from `conftest.py`
- **Never** create a second `QApplication`
- Force `QT_QPA_PLATFORM=offscreen` (already in conftest)
- Control async Qt behavior with event-loop-aware waiting, not `time.sleep()`

### 5.2 GUI Test Categories
| Category | Scope | Example |
|----------|-------|---------|
| Unit | Individual functions/methods, no Qt | `test_bootstrap_config_loading` |
| Integration | Component interactions, signals, state | `test_workspace_switch_repoints_panels` |
| GUI | Real Qt widgets, signals, input, focus | `test_titlebar_menu_enable_disable` |
| E2E | Complete workflows across boundaries | `test_open_project_edit_save` |

### 5.3 E2E vs Mocked Tests
- **Real E2E**: Launches actual application, uses real components, verifies end state
- **Mocked collection**: Unit/integration tests with mocks — **clearly labeled as such**
- Never claim GUI integration passed when only isolated functions were tested

### 5.4 UI/UX Verification
- Verify objective properties: layout, resizing, keyboard accessibility, visible focus, theme consistency
- Screenshot comparison / accessibility checks → label as **manual review required**
- Do not automate subjective usability judgments

---

## 6. Failure Reporting Contract

Every failed test must record:

| Field | Required |
|-------|----------|
| Test identifier | Yes |
| Test file & line number | Yes |
| Production source file & line (if traceback supports) | When available |
| Failing assertion/exception | Yes |
| Expected vs actual behavior | Yes |
| Concise failure explanation | Yes |
| Reproducible command | Yes |
| Links to traceback, log, screenshot | Yes |
| Classification: product defect / test problem / infrastructure / environment / unresolved | Yes |
| Root cause: confirmed / suspected / undetermined | Yes |

**Never invent exact source location or root cause.** If unknown, state explicitly.

---

## 7. Append-Only Historical Test Records

### 7.1 Per-Run Evidence (in `tests/reports/runs/<run_id>/`)
- `report.md` — Human-readable report
- `summary.json` — Machine-readable outcomes
- `environment.txt` — Sanitized execution environment
- `console.log` — Captured output/errors
- `junit_<suite>.xml` — Structured test results
- `coverage.xml` — Only when actually generated
- Tracebacks, screenshots, diagnostic artifacts

### 7.2 Global Historical Index
- `tests/reports/HISTORY.md` — Chronological index (version-controlled)
- `tests/reports/history/<run_id>.json` — Compact machine records
- Counts include **passed, failed, errors, skipped, blocked** (errors are not
  collapsed into failures)

### 7.3 Per-Suite README
Each suite's `README.md` contains:
1. Latest-run summary
2. Historical runs table
3. Exact failure locations & reproduction commands
4. Links to reports/artifacts
5. Test scope & known limitations

### 7.4 Immutability Rules
- **Never overwrite** previous run artifacts
- **Never silently replace** or auto-prune history
- If earlier report has error: preserve original + append correction note
- Newer successful run **preserves all earlier failure records**
- Unique run IDs with collision handling

---

## 8. Public vs Private Result Storage

### 8.1 Durable Summaries (Version-Controlled)
- `tests/reports/HISTORY.md`
- `tests/reports/history/*.json` (compact, sanitized)
- Per-suite `README.md` files
- `TESTING_STANDARDS.md`

**Before committing**: Inspect for sensitive information (credentials, tokens, private paths, personal data)

### 8.2 Detailed Artifacts (Local Only)
- `tests/reports/runs/<run_id>/` — Full logs, screenshots, env dumps, diagnostics
- Excluded from Git via `.gitignore` (narrowly scoped)
- Remain available locally for investigation
- Not deleted because ignored by Git

### 8.3 Git & Historical Integrity
- Record tested Git revision + dirty-tree status
- Record relevant staged/unstaged changes affecting results
- Do not claim reproducibility from commit alone when uncommitted changes exist
- Do not auto-commit/push test results
- Document which files are version-controlled vs local

---

## 9. Test Categories & Conventions

### 9.1 Markers (defined in conftest.py)
```python
@pytest.mark.unit          # Unit tests
@pytest.mark.integration   # Component interactions
@pytest.mark.gui           # Real Qt widget tests
@pytest.mark.e2e           # End-to-end workflows
@pytest.mark.performance   # Performance/stability
@pytest.mark.regression    # Regression tests
@pytest.mark.slow          # Long-running tests
@pytest.mark.optional_dep  # Requires optional tools (ruff, pyright, clang, jedi, git)
```

### 9.2 Fixtures (from conftest.py)
- `project_root` — Project root Path
- `venv_python` — Virtual env Python path
- `qapp` — Session-scoped QApplication
- `temp_workspace` — Temporary workspace with `.ds/solution.yaml`
- `temp_config_dir` — Temporary base directory for `ConfigurationService`
  (the service appends `.configs/config.json` itself)
- `tab_editor_parent` — Minimal parent widget with `currentDirectory` for
  `DreamTabbedEditor`
- `reset_singletons` — Auto-use, resets module-level state

---

## 10. Commands Reference

```bash
# Interactive TUI
./tests/run_tests.sh

# Single suite
./tests/run_tests.sh --suite bootstrapping
./tests/run_tests.sh --suite editor
./tests/run_tests.sh --suite navigation

# All suites (CI)
./tests/run_tests.sh --all

# List suites
./tests/run_tests.sh --list

# Direct pytest (for development; not a substitute for the runner)
QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/bootstrapping_test/ -p no:cacheprovider -q

# Lint/format check on test files
./venv/bin/python -m ruff check tests/
./venv/bin/python -m black --check --line-length 110 tests/
```

---

## 11. Durable Rules Persistence

These rules are recorded in:
1. **This file**: `tests/TESTING_STANDARDS.md` (authoritative reference)
2. **AGENTS.md** reference: Added concise pointer to testing contract
3. **Repository files**: All infrastructure files in `tests/`

Future agents must recover rules from repository files even without conversational memory.

---

## 12. Change-Safety Checklist for Test Changes

Before committing test changes:

- [ ] Did I add a test without weakening existing ones?
- [ ] Does the test use the project venv (`./venv/bin/python`)?
- [ ] Does it run headless (`QT_QPA_PLATFORM=offscreen`)?
- [ ] Does it use `qapp` fixture (not create QApplication)?
- [ ] Are temp directories used (no real user data)?
- [ ] Are async Qt operations waited properly (no arbitrary sleeps)?
- [ ] Are mocks only at justified boundaries?
- [ ] Is failure reporting complete (location, command, evidence)?
- [ ] Does run produce unique run ID and preserve history?
- [ ] Are detailed artifacts in `runs/` (not version-controlled)?
- [ ] Is HISTORY.md updated append-only?
- [ ] Suite README updated preserving history table?
- [ ] No production code modified?
- [ ] No pre-existing tests weakened/deleted?
- [ ] Line length ≤ 110, docstrings present, type hints, trailing newline?
