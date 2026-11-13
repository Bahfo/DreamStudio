"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Layout live tests: the DreamStudio chrome must stay stacked, keep its
configured widths, and survive side-panel and resize transitions.
"""

import pytest

from harness import (
    assert_positive_size,
    assert_regions_disjoint,
    live_probe,
    pump,
    resize_stress,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

SIDEBAR_MIN_WIDTH = 30
SIDEBAR_MAX_WIDTH = 80
PANEL_MIN_WIDTH = 150


def _chrome_regions(window) -> dict:
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


class TestChromeStacking:
    """Title, options, hero, and status regions stay stacked."""

    def test_chrome_disjoint_at_rest(self, qapp, qa_window):
        """At rest, no two chrome regions overlap."""
        assert_regions_disjoint(_chrome_regions(qa_window))

    def test_chrome_disjoint_after_left_panel_opens(self, qapp, qa_window):
        """Opening the left panel must not disturb the chrome stacking."""
        window = qa_window
        window.hero_window._vertical_menus_api.activate_panel("solution_explorer")
        pump(qapp, 100)
        assert_regions_disjoint(_chrome_regions(window))

    def test_chrome_disjoint_after_right_panel_opens(self, qapp, qa_window):
        """Opening the right panel must not disturb the chrome stacking."""
        window = qa_window
        window.hero_window._vertical_menus_api.activate_panel("ether_ai")
        pump(qapp, 100)
        assert_regions_disjoint(_chrome_regions(window))

    def test_chrome_disjoint_with_every_panel_open(self, qapp, qa_window):
        """With all panels open, the chrome still stacks cleanly."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        for panel_id in (
            "solution_explorer",
            "source_control",
            "file_outline",
            "properties",
            "todo_search",
            "server_explorer",
            "notifications",
            "ether_ai",
        ):
            api.activate_panel(panel_id)
        pump(qapp, 200)
        assert_regions_disjoint(_chrome_regions(window))
        assert_positive_size(window.hero_window._text_editor_center, "editor center")

    def test_status_bar_below_hero(self, qapp, qa_window):
        """The status bar sits below the hero region in the window."""
        window = qa_window
        hero_bottom = window.hero_window.mapTo(
            window, window.hero_window.rect().bottomLeft()
        ).y()
        status_top = window.status_bar.mapTo(
            window, window.status_bar.rect().topLeft()
        ).y()
        assert (
            status_top >= hero_bottom - 1
        ), f"status bar overlaps hero (status top {status_top}, hero bottom {hero_bottom})"


class TestSidebarWidths:
    """Sidebars keep their configured width while visible."""

    def test_sidebar_bars_keep_narrow_width(self, qapp, qa_window):
        """Left and right vertical bars stay within their configured width."""
        window = qa_window
        for name in ("left_sidebar", "right_sidebar"):
            sidebar = getattr(window, name)
            assert_positive_size(sidebar, name)
            assert (
                SIDEBAR_MIN_WIDTH <= sidebar.width() <= SIDEBAR_MAX_WIDTH
            ), f"{name} width {sidebar.width()} outside configured range"

    def test_left_panel_manager_keeps_width(self, qapp, qa_window):
        """The left panel manager keeps a usable width when a panel is open."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        api.activate_panel("solution_explorer")
        pump(qapp, 100)
        manager = window.hero_window._left_utils_manager
        assert manager.isVisible(), "left panel manager not visible"
        assert (
            manager.width() >= PANEL_MIN_WIDTH
        ), f"left panel manager too narrow: {manager.width()}"

    def test_right_panel_manager_keeps_width(self, qapp, qa_window):
        """The right panel manager keeps a usable width when a panel is open."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        api.activate_panel("properties")
        pump(qapp, 100)
        manager = window.hero_window._right_utils_manager
        assert manager.isVisible(), "right panel manager not visible"
        assert (
            manager.width() >= PANEL_MIN_WIDTH
        ), f"right panel manager too narrow: {manager.width()}"

    def test_editor_keeps_positive_size(self, qapp, qa_window):
        """The editor center stays positive with both side panels open."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        api.activate_panel("solution_explorer")
        api.activate_panel("ether_ai")
        pump(qapp, 150)
        editor_center = window.hero_window._text_editor_center
        assert_positive_size(editor_center, "editor center")
        assert (
            editor_center.width() > 100
        ), f"editor center squeezed to {editor_center.width()}"


class TestDockLayout:
    """The lower dock collapses and expands with the vertical splitter."""

    def test_lower_splitter_expands_with_dock(self, qapp, qa_window):
        """Showing the terminal gives the lower splitter a positive size."""
        window = qa_window
        splitter = window.hero_window._main_vertical_splitter
        window._toggle_terminal()
        pump(qapp, 150)
        sizes = splitter.sizes()
        assert sizes[-1] > 0, f"lower splitter has no height: {sizes}"
        assert window.hero_window._lower_widget.isVisible(), "dock not visible"

    def test_lower_splitter_collapses_when_hidden(self, qapp, qa_window):
        """Hiding the terminal collapses the lower splitter again."""
        window = qa_window
        splitter = window.hero_window._main_vertical_splitter
        window._toggle_terminal()
        pump(qapp, 150)
        window._toggle_terminal()
        pump(qapp, 150)
        sizes = splitter.sizes()
        assert sizes[-1] == 0, f"lower splitter did not collapse: {sizes}"


class TestResizeStress:
    """Resizing the window never breaks geometry."""

    def test_resize_stress_has_no_zero_size_widgets(self, qapp, qa_window):
        """Minimum, huge, and restored sizes keep every visible widget sized."""
        issues = resize_stress(qapp, qa_window)
        assert not issues, "geometry issues during resize:\n" + "\n".join(issues)

    def test_resize_stress_keeps_chrome_disjoint(self, qapp, qa_window):
        """Chrome regions stay disjoint at every tested size."""
        window = qa_window
        for width, height in ((320, 240), (1920, 1080), (1280, 800)):
            window.resize(width, height)
            pump(qapp, 100)
            assert_regions_disjoint(_chrome_regions(window))

    def test_live_probe_clean_after_side_open(self, qapp, qa_window):
        """No visible widget collapses to zero size when a panel opens."""
        window = qa_window
        window.hero_window._vertical_menus_api.activate_panel("source_control")
        pump(qapp, 150)
        issues = live_probe(window)
        assert not issues, "zero-size visible widgets:\n" + "\n".join(issues)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
