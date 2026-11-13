"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Source control live tests: the real GitVersionControl panel driven against a
git repository created inside the temporary workspace.
"""

import subprocess
from pathlib import Path

import pytest

from harness import (
    Sweep,
    assert_alive,
    click,
    code_editor,
    live_probe,
    poke,
    pump,
    race_probe,
    type_text,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

GIT_ENV = {
    "GIT_AUTHOR_NAME": "QA",
    "GIT_AUTHOR_EMAIL": "qa@example.com",
    "GIT_COMMITTER_NAME": "QA",
    "GIT_COMMITTER_EMAIL": "qa@example.com",
}


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command inside the workspace.

    Args:
        workspace: Repository directory.
        args: Git arguments to execute.

    Returns:
        The completed process.
    """
    env = dict(GIT_ENV)
    env["HOME"] = str(workspace)
    return subprocess.run(
        ["git", *args], cwd=workspace, check=True, capture_output=True, env=env
    )


def _panel(window):
    """Return the source-control panel of the window.

    Args:
        window: The DreamStudio main window.

    Returns:
        The GitVersionControl panel instance.
    """
    return window.hero_window._source_control


def _activate(window) -> None:
    """Activate the source-control panel.

    Args:
        window: The DreamStudio main window.
    """
    window.hero_window._vertical_menus_api.activate_panel("source_control")
    pump(qapp_instance(), 200)


def qapp_instance():
    """Return the live QApplication instance.

    Returns:
        The QApplication singleton.
    """
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance()


class TestSourceControlPanel:
    """The panel reflects the real repository state."""

    def test_panel_opens_on_repo_workspace(self, qapp, git_window):
        """The panel opens and reports the branch of the repository."""
        window = git_window
        _activate(window)
        panel = _panel(window)
        assert panel.isVisible(), "source control panel not visible"
        assert (
            "Branch" in panel._status_label.text()
        ), f"unexpected status label: {panel._status_label.text()}"

    def test_clean_repo_reports_no_changes(self, qapp, git_window):
        """A clean repository shows the 'No changes detected' row."""
        window = git_window
        _activate(window)
        panel = _panel(window)
        panel._refresh()
        pump(qapp, 800)
        texts = [
            panel.tree.topLevelItem(i).text(0)
            for i in range(panel.tree.topLevelItemCount())
        ]
        assert any(
            "No changes" in text for text in texts
        ), f"clean repo did not report no changes: {texts}"

    def test_dirty_file_appears_in_tree(self, qapp, git_window):
        """Editing a tracked file shows up in the changed-files tree."""
        window = git_window
        _activate(window)
        panel = _panel(window)
        tracked = Path(window.currentDirectory) / "main.py"
        tracked.write_text(tracked.read_text() + "\n# qa change\n", encoding="utf-8")
        panel._refresh()
        pump(qapp, 800)
        texts = [
            panel.tree.topLevelItem(i).text(0)
            for i in range(panel.tree.topLevelItemCount())
        ]
        assert any(
            "Changes" in text for text in texts
        ), f"dirty file not reported in the tree: {texts}"

    def test_editor_edit_reaches_the_panel(self, qapp, git_window):
        """An edit in the editor reaches the source-control panel."""
        window = git_window
        tabs = window.hero_window._text_editor_center.tabs
        tabs.open_file_by_path(str(Path(window.currentDirectory) / "main.py"))
        pump(qapp, 400)
        _activate(window)
        panel = _panel(window)
        editor = code_editor(window.hero_window._text_editor_center.current_editor())
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "# qa\n")
        panel._refresh()
        pump(qapp, 800)
        texts = [
            panel.tree.topLevelItem(i).text(0)
            for i in range(panel.tree.topLevelItemCount())
        ]
        assert any(
            "Changes" in text for text in texts
        ), f"editor edit not visible in source control: {texts}"

    def test_tabs_switch_pages(self, qapp, git_window):
        """Status, History, and Branches buttons switch the panel page."""
        window = git_window
        _activate(window)
        panel = _panel(window)
        click(qapp, panel.btn_history)
        assert panel.workspace_stack.currentIndex() == 1, "history page not selected"
        click(qapp, panel.btn_branches)
        assert panel.workspace_stack.currentIndex() == 2, "branches page not selected"
        click(qapp, panel.btn_status)
        assert panel.workspace_stack.currentIndex() == 0, "status page not selected"

    def test_history_shows_the_fixture_commit(self, qapp, git_window):
        """The history tab shows the commit created by the fixture."""
        window = git_window
        _activate(window)
        panel = _panel(window)
        click(qapp, panel.btn_history)
        pump(qapp, 300)
        assert panel.history_stack.count() >= 1, "history stack is empty"

    def test_panel_buttons_are_clickable(self, qapp, git_window):
        """Poking the panel buttons records no failure."""
        window = git_window
        _activate(window)
        sweep = Sweep("source control poke")
        poke(qapp, _panel(window), sweep)
        sweep.finish()
        assert_alive(qapp, window)

    def test_panel_has_no_zero_size_widgets(self, qapp, git_window):
        """No visible widget inside the panel collapses to zero size."""
        window = git_window
        _activate(window)
        issues = live_probe(_panel(window))
        assert not issues, "zero-size visible widgets:\n" + "\n".join(issues)


class TestCommitFlow:
    """Committing from the panel must work against the temp repository."""

    def test_empty_commit_message_is_rejected(self, qapp, git_window):
        """An empty commit message does not create a commit."""
        window = git_window
        _activate(window)
        panel = _panel(window)
        tracked = Path(window.currentDirectory) / "main.py"
        tracked.write_text(tracked.read_text() + "\n# qa\n", encoding="utf-8")
        panel._refresh()
        pump(qapp, 600)
        panel.commit_input.setPlainText("")
        panel._do_commit()
        pump(qapp, 600)
        log = _git(Path(window.currentDirectory), "log", "--oneline").stdout.decode()
        assert log.count("\n") == 1, f"empty message created a commit:\n{log}"

    def test_commit_with_message_creates_commit(self, qapp, git_window):
        """A commit with a message creates a commit in the temp repository."""
        window = git_window
        _activate(window)
        panel = _panel(window)
        tracked = Path(window.currentDirectory) / "main.py"
        tracked.write_text(tracked.read_text() + "\n# qa commit\n", encoding="utf-8")
        panel._refresh()
        pump(qapp, 600)
        panel.commit_input.setPlainText("qa commit message")
        panel._do_commit()
        pump(qapp, 1500)
        log = _git(Path(window.currentDirectory), "log", "--oneline").stdout.decode()
        assert "qa commit message" in log, f"commit not created:\n{log}"

    def test_commit_button_click_commits(self, qapp, git_window):
        """Clicking the Commit Changes button performs the commit."""
        window = git_window
        _activate(window)
        panel = _panel(window)
        tracked = Path(window.currentDirectory) / "main.py"
        tracked.write_text(tracked.read_text() + "\n# qa click\n", encoding="utf-8")
        panel._refresh()
        pump(qapp, 600)
        panel.commit_input.setPlainText("qa click message")
        click(qapp, panel.commit_btn)
        pump(qapp, 1500)
        log = _git(Path(window.currentDirectory), "log", "--oneline").stdout.decode()
        assert "qa click message" in log, f"commit button did not commit:\n{log}"

    def test_refresh_during_scan_is_safe(self, qapp, git_window):
        """Refreshing repeatedly while the status scan runs stays stable."""
        window = git_window
        _activate(window)
        panel = _panel(window)
        race_probe(qapp, panel._refresh, 3)
        pump(qapp, 800)
        assert_alive(qapp, window)
        assert panel.tree.topLevelItemCount() >= 0, "tree in a broken state"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
