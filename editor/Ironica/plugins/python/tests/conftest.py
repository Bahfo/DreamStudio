"""Shared fixtures for Python plugin tests.

Ensures the project root is on ``sys.path`` so that
``editor.Ironica.plugins.python.*`` imports resolve correctly.
"""

import os
import sys
import types
import pytest

# Ensure the project root is on sys.path.
_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# Mock heavy / unavailable dependencies.
def _ensure_mock_module(name):
    parts = name.split(".")
    for i in range(len(parts)):
        partial = ".".join(parts[: i + 1])
        if partial not in sys.modules:
            mod = types.ModuleType(partial)
            mod.__path__ = []
            sys.modules[partial] = mod


_MOCK_MODULES = [
    "pyte",
    "pyte.screens",
    "pyte/screen",
    "blessed",
    "docker",
    "docker_py",
    "fitz",
    "git",
    "git.exc",
    "psutil",
    "pyqtgraph",
    "pywinpty",
    "yaml",
    "PIL",
]

for _mod_name in _MOCK_MODULES:
    _ensure_mock_module(_mod_name)

# Provide minimal stubs expected from pyte.
if "pyte.screens" in sys.modules:
    _screens = sys.modules["pyte.screens"]

    class _FakeHistoryScreen:
        pass

    class _FakeChar:
        pass

    _screens.HistoryScreen = _FakeHistoryScreen
    _screens.Char = _FakeChar
