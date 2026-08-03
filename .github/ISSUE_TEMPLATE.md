# DreamStudio IDE — Issue Report

Thank you for taking the time to report an issue or request a feature.
Please fill in the relevant section below.

---

## Bug Report

**Title:** _A clear, concise title for the bug._

### Environment
- **DreamStudio Version:** <!-- e.g., 1.0.0 -->
- **OS:** <!-- e.g., Linux (Ubuntu 22.04), Windows 11, macOS Sonoma -->
- **Python Version:** <!-- e.g., 3.11.4 -->
- **PyQt6 Version:** <!-- e.g., 6.5.0 -->

### Description
_A clear description of the bug._

### Steps to Reproduce
1. ...
2. ...
3. ...

### Expected Behavior
_What you expected to happen._

### Actual Behavior
_What actually happened. Include error messages or tracebacks if applicable._

### Screenshots
_If applicable, add screenshots to help explain the problem._

### Additional Context
_Any other relevant information._

---

## Feature Request

**Title:** _A clear, concise title for the feature._

### Description
_A clear description of the feature you'd like._

### Use Case
_Why is this feature needed? What problem does it solve?_

### Proposed Solution
_If you have an idea for how this could be implemented, describe it here._

### Alternatives Considered
_Any alternative solutions or workarounds you've considered._

### Additional Context
_Any other relevant information, mockups, or references._

---

## Known Issues (Editor Module)

The following bugs have been identified in the `editor/` module.
If you are reporting one of these, reference the ID below.

| ID | Severity | File | Line(s) | Description |
|----|----------|------|---------|-------------|
| BUG-001 | Critical | `editor/debugger/python_debug.py` | 39–42 | `resolve_breakpoints()` silently continues after `os.path.exists()` returns `False`, then crashes on `open()` with `FileNotFoundError`. |
| BUG-002 | Critical | `editor/base/statusBar.py` | 254 | `get_repo_name()` calls `os.path.basename()` but `os` is never imported — raises `NameError` at runtime. |
| BUG-003 | Critical | `editor/Ironica/autocompletion/core.py` | 61 | `register_provider()` appends `self.providers` (the list) to itself instead of appending the `provider` argument — causes infinite self-reference and corrupts the provider list. |
| BUG-004 | Critical | `editor/Ironica/autocompletion/core.py` | 66–94 | `fetch_completions()` never returns `final_results` — callers always receive `None`. |
| BUG-005 | Moderate | `editor/Ironica/code_editor.py` | 244–252 | `is_zoomed()` returns `None` instead of `bool` — documented as a boolean query but has no `return` statement. |
| BUG-006 | Moderate | `editor/base/optionsBar.py` | 47 | No guard when the JSON config file is missing — `_build_bar()` silently fails and the bar renders empty. |
| BUG-007 | Moderate | `editor/utils/properties/get_proj_type.py` | 11–22 | `get_project_info()` is unimplemented (TODO), reads the `.dreamstudio` file but never returns anything — callers receive `None`. |
| BUG-008 | Moderate | `editor/debugger/python_debug.py` | 62 | Syntax-error path returns raw line mapping without notifying the user — silent incorrect behavior. |
| BUG-009 | Low | `editor/Ironica/code_editor.py` | 1450–1453,1464 | Magic numbers `2540`, `2542`, `2544`, `2546` used for Scintilla annotation API without named constants — fragile and hard to maintain. |
| BUG-010 | Low | `editor/Ironica/autocompletion/core.py` | 79 | Variable name typo: `aggergated_results` should be `aggregated_results`. |
