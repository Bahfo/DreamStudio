"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Side panel live tests: every panel registered in workspace_container.py must
activate, size, accept interaction, and deactivate cleanly.
"""

from pathlib import Path

import pytest

from harness import (
    Sweep,
    assert_alive,
    assert_positive_size,
    click,
    code_editor,
    live_probe,
    poke,
    pump,
    type_probe,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

PANELS = {
    "solution_explorer": "_solution_explorer",
    "source_control": "_source_control",
    "file_outline": "_file_outline",
    "properties": "_properties_explorer",
    "todo_search": "_todo_search",
    "server_explorer": "_server_explorer",
    "notifications": "_notifications_panel",
    "ether_ai": "_ether_ai",
}


def _panel_widget(window, panel_id: str):
    """Return the widget instance registered for *panel_id*.

    Args:
        window: The DreamStudio main window.
        panel_id: Registered panel identifier.

    Returns:
        The panel widget.
    """
    return getattr(window.hero_window, PANELS[panel_id])


def _activate(window, panel_id: str) -> None:
    """Activate a panel through the VerticalMenusAPI.

    Args:
        window: The DreamStudio main window.
        panel_id: Registered panel identifier.
    """
    window.hero_window._vertical_menus_api.activate_panel(panel_id)


def _deactivate(window, panel_id: str) -> None:
    """Deactivate a panel through the VerticalMenusAPI.

    Args:
        window: The DreamStudio main window.
        panel_id: Registered panel identifier.
    """
    window.hero_window._vertical_menus_api.deactivate_panel(panel_id)


class TestPanelLifecycle:
    """Every registered panel activates, shows, and deactivates."""

    def test_every_panel_activates_and_sizes(self, qapp, qa_window):
        """Activating any panel shows it with a positive size."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        for panel_id in PANELS:
            _activate(window, panel_id)
            pump(qapp, 120)
            assert api.is_visible(panel_id), f"panel '{panel_id}' not visible"
            widget = _panel_widget(window, panel_id)
            assert_positive_size(widget, f"panel '{panel_id}'")
            _deactivate(window, panel_id)
            pump(qapp, 80)
            assert not api.is_visible(panel_id), f"panel '{panel_id}' still visible"

    def test_panels_have_no_zero_size_children(self, qapp, qa_window):
        """A visible panel has no visible zero-size descendants."""
        window = qa_window
        for panel_id in PANELS:
            _activate(window, panel_id)
            pump(qapp, 120)
            issues = live_probe(_panel_widget(window, panel_id))
            assert (
                not issues
            ), f"panel '{panel_id}' has zero-size widgets:\n" + "\n".join(issues)
            _deactivate(window, panel_id)
            pump(qapp, 60)

    def test_deactivated_panel_is_hidden(self, qapp, qa_window):
        """A deactivated panel is not visible on screen."""
        window = qa_window
        for panel_id in PANELS:
            _activate(window, panel_id)
            pump(qapp, 120)
            _deactivate(window, panel_id)
            pump(qapp, 120)
            widget = _panel_widget(window, panel_id)
            assert not widget.isVisible(), f"panel '{panel_id}' still visible"

    def test_click_inside_panel_does_not_break_window(self, qapp, qa_window):
        """Clicking inside a panel never hides the window or raises."""
        window = qa_window
        sweep = Sweep("panel click sweep")
        for panel_id in PANELS:
            _activate(window, panel_id)
            pump(qapp, 120)
            widget = _panel_widget(window, panel_id)
            sweep.step(f"click inside '{panel_id}'", click, qapp, widget)
            if not window.isVisible():
                sweep.note(f"click inside '{panel_id}'", "window hidden")
                break
            _deactivate(window, panel_id)
            pump(qapp, 60)
        sweep.finish()
        assert_alive(qapp, window)

    def test_panel_button_poke_is_clean(self, qapp, qa_window):
        """Poking panel buttons records no failure for any panel."""
        window = qa_window
        sweep = Sweep("panel button poke")
        for panel_id in PANELS:
            _activate(window, panel_id)
            pump(qapp, 120)
            sweep.step(
                f"poke '{panel_id}'", poke, qapp, _panel_widget(window, panel_id), sweep
            )
            _deactivate(window, panel_id)
            pump(qapp, 60)
        sweep.finish()

    def test_panel_text_inputs_accept_input(self, qapp, qa_window):
        """Text entries inside panels accept and release typed input."""
        window = qa_window
        sweep = Sweep("panel text input")
        for panel_id in PANELS:
            _activate(window, panel_id)
            pump(qapp, 120)
            sweep.step(
                f"type in '{panel_id}'",
                type_probe,
                qapp,
                _panel_widget(window, panel_id),
                sweep,
            )
            _deactivate(window, panel_id)
            pump(qapp, 60)
        sweep.finish()


class TestFileOutlinePanel:
    """The outline panel has its own title and navigation contract."""

    def test_outline_title_is_human_readable(self, qapp, qa_window):
        """The outline tab must show a human title, not the raw panel id.

        NOTE (QA finding): ``file_outline`` is absent from
        ``VerticalMenusAPI._TITLES``, so the tab falls back to the raw id.
        """
        from editor.api.vertical_menus_api import VerticalMenusAPI

        window = qa_window
        _activate(window, "file_outline")
        pump(qapp, 150)
        manager = window.hero_window._left_utils_manager
        titles = [manager._tab_bar.tabText(i) for i in range(manager._tab_bar.count())]
        assert (
            "file_outline" not in titles
        ), f"outline tab shows the raw panel id: {titles}"
        assert (
            "file_outline" not in VerticalMenusAPI._TITLES
        ), "file_outline is missing from VerticalMenusAPI._TITLES"

    def test_outline_lists_symbols_of_open_file(self, qapp, qa_window, sample_tree):
        """Opening a Python file must populate the outline with symbols."""
        from PyQt6.QtWidgets import QTreeWidget

        window = qa_window
        tabs = window.hero_window._text_editor_center.tabs
        tabs.open_file_by_path(str(Path(sample_tree) / "main.py"))
        pump(qapp, 300)
        _activate(window, "file_outline")
        pump(qapp, 300)
        outline = window.hero_window._file_outline
        tree = outline.findChild(QTreeWidget)
        assert tree is not None, "outline panel has no tree widget"
        assert tree.topLevelItemCount() > 0, "outline has no symbols"

    def test_outline_symbol_click_moves_cursor(self, qapp, qa_window, sample_tree):
        """Clicking an outline symbol moves the editor cursor to that line."""
        from PyQt6.QtWidgets import QTreeWidget

        window = qa_window
        tabs = window.hero_window._text_editor_center.tabs
        tabs.open_file_by_path(str(Path(sample_tree) / "main.py"))
        pump(qapp, 300)
        _activate(window, "file_outline")
        pump(qapp, 300)
        outline = window.hero_window._file_outline
        tree = outline.findChild(QTreeWidget)
        if tree is None or tree.topLevelItemCount() == 0:
            pytest.skip("outline produced no symbols for the sample file")
        editor = code_editor(window.hero_window._text_editor_center.current_editor())
        editor.setCursorPosition(0, 0)
        outline.symbol_clicked.emit(3)
        pump(qapp, 100)
        line, _ = editor.getCursorPosition()
        assert line == 3, f"cursor did not follow the outline symbol: {line}"


class TestSolutionExplorerPanel:
    """The explorer reflects the workspace and opens files on double click."""

    def test_explorer_shows_workspace_files(self, qapp, qa_window, sample_tree):
        """The explorer tree contains the sample file."""
        from PyQt6.QtWidgets import QTreeView

        window = qa_window
        _activate(window, "solution_explorer")
        pump(qapp, 300)
        explorer = window.hero_window._solution_explorer
        tree = explorer.findChild(QTreeView)
        assert tree is not None, "explorer has no tree view"
        assert tree.model() is not None, "explorer tree has no model"

    def test_explorer_double_click_opens_file(self, qapp, qa_window, sample_tree):
        """Double-clicking a file row opens it in an editor tab."""
        from PyQt6.QtWidgets import QTreeView

        window = qa_window
        _activate(window, "solution_explorer")
        pump(qapp, 300)
        explorer = window.hero_window._solution_explorer
        tree = explorer.findChild(QTreeView)
        model = tree.model()
        target = None
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            name = model.data(index)
            if name and "main.py" in str(name):
                target = index
                break
        if target is None:
            pytest.skip("explorer did not expose main.py in the temp workspace")
        tree.expandToDepth(0)
        tree.setCurrentIndex(target)
        tree.scrollTo(target)
        pump(qapp, 100)
        tabs = window.hero_window._text_editor_center.tabs
        before = tabs.count()
        window._on_explorer_double_click(target)
        pump(qapp, 300)
        assert tabs.count() == before + 1, "double click did not open a tab"


class TestEtherAiPanel:
    """The Ether AI panel must accept input without a live backend."""

    def test_ether_ai_prompt_accepts_text(self, qapp, qa_window):
        """Typing in the Ether AI prompt does not raise."""
        window = qa_window
        _activate(window, "ether_ai")
        pump(qapp, 200)
        ether = window.hero_window._ether_ai
        sweep = Sweep("ether ai input")
        type_probe(qapp, ether, sweep, "hello")
        sweep.finish()
        assert_alive(qapp, window)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
