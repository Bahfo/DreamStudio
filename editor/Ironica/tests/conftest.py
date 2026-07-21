"""Shared fixtures for DreamStudio text-editor tests.

Set ``QT_QPA_PLATFORM=offscreen`` before running to avoid needing a
display server.

IMPORTANT: This conftest intentionally mocks out IDE-level modules
(terminal, git, explorer, etc.) that the top-level ``editor/__init__.py``
tries to import.  This lets us test the text-editor subsystem in
isolation without requiring the full dependency stack.
"""

import os
import sys
import types
import pytest

# Ensure the project root is on sys.path so that ``editor.*`` imports work.
_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ---------------------------------------------------------------------------
# Mock heavy / unavailable dependencies before any editor imports.
# ---------------------------------------------------------------------------


def _ensure_mock_module(name):
    """Create a stub module (and its parents) so that ``import name``
    does not fail with ``ModuleNotFoundError``."""
    parts = name.split(".")
    for i in range(len(parts)):
        partial = ".".join(parts[: i + 1])
        if partial not in sys.modules:
            mod = types.ModuleType(partial)
            mod.__path__ = []  # mark as package
            sys.modules[partial] = mod


# Modules that pull in heavy or unavailable dependencies.
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

# Provide minimal stub classes that the codebase expects from pyte.
if "pyte.screens" in sys.modules:
    _screens = sys.modules["pyte.screens"]

    class _FakeHistoryScreen:
        pass

    class _FakeChar:
        pass

    _screens.HistoryScreen = _FakeHistoryScreen
    _screens.Char = _FakeChar

# ---------------------------------------------------------------------------
# Now it is safe to import the editor text-editor modules.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp_instance():
    """Create a single ``QApplication`` for the entire test session."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture()
def editor(qapp_instance):
    """Return a fresh ``CodeEditor`` instance."""
    from editor.Ironica.code_editor import CodeEditor

    w = CodeEditor()
    yield w
    if hasattr(w, "_autocomplete_ext"):
        w._autocomplete_ext.cleanup()
    w.deleteLater()


@pytest.fixture()
def editor_api(qapp_instance):
    """Return a fresh ``EditorAPI`` wrapping a ``CodeEditor``."""
    from editor.Ironica.code_editor import CodeEditor
    from editor.Ironica.api import EditorAPI

    ed = CodeEditor()
    api = EditorAPI(ed)
    yield api
    if hasattr(ed, "_autocomplete_ext"):
        ed._autocomplete_ext.cleanup()
    ed.deleteLater()


@pytest.fixture()
def language_registry():
    """Reset the ``LanguageRegistry`` before and after each test."""
    from editor.Ironica.language_engine import LanguageRegistry

    LanguageRegistry.reset()
    yield LanguageRegistry
    LanguageRegistry.reset()


@pytest.fixture()
def sample_language_json(tmp_path):
    """Write a minimal valid language JSON file and return its path."""
    import json

    config = {
        "lang": "test_lang",
        "extensions": ["tst", "test"],
        "styles": {
            "keyword": "#FF0000",
            "string": "#00FF00",
        },
        "keywords": {
            "keyword": ["if", "else", "for", "while"],
            "string": ["hello", "world"],
        },
    }
    p = tmp_path / "test_lang.json"
    p.write_text(json.dumps(config), encoding="utf-8")
    return str(p)


@pytest.fixture()
def sample_legacy_json(tmp_path):
    """Write a legacy-format (words/colors_schema) language JSON file."""
    import json

    config = {
        "lang": "legacy_lang",
        "extensions": ["lg"],
        "words": {
            "if": "keyword",
            "else": "keyword",
            "hello": "string",
        },
        "colors_schema": {
            "keyword": "#FF0000",
            "string": "#00FF00",
        },
    }
    p = tmp_path / "legacy_lang.json"
    p.write_text(json.dumps(config), encoding="utf-8")
    return str(p)
