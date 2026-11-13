"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Suite fixtures for the gui_qa live-window tests: a ServiceRegistry and the
DreamStudio main window built exactly the way startup phase 8 builds it,
plus sample-file and git-repo workspace fixtures.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from editor.utils.solution.workspace_service import WorkspaceService

PROJECT_ROOT = Path(__file__).parents[2]
SUITE_DIR = Path(__file__).parent

if str(SUITE_DIR) not in sys.path:
    sys.path.insert(0, str(SUITE_DIR))

SETTLE_MS = 300


def _build_registry(tmp_path: Path, workspace: Path):
    """Create a ServiceRegistry mirroring startup phases 2-6.

    Args:
        tmp_path: Scratch directory for the configuration service.
        workspace: Workspace directory the service will point at.

    Returns:
        Tuple of (ServiceRegistry, ConfigurationService).
    """
    from config.config import ConfigurationService
    from config.registry import ServiceRegistry
    from config.resources import ResourceManager

    registry = ServiceRegistry()
    config_service = ConfigurationService(str(tmp_path / "qa_config_base"))
    cfg = config_service.load()
    resource_manager = ResourceManager(str(PROJECT_ROOT))
    theme_content = resource_manager.load_theme("dark")

    registry.register("config", cfg)
    registry.register("config_service", config_service)
    registry.register("theme_content", theme_content)
    registry.register("resource_manager", resource_manager)
    registry.register("base_dir", str(PROJECT_ROOT))
    registry.register("workspace", WorkspaceService())
    return registry, config_service


def _register_language_plugins() -> None:
    """Register the language plugins the way startup phase 9 does.

    The real boot pipeline creates the main window and then registers the
    language plugins, so editors know their language (and the outline and
    completion providers exist). The QA window mirrors that order.

    Returns:
        None; the language registry is updated in place.
    """
    from editor.Ironica.plugins.registration import register_all_languages

    register_all_languages()


def _make_window(qapp, registry, config_service, workspace_path: str):
    """Build and show the DreamStudio window the same way phase 8 does.

    Args:
        qapp: Live QApplication instance.
        registry: Registry holding config/theme/resource/workspace services.
        config_service: Unused placeholder keeping parity with real startup.
        workspace_path: Workspace directory passed to the window and service.

    Returns:
        Tuple of (window, workspace_service, ui_ready_count_list).
    """
    import sys

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from ui_build import DreamStudio

    window = DreamStudio(registry=registry, current_workspace=workspace_path)
    window.setEnabled(True)
    window.resize(1280, 800)

    _register_language_plugins()

    workspace = registry.get("workspace")
    try:
        workspace.attach_window(window)
        if workspace_path:
            workspace.open_workspace(workspace_path)
    except Exception:
        window.currentDirectory = ""

    ready_hits: list[int] = []
    window.ui_ready.connect(lambda: ready_hits.append(1))
    window.show()
    from harness import pump

    pump(qapp, SETTLE_MS)
    window.ui_ready.emit()
    pump(qapp, SETTLE_MS)
    return window, workspace, ready_hits


@pytest.fixture
def sample_tree(temp_workspace: Path) -> Path:
    """Populate the temp workspace with sample files before the window opens.

    Args:
        temp_workspace: Empty workspace directory from the root conftest.

    Returns:
        The populated workspace path.
    """
    workspace = temp_workspace
    (workspace / "main.py").write_text(
        '"""Sample module for gui_qa live tests."""\n'
        "\n"
        "import os\n"
        "\n"
        "\n"
        "def greet(name: str) -> str:\n"
        '    """Return a greeting."""\n'
        '    accent = "#aabbcc"\n'
        '    sky = "rgb(30, 144, 255)"\n'
        '    sea = "steelblue"\n'
        '    return f"hello {name} {accent} {sky} {sea}"\n'
        "\n"
        "\n"
        "class Sample:\n"
        '    """Trivial class used by navigation tests."""\n'
        "\n"
        "    def method(self, value: int) -> int:\n"
        '        """Double the value."""\n'
        "        return value * 2\n"
    )
    (workspace / "helpers.py").write_text(
        '"""Second sample file for tab switching."""\n'
        "\n"
        "def add(a: int, b: int) -> int:\n"
        '    """Sum two integers."""\n'
        "    return a + b\n"
    ),
    (workspace / "longlines.py").write_text(
        '"""Very long single line for wrap-mode tests."""\n'
        "\n"
        "LONG = '" + "x" * 400 + "'\n"
    )
    (workspace / "notes.txt").write_text("plain text notes\nsecond line\n")
    (workspace / ".gitignore").write_text("ignored_dir/\n*.log\n")
    (workspace / "ignored_dir").mkdir()
    (workspace / "ignored_dir" / "secret.txt").write_text("hidden from explorer\n")
    (workspace / "case_mixed.txt").write_text("Find Me here\nfind me again\nFIND ME\n")
    return workspace


@pytest.fixture
def qa_registry(qapp, temp_workspace: Path, tmp_path: Path):
    """Provide a ServiceRegistry wired like startup phases 2-6.

    Args:
        qapp: Live QApplication instance.
        temp_workspace: Workspace directory.
        tmp_path: Scratch directory for config storage.

    Yields:
        Tuple of (ServiceRegistry, ConfigurationService).
    """
    registry, config_service = _build_registry(tmp_path, temp_workspace)
    yield registry, config_service


@pytest.fixture
def qa_window(qapp, qa_registry, sample_tree: Path):
    """Build, show, and tear down the real DreamStudio main window.

    The window is built exactly like startup phase 8, enabled, shown, and
    ui_ready is emitted once so analysis may start. Teardown closes and
    deletes the window so one class cannot poison the next.

    Args:
        qapp: Live QApplication instance.
        qa_registry: Registry and config service pair.
        sample_tree: Populated workspace directory.

    Yields:
        The shown DreamStudio window.
    """
    from harness import assert_alive, pump, settle_analysis, settle_editors

    registry, config_service = qa_registry
    window, _workspace, ready_hits = _make_window(
        qapp, registry, config_service, str(sample_tree)
    )
    assert ready_hits == [1], "ui_ready must be emitted exactly once"
    yield window
    assert_alive(qapp, window)
    settle_editors(window)
    settle_analysis(qapp, window.hero_window._lower_widget.problems_window)
    window.close()
    window.deleteLater()
    pump(qapp, 100)


@pytest.fixture
def git_workspace(temp_workspace: Path) -> Path:
    """Initialize a real git repository inside the temp workspace.

    The repository starts clean with one commit of the sample files, so
    source-control tests can create controlled dirty states.

    Args:
        temp_workspace: Workspace directory to turn into a git repo.

    Returns:
        The workspace path containing the repository.
    """
    workspace = temp_workspace
    (workspace / "main.py").write_text(
        '"""Committed sample module."""\n'
        "\n"
        "def committed() -> str:\n"
        '    """Return a marker string."""\n'
        '    return "v1"\n'
    )
    env = {
        "GIT_AUTHOR_NAME": "QA",
        "GIT_AUTHOR_EMAIL": "qa@example.com",
        "GIT_COMMITTER_NAME": "QA",
        "GIT_COMMITTER_EMAIL": "qa@example.com",
        "HOME": str(workspace),
    }
    run = lambda *args: subprocess.run(  # noqa: E731
        ["git", *args], cwd=workspace, env=env, check=True, capture_output=True
    )
    run("init")
    run("add", "-A")
    run("commit", "-m", "initial commit")
    return workspace


@pytest.fixture
def git_window(qapp, qa_registry, git_workspace: Path):
    """Build the window over a git-enabled workspace.

    Args:
        qapp: Live QApplication instance.
        qa_registry: Registry and config service pair.
        git_workspace: Workspace directory containing a git repository.

    Yields:
        The shown DreamStudio window.
    """
    from harness import assert_alive, pump, settle_analysis, settle_editors

    registry, config_service = qa_registry
    window, _workspace, ready_hits = _make_window(
        qapp, registry, config_service, str(git_workspace)
    )
    assert ready_hits == [1], "ui_ready must be emitted exactly once"
    yield window
    assert_alive(qapp, window)
    settle_editors(window)
    settle_analysis(qapp, window.hero_window._lower_widget.problems_window)
    window.close()
    window.deleteLater()
    pump(qapp, 100)
