"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Pytest configuration and shared fixtures for DreamStudio IDE testing.
"""

import os
import sys
from pathlib import Path

import pytest

# Force headless Qt platform for all tests
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Prevent pytest cache from being written to the repository
os.environ.setdefault("PYTEST_CACHE_DIR", str(PROJECT_ROOT / ".pytest_cache"))


def pytest_configure(config):
    """Configure pytest with project-specific settings."""
    config.addinivalue_line("markers", "unit: Unit tests for individual functions/methods")
    config.addinivalue_line("markers", "integration: Integration tests for component interactions")
    config.addinivalue_line("markers", "gui: GUI tests requiring Qt widgets")
    config.addinivalue_line("markers", "e2e: End-to-end workflow tests")
    config.addinivalue_line("markers", "performance: Performance and stability tests")
    config.addinivalue_line("markers", "regression: Regression tests for known defects")
    config.addinivalue_line("markers", "slow: Tests that take significant time to run")
    config.addinivalue_line("markers", "optional_dep: Tests that require optional dependencies")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file path
        rel_path = Path(item.fspath).relative_to(PROJECT_ROOT)
        path_str = str(rel_path)

        if "bootstrapping_test" in path_str:
            item.add_marker(pytest.mark.unit)
        elif "editor_test" in path_str:
            item.add_marker(pytest.mark.gui)
        elif "navigation_test" in path_str or "python_plugin_test" in path_str:
            item.add_marker(pytest.mark.integration)

        # Mark tests that use external tools
        if any(keyword in item.name.lower() for keyword in ["ruff", "pyright", "clang", "jedi", "git"]):
            item.add_marker(pytest.mark.optional_dep)


@pytest.fixture(scope="session")
def project_root():
    """Provide the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def venv_python():
    """Provide the virtual environment Python interpreter path."""
    return PROJECT_ROOT / "venv" / "bin" / "python"


@pytest.fixture(scope="session")
def qapp():
    """
    Session-scoped QApplication fixture.

    Forces offscreen platform and ensures only one QApplication exists.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        # Set attribute before creating app
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        app = QApplication(sys.argv)
        app.setApplicationName("DreamStudio-Test")

    yield app

    # Don't quit the app - let pytest handle cleanup
    # app.quit() would interfere with other tests


@pytest.fixture
def temp_workspace(tmp_path):
    """
    Provide a temporary workspace directory with .ds solution marker.

    This creates a minimal valid workspace for testing.
    """
    import yaml

    from editor.utils.solution.paths import DS_DIR, SOLUTION_FILE

    workspace = tmp_path / "test_workspace"
    workspace.mkdir(parents=True)

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
def tab_editor_parent(qapp):
    """
    Provide a minimal main-window stand-in for DreamTabbedEditor.

    ``DreamTabbedEditor`` reads ``parent.currentDirectory`` during
    construction, so a bare QWidget is extended with that attribute.
    """
    from PyQt6.QtWidgets import QWidget

    parent = QWidget()
    parent.currentDirectory = ""
    yield parent
    parent.deleteLater()


@pytest.fixture
def temp_config_dir(tmp_path):
    """
    Provide a temporary base directory for ConfigurationService.

    ConfigurationService appends ``.configs/config.json`` itself, so the
    fixture returns the base directory, not the ``.configs`` subdirectory.
    """
    base_dir = tmp_path / "config_base"
    base_dir.mkdir()
    return base_dir


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Auto-use fixture to reset singleton state between tests.

    This prevents state leakage from previous tests.
    """
    # Reset any module-level singletons that might persist
    # Import inside fixture to avoid import-time side effects
    yield

    # Post-test cleanup
    import gc

    gc.collect()


# Pytest hooks for better reporting
def pytest_runtest_logreport(report):
    """Enhanced reporting for test runs."""


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Custom terminal summary with suite information."""
