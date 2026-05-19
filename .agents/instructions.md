# AI Integration Guidelines

## DreamStudio IDE Instruction System for Autonomous and Semi-Autonomous Models

---

# Purpose

This document defines the orchestration standards, execution constraints, architectural philosophy, and operational behavior expected from all AI models interacting with this repository.

This repository is not a simple application.
It is a long-term IDE platform written in Python using PyQt6, designed as a reusable base architecture 
for future IDE products.

The system targets:

* Python development
* C development
* C++ development
* IDE tooling infrastructure
* Editor systems
* Static analysis systems
* Build orchestration
* Language tooling
* Plugin systems
* Cross-language extensibility

AI systems interacting with this repository must prioritize:

* Architectural consistency
* Stability
* Maintainability
* Scalability
* UI consistency
* Low technical debt
* Long-term extensibility
* High readability
* Component isolation
* Modular design

This document acts as a persistent instruction layer for all AI coding agents.

---

# Primary Objectives

The repository exists to build:

1. A professional-grade IDE framework
2. A reusable IDE core architecture
3. A scalable editor platform
4. A customizable developer environment
5. A future multi-language tooling ecosystem

The repository is NOT:

* A quick prototype
* A throwaway demo
* A scripting playground
* A single-language editor
* A shortcut-heavy experimental environment

Every contribution must support long-term maintainability.

---

# AI Agent Operational Philosophy

All AI models must behave as senior software engineers working inside a professional software company.

Models must:

* Think before modifying architecture
* Avoid impulsive rewrites
* Preserve compatibility
* Prefer incremental improvements
* Minimize hidden coupling
* Respect existing abstractions
* Maintain code readability
* Avoid introducing unnecessary dependencies
* Preserve consistent coding standards
* Avoid framework fragmentation

Models must NEVER:

* Randomly refactor unrelated systems
* Rewrite stable systems without explicit instruction
* Replace architecture impulsively
* Add unnecessary abstraction layers
* Introduce hidden global state
* Create circular dependencies
* Mix business logic with UI logic
* Embed large logic directly into widgets
* Use magic numbers or unexplained constants
* Create giant monolithic classes

---

# PyQt6 Standards

PyQt6 is the primary GUI framework.

All AI systems must follow strict PyQt6 architectural discipline.

## Mandatory Rules

### 1. Avoid Massive QWidget Classes

Widgets must remain focused.

Bad:

* One QWidget handling:

  * editor rendering
  * filesystem
  * syntax parsing
  * terminal execution
  * diagnostics
  * build systems

Good:

* Thin UI widgets
* External services
* Dedicated managers
* Signal-driven communication

---

### 2. Use Signals Properly

Avoid direct tight coupling.

Preferred:

```python
class FileManager(QObject):
    fileOpened = pyqtSignal(str)
```

Avoid:

```python
main_window.editor.setText(...)
```

inside deeply nested components.

---

### 3. Background Work Must Never Freeze UI

Heavy operations must use:

* QThread
* QRunnable
* QThreadPool
* asynchronous workers

Examples:

* indexing
* linting
* file scanning
* syntax analysis
* build execution
* searching
* git operations

must NOT block the main thread.

---

### 4. Theme System Must Be Centralized

Avoid inline styles.

Preferred:

```python
ThemeManager.get_color("editor.background")
```

Avoid:

```python
widget.setStyleSheet("background: #111")
```

throughout the codebase.

---

### 5. Editor Components Must Be Reusable

Editor widgets should be standalone and embeddable.

Avoid hardcoding:

* project references
* filesystem assumptions
* terminal assumptions
* language assumptions

The editor must become a reusable subsystem.

---

# Language Support Philosophy

The repository targets:

* Python
* C
* C++

All language tooling should evolve through abstraction.

Preferred architecture:

```text
LanguageProvider
├── PythonProvider
├── CProvider
└── CPPProvider
```

Avoid:

```python
if extension == ".py":
```

spread throughout the entire codebase.

Language-specific behavior should remain encapsulated.

---

# Code Generation Rules for AI Models

## AI models MUST:

### Produce complete code

Generated code must:

* compile
* run
* import correctly
* avoid syntax errors
* follow repository structure
* avoid placeholder implementations unless requested

---

### Preserve Existing APIs

Avoid breaking:

* method signatures
* plugin interfaces
* manager contracts
* settings schemas
* signal behavior

unless explicitly instructed.

---

### Use Explicit Naming

Preferred:

```python
project_tree_widget
build_configuration_manager
language_server_client
```

Avoid:

```python
obj
x
thing
mgr
```

---

### Prefer Composition Over Inheritance

Avoid deep inheritance trees.

Preferred:

```python
class EditorController:
    def __init__(self, editor_widget):
        self.editor_widget = editor_widget
```

---

### Use Type Hints

All new Python code should use typing.

Example:

```python
def open_project(path: str) -> bool:
```

---

### Use Docstrings Carefully

Use concise professional documentation.

Avoid useless comments like:

```python
# increment i
i += 1
```

Preferred:

```python
"""Handles asynchronous indexing of project files."""
```

---

# Editor System Guidelines

The editor system is the core of the repository.

All AI models must prioritize:

* responsiveness
* scalability
* extensibility
* clean rendering
* syntax architecture
* plugin compatibility

# File Management Rules

File operations must be safe.

AI models must:

* avoid destructive writes
* preserve encoding
* preserve line endings
* handle large files
* avoid memory-heavy operations

Preferred:

```python
with open(path, "r", encoding="utf-8") as file:
```

Avoid assumptions about:

* UTF-only systems
* Unix-only paths
* small file sizes

---

# State Management Philosophy

Avoid uncontrolled global state.

Preferred:

* service managers
* dependency injection
* event systems
* explicit ownership

Avoid:

```python
GLOBAL_EDITOR = None
```

---

# Logging Standards

All non-trivial systems should support structured logging.

Preferred:

```python
logger.info("Opened project: %s", path)
```

Avoid:

```python
print("opened")
```

for production systems.

---

# Error Handling Rules

AI models must NEVER silently swallow exceptions.

Avoid:

```python
except:
    pass
```

Preferred:

```python
except Exception as error:
    logger.exception(error)
```

Errors must remain observable.

---

# Performance Requirements

The IDE must remain responsive under:

* large projects
* many open files
* background indexing
* syntax parsing
* terminal execution
* diagnostics

AI systems must avoid:

* repeated full filesystem scans
* unnecessary repaint loops
* synchronous blocking operations
* excessive allocations
* duplicated parsing work

---

# AI Contribution Constraints

AI models must NOT:

* randomly rename files
* move architecture unnecessarily
* introduce incompatible dependencies
* replace working code impulsively
* modify unrelated modules
* delete systems without instruction
* over-engineer small systems

AI models SHOULD:

* propose improvements incrementally
* preserve compatibility
* isolate changes
* explain architectural reasoning
* document assumptions

---

# Repository Coding Style

## Python Style

Use:

* PEP8
* type hints
* explicit imports
* descriptive names
* modular classes

Avoid:

* wildcard imports
* gigantic functions
* deeply nested logic
* implicit state

---

# C/C++ Integration Philosophy

The IDE targets native tooling support.

Future integrations may include:

* clangd
* gcc
* gdb
* cmake
* make
* debugger integration
* static analyzers

AI models should preserve future compatibility.

Avoid tightly coupling the IDE to Python-only assumptions.

---

# Terminal Integration Rules

Terminal systems must:

* remain asynchronous
* support multiple sessions
* isolate shell processes
* avoid UI blocking
* support future PTY expansion

Avoid simplistic blocking subprocess usage for long-running processes.

---

# Future Scalability Goals

This repository may later evolve into:

* a professional desktop IDE
* a modular IDE framework
* a commercial-grade platform
* a cross-language development environment
* an educational IDE system
* a plugin marketplace ecosystem

All AI-generated code must anticipate future scale.

---

# Testing Philosophy

AI models should generate testable systems.

Avoid:

* hidden side effects
* UI-bound logic everywhere
* hardcoded dependencies

Preferred:

* service isolation
* deterministic behavior
* modular APIs

---

# Documentation Rules

AI models must document:

* architecture decisions
* public APIs
* subsystem responsibilities
* non-obvious behaviors

Documentation must remain concise and technical.

Avoid:

* excessive tutorial-style comments
* redundant documentation
* misleading placeholders

---

# Preferred Architectural Patterns

Preferred:

* manager systems
* service-oriented architecture
* event-driven communication
* modular providers
* adapter patterns
* command systems
* layered architecture

Avoid:

* giant god classes
* uncontrolled inheritance
* tightly coupled widgets
* duplicated logic

---

# AI Decision-Making Priorities

When uncertain, prioritize in this order:

1. Stability
2. Maintainability
3. Readability
4. Scalability
5. Extensibility
6. Performance
7. Feature quantity

Correct architecture is more important than fast feature generation.

---

# Refactoring Rules

Refactoring must:

* preserve behavior
* preserve APIs
* remain incremental
* avoid unnecessary rewrites

Large rewrites require explicit justification.

---

# Dependency Rules

AI models should minimize external dependencies.

Before adding a dependency, consider:

* maintenance burden
* compatibility
* platform support
* licensing
* binary size
* performance impact

Avoid adding libraries for trivial functionality.

---

# Cross-Platform Philosophy

The IDE should remain cross-platform whenever possible.

Target environments:

* Linux
* Windows
* potentially macOS

Avoid:

* platform-specific assumptions
* hardcoded paths
* shell-specific behavior

Use:

```python
pathlib
```

instead of fragile path concatenation.

---

# AI Communication Expectations

When generating implementation plans, AI systems should:

* explain architecture clearly
* explain tradeoffs
* identify risks
* isolate responsibilities
* preserve consistency

Avoid vague explanations.

---

# Repository Long-Term Vision

The repository is intended to become:

* a robust engineering platform
* a reusable IDE architecture
* a scalable development environment
* a maintainable software ecosystem

Every AI-generated contribution must support that direction.

---

# Final Mandatory Rules

## Always

* maintain modularity
* preserve architecture consistency
* avoid unnecessary rewrites
* prefer explicitness
* preserve UI responsiveness
* isolate language logic
* separate UI from logic
* support future scalability
* write maintainable code

## Never

* create giant monolithic systems
* tightly couple unrelated modules
* block the UI thread
* silently ignore exceptions
* introduce architectural chaos
* rewrite stable systems impulsively
* mix editor logic with rendering logic
* break compatibility casually

---

# AI Execution Directive

All AI systems interacting with this repository must behave as disciplined engineering contributors.

The goal is not merely generating code.

The goal is building a maintainable, scalable, professional IDE platform capable of evolving over many years.
