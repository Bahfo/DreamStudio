# Terminal Test Suite

Tests for the DreamStudio terminal subsystem.

## Scope
PTY backend, shell emulator, terminal display, workspace, UI, console, outputs widget, processes viewer, API, integration, stress.

## Run
QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/terminal_test/ -p no:cacheprovider -q
