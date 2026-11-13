"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Adversarial interaction live tests: overlapping panel, editor, dock, and
resize interactions must leave the window in a consistent state.
"""

from pathlib import Path

import pytest

from harness import (
    assert_alive,
    assert_positive_size,
    assert_regions_disjoint,
    code_editor,
    focus_walk,
    live_probe,
    pump,
    race_probe,
    resize_stress,
    type_text,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

ALL_PANELS = (
    "solution_explorer",
    "source_control",
    "file_outline",
    "properties",
    "todo_search",
    "server_explorer",
    "notifications",
    "ether_ai",
)


def _chrome(window) -> dict:
    """Collect the chrome regions that must never overlap.

    Args:
        window: The DreamStudio main window.

    Returns:
        Mapping of region name to widget.
    """
    return {
        "title_bar": window.title_bar,
        "options_bar": window.options_menu,
        "status_bar": window.status_bar,
    }


class TestPanelCombinations:
    """Opening many panels at once stays consistent."""

    def test_all_panels_open_together(self, qapp, qa_window):
        """All eight panels can be open at the same time."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        for panel_id in ALL_PANELS:
            api.activate_panel(panel_id)
        pump(qapp, 300)
        for panel_id in ALL_PANELS:
            assert api.is_visible(panel_id), f"panel '{panel_id}' not visible"
        assert_positive_size(window.hero_window._text_editor_center, "editor center")
        assert_regions_disjoint(_chrome(window))

    def test_all_panels_closed_together(self, qapp, qa_window):
        """Closing every panel collapses both sidebars again."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        for panel_id in ALL_PANELS:
            api.activate_panel(panel_id)
        pump(qapp, 250)
        for panel_id in ALL_PANELS:
            api.deactivate_panel(panel_id)
        pump(qapp, 250)
        for panel_id in ALL_PANELS:
            assert not api.is_visible(panel_id), f"panel '{panel_id}' still visible"

    def test_panels_open_together_have_no_zero_size_widgets(self, qapp, qa_window):
        """No visible widget collapses while every panel is open."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        for panel_id in ALL_PANELS:
            api.activate_panel(panel_id)
        pump(qapp, 300)
        issues = live_probe(window)
        assert not issues, "zero-size visible widgets:\n" + "\n".join(issues)

    def test_panel_toggle_storm_ends_consistent(self, qapp, qa_window):
        """Rapid panel toggles end in a state matching the panel flags."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        for panel_id in ("solution_explorer", "properties"):
            api.activate_panel(panel_id)
        pump(qapp, 200)

        def cycle() -> None:
            """Toggle two panels in sequence.

            Returns:
                None; the side effect is the two panel toggles.
            """
            api.deactivate_panel("solution_explorer")
            api.activate_panel("solution_explorer")
            api.deactivate_panel("properties")
            api.activate_panel("properties")

        race_probe(qapp, cycle, 3)
        pump(qapp, 250)
        assert api.is_visible("solution_explorer"), "explorer visibility diverged"
        assert api.is_visible("properties"), "properties visibility diverged"


class TestEditorCombinations:
    """Typing while the UI changes stays consistent."""

    def test_typing_while_panel_toggles(self, qapp, qa_window, sample_tree):
        """Typing in the editor while a panel toggles never raises."""
        window = qa_window
        tabs = window.hero_window._text_editor_center.tabs
        tabs.open_file_by_path(str(Path(sample_tree) / "main.py"))
        pump(qapp, 300)
        editor = code_editor(window.hero_window._text_editor_center.current_editor())
        editor.setCursorPosition(0, 0)
        api = window.hero_window._vertical_menus_api

        def type_char() -> None:
            """Type a character into the editor.

            Returns:
                None; the side effect is the inserted character.
            """
            type_text(qapp, editor, "x")

        def toggle_panel() -> None:
            """Toggle the properties panel visibility.

            Returns:
                None; the side effect is the panel toggle.
            """
            api.deactivate_panel("properties")
            api.activate_panel("properties")

        race_probe(qapp, type_char, 3)
        race_probe(qapp, toggle_panel, 3)
        pump(qapp, 300)
        assert_alive(qapp, window)
        assert "x" in editor.text(), "typed characters were lost"

    def test_open_close_storm_leaves_one_tab(self, qapp, qa_window, sample_tree):
        """Opening and closing the same file repeatedly leaves one tab."""
        window = qa_window
        tabs = window.hero_window._text_editor_center.tabs
        target = str(Path(sample_tree) / "main.py")

        def cycle() -> None:
            """Open the sample file and close the active tab.

            Returns:
                None; the side effect is the opened and closed tab.
            """
            tabs.open_file_by_path(target)
            pump(qapp, 40)
            tabs.close_tab()
            pump(qapp, 40)

        race_probe(qapp, cycle, 5)
        tabs.open_file_by_path(target)
        pump(qapp, 300)
        assert tabs.count() == 1, f"expected one tab, got {tabs.count()}"

    def test_two_files_open_rapidly_keeps_both(self, qapp, qa_window, sample_tree):
        """Opening two files quickly keeps both tabs."""
        window = qa_window
        tabs = window.hero_window._text_editor_center.tabs
        first = str(Path(sample_tree) / "main.py")
        second = str(Path(sample_tree) / "helpers.py")
        tabs.open_file_by_path(first)
        pump(qapp, 50)
        tabs.open_file_by_path(second)
        pump(qapp, 400)
        assert tabs.count() == 2, f"expected two tabs, got {tabs.count()}"


class TestDockCombinations:
    """Dock toggles during background work stay consistent."""

    def test_terminal_toggle_storm_with_analysis_running(self, qapp, qa_window):
        """Toggling the dock while analysis runs keeps the splitter sane."""
        window = qa_window
        splitter = window.hero_window._main_vertical_splitter
        race_probe(qapp, window._toggle_terminal, 6)
        pump(qapp, 800)
        assert_alive(qapp, window)
        sizes = splitter.sizes()
        assert sizes[-1] >= 0, f"negative dock size: {sizes}"

    def test_problems_and_terminal_storm(self, qapp, qa_window):
        """Switching between Problems and the terminal stays consistent."""
        window = qa_window
        dock = window.hero_window._lower_widget

        def cycle() -> None:
            """Switch the dock between Problems and the terminal.

            Returns:
                None; the side effect is the dock stack switch.
            """
            window._toggle_problems()
            window._toggle_terminal()

        race_probe(qapp, cycle, 4)
        pump(qapp, 400)
        assert_alive(qapp, window)
        assert dock._stack.currentWidget() is not None, "dock has no active entry"


class TestResizeCombinations:
    """Resizing during interaction stays consistent."""

    def test_resize_with_panels_open(self, qapp, qa_window):
        """Resizing with open panels keeps the editor positive."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        api.activate_panel("solution_explorer")
        api.activate_panel("ether_ai")
        pump(qapp, 250)
        issues = resize_stress(qapp, window)
        assert not issues, "geometry issues during resize:\n" + "\n".join(issues)
        assert_positive_size(window.hero_window._text_editor_center, "editor center")

    def test_resize_with_dock_open(self, qapp, qa_window):
        """Resizing with the dock open keeps the splitter sane."""
        window = qa_window
        window._toggle_terminal()
        pump(qapp, 250)
        issues = resize_stress(qapp, window)
        assert not issues, "geometry issues during resize:\n" + "\n".join(issues)
        sizes = window.hero_window._main_vertical_splitter.sizes()
        assert sizes[-1] > 0, f"dock lost its space while resizing: {sizes}"


class TestFocusCombinations:
    """Focus traversal does not get stuck."""

    def test_focus_walk_through_the_window(self, qapp, qa_window):
        """Tab traversal through the whole window keeps moving focus."""
        issues = focus_walk(qapp, qa_window, max_tabs=40)
        assert not issues, "focus walk problems:\n" + "\n".join(issues)

    def test_focus_walk_with_panels_open(self, qapp, qa_window):
        """Tab traversal still moves with the panels open."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        api.activate_panel("solution_explorer")
        api.activate_panel("properties")
        pump(qapp, 250)
        issues = focus_walk(qapp, window, max_tabs=40)
        assert not issues, "focus walk problems:\n" + "\n".join(issues)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
