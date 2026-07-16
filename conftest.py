"""Root conftest for DreamStudio tests.

This conftest is loaded BEFORE any ``editor`` package imports.
It mocks heavy or unavailable third-party dependencies so that
``editor/__init__.py`` (which pulls in terminal, git, explorer, etc.)
can be imported without the full dependency stack.
"""

import sys
import types


def _ensure_mock_module(name):
    """Create a stub module (and its parents) so that ``import name``
    does not fail with ``ModuleNotFoundError``."""
    parts = name.split(".")
    for i in range(len(parts)):
        partial = ".".join(parts[: i + 1])
        if partial not in sys.modules:
            mod = types.ModuleType(partial)
            mod.__path__ = []
            sys.modules[partial] = mod


# Modules that pull in heavy or unavailable dependencies.
_MOCK_MODULES = [
    "pyte",
    "pyte.screens",
    "pyte.screen",
    "pyte.streams",
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

# Provide minimal stubs that the codebase expects from pyte.
if "pyte.screens" in sys.modules:
    _screens = sys.modules["pyte.screens"]

    class _FakeHistoryScreen:
        pass

    class _FakeChar:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    _screens.HistoryScreen = _FakeHistoryScreen
    _screens.Char = _FakeChar

if "pyte.streams" in sys.modules:
    _streams = sys.modules["pyte.streams"]

    class _FakeStream:
        pass

    _streams.Stream = _FakeStream

if "git" in sys.modules:
    _git = sys.modules["git"]

    class _FakeRepo:
        def __init__(self, *a, **kw):
            pass

    _git.Repo = _FakeRepo
    _git.exc = sys.modules.get("git.exc") or types.ModuleType("git.exc")
    sys.modules["git.exc"] = _git.exc
    _git.exc.GitCommandError = type("GitCommandError", (Exception,), {})
