# Specialized Instructions: Code Analysis, Security & Testing

This document guides advanced operations concerning quality assurance, deep code diagnosis, and test pattern implementation.

## 1. Code Analysis & Vulnerability Auditing
When running code analysis (`/audit`), you must look closely for these desktop software vulnerabilities:
- **Unsanitized Execution Paths:** Inspect how user code paths, terminal commands, or dynamic strings are fed into system shells (`os.system`, `subprocess.Popen`). Ensure `shell=False` is preferred and arguments are cleanly arrayed to avoid injection vulnerabilities.
- **Resource Exhaustion:** Watch out for unmonitored loops reading infinite streams from subprocess standard outputs. Ensure all socket reading or process pipes use defined chunk sizes and non-blocking poll methods.
- **Race Conditions:** Look for multiple background workers writing to shared data buffers without proper mutual exclusions (`QMutex`, `QMutexLocker`).

## 2. Testing Framework Standards
When generating test suites or inspecting bug patterns (`/test`), apply these standards:
- **Framework Choice:** Use `pytest` combined with `pytest-qt` to handle testing GUI elements without spawning active desktop loops when running headless test pipelines.
- **GUI Interactivity Mocking:** Use the `qtbot` fixture to simulate UI actions (typing text, clicking toolbar actions, switching document tabs) rather than calling methods directly.
- **Thread Testing:** When writing assertions against asynchronous workers, ensure you verify that your custom signals (`pyqtSignal`) emit the precise payload expected before validating side effects.
- **Mocking External Dependencies:** Mock all external subprocesses, virtual environments, and system file systems (`unittest.mock`) to keep the test architecture quick, predictable, and completely isolated.