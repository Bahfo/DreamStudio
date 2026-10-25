"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared test fixtures.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_qapplication():
    """Mock QApplication for tests that don't need real Qt."""
    with (
        patch("PyQt6.QtWidgets.QApplication.instance", return_value=None),
        patch("PyQt6.QtWidgets.QApplication") as mock_app_class,
    ):
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app_class.instance.return_value = mock_app
        yield mock_app


@pytest.fixture
def temp_dir():
    """Temporary directory that cleans up after test."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def temp_workspace_with_solution(temp_dir):
    """Temporary workspace with .ds/solution.yaml marker."""
    import yaml

    from editor.utils.solution.paths import DS_DIR, SOLUTION_FILE

    workspace = temp_dir / "workspace"
    workspace.mkdir()

    ds_dir = workspace / DS_DIR
    ds_dir.mkdir(parents=True)

    solution_data = {
        "version": 1,
        "name": "Test Workspace",
        "project_type": "python_console_application",
        "manifest": "manifests/projects/python_console_application.yaml",
        "created_at": "2026-01-01T00:00:00Z",
    }

    with open(ds_dir / SOLUTION_FILE, "w") as f:
        yaml.safe_dump(solution_data, f)

    return workspace


@pytest.fixture
def sample_python_file(temp_dir):
    """Sample Python file for testing."""
    file_path = temp_dir / "sample.py"
    file_path.write_text(
        """
def hello():
    print("Hello, World!")

class MyClass:
    def method(self):
        return 42

if __name__ == "__main__":
    hello()
"""
    )
    return file_path


@pytest.fixture
def sample_cpp_file(temp_dir):
    """Sample C++ file for testing."""
    file_path = temp_dir / "sample.cpp"
    file_path.write_text(
        """
#include <iostream>

void hello() {
    std::cout << "Hello, World!" << std::endl;
}

class MyClass {
public:
    int method() {
        return 42;
    }
};

int main() {
    hello();
    return 0;
}
"""
    )
    return file_path


@pytest.fixture
def mock_editor():
    """Mock CodeEditor for unit tests."""
    from PyQt6.Qsci import QsciScintilla

    editor = MagicMock(spec=QsciScintilla)
    editor.text.return_value = ""
    editor.isReadOnly.return_value = False
    editor.isModified.return_value = False
    editor.getCursorPosition.return_value = (0, 0)
    editor.SendScintilla.return_value = 0
    return editor


@pytest.fixture
def mock_provider():
    """Mock BaseLanguageProvider."""
    from editor.Ironica.language_engine import BaseLanguageProvider

    provider = MagicMock(spec=BaseLanguageProvider)
    provider.get_hover_hint.return_value = None
    provider.get_definition_location.return_value = None
    provider.get_declaration_location.return_value = []
    provider.get_implementation_location.return_value = []
    provider.get_references.return_value = []
    provider.format_source.return_value = ""
    provider.has_diagnostics.return_value = False
    provider.has_outline.return_value = False
    provider.has_folding.return_value = False
    return provider


@pytest.fixture
def isolated_config_dir(temp_dir):
    """Isolated config directory for ConfigurationService tests."""
    config_dir = temp_dir / ".configs"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_notification_manager():
    """Mock notification manager."""
    from editor.utils.notifications.notification_manager import NotificationManager

    manager = MagicMock(spec=NotificationManager)
    manager.add_error = MagicMock()
    manager.add_warning = MagicMock()
    manager.add_info = MagicMock()
    return manager


# Pytest configuration for test isolation
# (These functions are not active hooks; they are helpers for conftest.py)


def pytest_configure(config):
    """Additional pytest configuration."""


def pytest_collection_modifyitems(config, items):
    """Modify collected items to add isolation markers."""
    # No-op; see conftest.py for active marker logic
