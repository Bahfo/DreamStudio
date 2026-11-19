"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Float/dock live tests: a side panel must open in a standalone top-level
window, keep working while it is detached, and return to the exact slot it
was registered in when the float button is pressed again.
"""

import pytest

from harness import assert_alive, click, live_probe, pump

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

FLOAT_TOOLTIP = "Float Tool Window"
DOCK_TOOLTIP = "Dock Tool Window"


def _panel_widget(window, panel_id: str):
    """Return the panel shell registered under *panel_id*.

    Args:
        window: The DreamStudio main window.
        panel_id: Registered panel identifier.

    Returns:
        The ``PanelShell`` instance.
    """
    return window.hero_window._vertical_menus_api._widgets[panel_id]


def _manager(window, panel_id: str):
    """Return the side stack that hosts *panel_id*.

    Args:
        window: The DreamStudio main window.
        panel_id: Registered panel identifier.

    Returns:
        The ``UtilityTabManager`` instance.
    """
    return window.hero_window._vertical_menus_api._tab_managers[panel_id]


def _tab_index(window, panel_id: str) -> int:
    """Return the tab index of *panel_id* inside its side stack.

    Args:
        window: The DreamStudio main window.
        panel_id: Registered panel identifier.

    Returns:
        The tab index, or ``-1`` when the panel is not registered.
    """
    return _manager(window, panel_id)._panel_ids.index(panel_id)


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


class TestPanelFloatBasics:
    """The float button detaches a panel into a top-level window."""

    def test_float_button_opens_top_level_window(self, qapp, qa_window):
        """Clicking the float button creates a visible top-level window."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)

        assert not panel.is_floating, "panel must start docked"
        assert panel._float_window is None, "a docked panel owns no float window"

        click(qapp, panel.undock_btn)
        pump(qapp, 120)

        assert panel.is_floating, "panel did not enter the floating state"
        assert panel._float_window is not None, "no floating window was created"
        assert panel._float_window.isWindow(), "floating panel is not a top-level window"
        assert panel._float_window.isVisible(), "floating window is not visible"

    def test_float_button_toggles_tooltip_and_icon(self, qapp, qa_window):
        """The float button advertises the action it will perform next."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)

        assert panel.undock_btn.toolTip() == FLOAT_TOOLTIP

        click(qapp, panel.undock_btn)
        pump(qapp, 120)
        assert panel.undock_btn.toolTip() == DOCK_TOOLTIP

        click(qapp, panel.undock_btn)
        pump(qapp, 120)
        assert panel.undock_btn.toolTip() == FLOAT_TOOLTIP

    def test_float_hides_the_side_tab(self, qapp, qa_window):
        """A floating panel no longer occupies a tab in its side stack."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)
        manager = _manager(window, "solution_explorer")
        index = _tab_index(window, "solution_explorer")
        assert manager._tab_bar.isTabVisible(index)

        click(qapp, panel.undock_btn)
        pump(qapp, 120)

        assert not manager._tab_bar.isTabVisible(index), "the side tab must be hidden while the panel floats"

    def test_float_window_carries_the_panel_frame(self, qapp, qa_window):
        """The floating window hosts the very same frame the side stack held."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)

        frame = panel._frame
        click(qapp, panel.undock_btn)
        pump(qapp, 120)

        assert panel._float_window is not None
        assert (
            frame.parentWidget() is panel._float_window
        ), "the panel frame was not reparented into the floating window"


class TestPanelDockReturn:
    """Docking returns the panel to the slot it was registered in."""

    def test_dock_restores_the_original_tab(self, qapp, qa_window):
        """The panel returns to the tab it came from, not to another slot."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)
        manager = _manager(window, "solution_explorer")
        index = _tab_index(window, "solution_explorer")
        stack_index = manager._stack.indexOf(panel)

        click(qapp, panel.undock_btn)
        pump(qapp, 120)
        click(qapp, panel.undock_btn)
        pump(qapp, 120)

        assert not panel.is_floating, "panel did not return to the docked state"
        assert panel._float_window is None, "the floating window was not released"
        assert manager._stack.indexOf(panel) == stack_index, "the panel changed its slot in the side stack"
        assert manager._tab_bar.isTabVisible(index), "the side tab was not restored"

    def test_dock_returns_the_frame_to_the_panel(self, qapp, qa_window):
        """The frame is reparented back into the panel shell."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)
        frame = panel._frame

        click(qapp, panel.undock_btn)
        pump(qapp, 120)
        click(qapp, panel.undock_btn)
        pump(qapp, 120)

        assert frame.parentWidget() is panel, "the panel frame was not returned to the panel shell"

    def test_float_dock_cycle_is_stable(self, qapp, qa_window):
        """Repeated float/dock cycles keep the panel in the same slot."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)
        manager = _manager(window, "solution_explorer")
        stack_index = manager._stack.indexOf(panel)

        for _ in range(3):
            click(qapp, panel.undock_btn)
            pump(qapp, 80)
            assert panel.is_floating
            click(qapp, panel.undock_btn)
            pump(qapp, 80)
            assert not panel.is_floating
            assert manager._stack.indexOf(panel) == stack_index

        assert_alive(qapp, window)

    def test_window_manager_close_docks_the_panel(self, qapp, qa_window):
        """Closing the floating window docks the panel back into the IDE."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)
        manager = _manager(window, "solution_explorer")
        index = _tab_index(window, "solution_explorer")

        click(qapp, panel.undock_btn)
        pump(qapp, 120)
        float_window = panel._float_window
        assert float_window is not None

        float_window.close()
        pump(qapp, 120)

        assert not panel.is_floating, "the panel stayed detached after the window closed"
        assert panel._float_window is None, "the closed float window is still tracked"
        assert manager._tab_bar.isTabVisible(index), "the side tab was not restored"


class TestPanelFloatBehaviour:
    """A floating panel keeps working and never leaves its origin behind."""

    def test_floating_panel_keeps_its_content(self, qapp, qa_window, sample_tree):
        """The explorer tree stays populated while the panel floats."""
        from PyQt6.QtWidgets import QTreeView

        window = qa_window
        _activate(window, "solution_explorer")
        pump(qapp, 200)
        panel = _panel_widget(window, "solution_explorer")
        tree = panel.findChild(QTreeView)
        assert tree is not None, "explorer has no tree view"

        click(qapp, panel.undock_btn)
        pump(qapp, 200)

        assert tree.model() is not None, "the explorer lost its model while floating"
        assert tree.isVisibleTo(
            panel._float_window
        ), "the explorer tree is not visible inside the floating window"

    def test_floating_panel_has_no_zero_size_children(self, qapp, qa_window):
        """The floating window contains no visible zero-sized widgets."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 150)

        click(qapp, panel.undock_btn)
        pump(qapp, 150)

        issues = live_probe(panel._float_window)
        assert not issues, "the floating window has broken widgets:\n" + "\n".join(issues)

    def test_floating_window_inherits_the_ide_theme(self, qapp, qa_window):
        """The floating window is painted with the IDE's global stylesheet."""
        from PyQt6.QtGui import QPalette

        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 150)
        expected = window.palette().color(QPalette.ColorRole.Window)

        click(qapp, panel.undock_btn)
        pump(qapp, 150)

        actual = panel._float_window.palette().color(QPalette.ColorRole.Window)
        assert (
            actual == expected
        ), f"the floating window lost the IDE theme: {actual.name()} != {expected.name()}"

    def test_floating_panel_keeps_the_ide_alive(self, qapp, qa_window):
        """Floating and docking a panel never hides the main window."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)

        click(qapp, panel.undock_btn)
        pump(qapp, 120)
        assert window.isVisible(), "the main window vanished while a panel floated"

        click(qapp, panel.undock_btn)
        pump(qapp, 120)
        assert_alive(qapp, window)

    def test_two_panels_can_float_independently(self, qapp, qa_window):
        """Left and right panels float without colliding."""
        window = qa_window
        left = _panel_widget(window, "solution_explorer")
        right = _panel_widget(window, "properties")
        _activate(window, "solution_explorer")
        _activate(window, "properties")
        pump(qapp, 150)

        click(qapp, left.undock_btn)
        pump(qapp, 120)
        click(qapp, right.undock_btn)
        pump(qapp, 120)

        assert left.is_floating, "the left panel did not float"
        assert right.is_floating, "the right panel did not float"
        assert left._float_window is not right._float_window, "both panels share one floating window"

        click(qapp, left.undock_btn)
        click(qapp, right.undock_btn)
        pump(qapp, 120)
        assert not left.is_floating
        assert not right.is_floating
        assert_alive(qapp, window)

    def test_closing_a_floating_panel_docks_it_first(self, qapp, qa_window):
        """The header close button docks the panel and then closes it."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)
        closed = []
        panel.close_requested.connect(lambda: closed.append(True))

        click(qapp, panel.undock_btn)
        pump(qapp, 120)
        click(qapp, panel.close_btn)
        pump(qapp, 120)

        assert not panel.is_floating, "the closed panel stayed detached"
        assert panel._float_window is None, "the closed panel kept its float window"
        assert closed, "close_requested was not emitted"
        assert_alive(qapp, window)

    def test_deactivating_a_floating_panel_docks_it(self, qapp, qa_window):
        """Deactivating a floating panel through the API docks it back."""
        window = qa_window
        panel = _panel_widget(window, "solution_explorer")
        _activate(window, "solution_explorer")
        pump(qapp, 120)

        click(qapp, panel.undock_btn)
        pump(qapp, 120)
        _deactivate(window, "solution_explorer")
        pump(qapp, 120)

        assert not panel.is_floating, "the deactivated panel stayed detached"
        assert panel._float_window is None, "the deactivated panel kept its float window"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
