"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Bottom dock live tests: the UtilsContainer stack, the terminal panel, and the
Problems panel of the real DreamStudio window.
"""

import pytest

from harness import (
    Sweep,
    assert_alive,
    assert_positive_size,
    click,
    live_probe,
    poke,
    pump,
    race_probe,
    type_text,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]


def _dock(window):
    """Return the lower UtilsContainer of the window.

    Args:
        window: The DreamStudio main window.

    Returns:
        The UtilsContainer instance.
    """
    return window.hero_window._lower_widget


class TestDockStack:
    """The dock stack keeps terminal at 0 and Problems at 1."""

    def test_stack_order_is_terminal_then_problems(self, qapp, qa_window):
        """The dock stack index 0 is the terminal and 1 is Problems."""
        dock = _dock(qa_window)
        assert dock._stack.count() >= 2, "dock stack has fewer than two entries"
        assert dock._stack.widget(0) is dock.terminal_window, (
            "stack index 0 is not the terminal"
        )
        assert dock._stack.widget(1) is dock.problems_window, (
            "stack index 1 is not the Problems panel"
        )

    def test_terminal_toggle_shows_terminal(self, qapp, qa_window):
        """Toggling the terminal shows the dock with the terminal selected."""
        window = qa_window
        dock = _dock(window)
        window._toggle_terminal()
        pump(qapp, 200)
        assert dock.isVisible(), "dock not visible after terminal toggle"
        assert dock._stack.currentWidget() is dock.terminal_window, (
            "terminal not the active stack entry"
        )

    def test_problems_toggle_shows_problems(self, qapp, qa_window):
        """Toggling Problems shows the dock with Problems selected."""
        window = qa_window
        dock = _dock(window)
        window._toggle_problems()
        pump(qapp, 200)
        assert dock.isVisible(), "dock not visible after problems toggle"
        assert dock._stack.currentWidget() is dock.problems_window, (
            "Problems not the active stack entry"
        )

    def test_lower_splitter_matches_dock_visibility(self, qapp, qa_window):
        """The vertical splitter gives space to the dock only while shown."""
        window = qa_window
        splitter = window.hero_window._main_vertical_splitter
        window._toggle_terminal()
        pump(qapp, 200)
        assert splitter.sizes()[-1] > 0, "dock shown but splitter has no space"
        window._toggle_terminal()
        pump(qapp, 200)
        assert splitter.sizes()[-1] == 0, "dock hidden but splitter kept space"


class TestTerminalPanel:
    """The terminal panel accepts commands without crashing the IDE."""

    def test_terminal_has_positive_size_when_shown(self, qapp, qa_window):
        """The terminal widget is sized when the dock is open."""
        window = qa_window
        window._toggle_terminal()
        pump(qapp, 200)
        assert_positive_size(_dock(window).terminal_window, "terminal panel")

    def test_terminal_accepts_typed_command(self, qapp, qa_window):
        """Typing a benign command into the terminal does not raise."""
        window = qa_window
        window._toggle_terminal()
        pump(qapp, 200)
        terminal = _dock(window).terminal_window
        sweep = Sweep("terminal typing")
        sweep.step("type echo", type_text, qapp, terminal, "echo qa")
        sweep.finish()
        assert_alive(qapp, window)

    def test_terminal_button_poke_is_clean(self, qapp, qa_window):
        """Poking terminal buttons records no failure."""
        window = qa_window
        window._toggle_terminal()
        pump(qapp, 200)
        sweep = Sweep("terminal poke")
        poke(qapp, _dock(window).terminal_window, sweep)
        sweep.finish()
        assert_alive(qapp, window)


class TestProblemsPanel:
    """The Problems panel renders with and without diagnostics."""

    def test_problems_panel_has_positive_size_when_shown(self, qapp, qa_window):
        """The Problems widget is sized when the dock is open."""
        window = qa_window
        window._toggle_problems()
        pump(qapp, 200)
        assert_positive_size(_dock(window).problems_window, "problems panel")

    def test_problems_counts_are_readable(self, qapp, qa_window):
        """The Problems panel reports a problem-count triple."""
        window = qa_window
        counts = _dock(window).problems_window.problem_counts()
        assert len(counts) == 3, f"unexpected problem-count shape: {counts}"
        assert all(isinstance(value, int) for value in counts), (
            f"problem counts are not integers: {counts}"
        )

    def test_problems_panel_poke_is_clean(self, qapp, qa_window):
        """Poking Problems-panel buttons records no failure."""
        window = qa_window
        window._toggle_problems()
        pump(qapp, 200)
        sweep = Sweep("problems poke")
        poke(qapp, _dock(window).problems_window, sweep)
        sweep.finish()
        assert_alive(qapp, window)

    def test_problems_filter_groups_switch(self, qapp, qa_window):
        """Switching the Problems filter group changes the visible group."""
        window = qa_window
        problems = _dock(window).problems_window
        problems.show_group("errors")
        pump(qapp, 100)
        assert problems.filter_group() == "errors", (
            f"filter group not applied: {problems.filter_group()}"
        )
        problems.show_all_groups()
        pump(qapp, 100)
        assert problems.filter_group() not in ("errors",), (
            f"show_all_groups did not clear the filter: {problems.filter_group()}"
        )


class TestDockRaces:
    """Rapid dock toggles must end in a consistent state."""

    def test_toggle_storm_ends_consistent(self, qapp, qa_window):
        """After a toggle storm the dock state matches the stack selection."""
        window = qa_window
        dock = _dock(window)
        race_probe(qapp, window._toggle_terminal, 4)
        pump(qapp, 200)
        visible = dock.isVisible()
        current = dock._stack.currentWidget()
        if visible:
            assert current is not None, "dock visible without a stack selection"
        else:
            assert window.hero_window._main_vertical_splitter.sizes()[-1] == 0, (
                "dock hidden but the splitter kept its space"
            )

    def test_no_zero_size_widgets_after_storm(self, qapp, qa_window):
        """No visible widget collapses to zero size during a dock storm."""
        window = qa_window
        race_probe(qapp, window._toggle_problems, 4)
        pump(qapp, 200)
        issues = live_probe(window)
        assert not issues, "zero-size visible widgets:\n" + "\n".join(issues)

    def test_terminal_close_request_hides_dock(self, qapp, qa_window):
        """The terminal close request hides the dock and collapses it."""
        window = qa_window
        dock = _dock(window)
        window._toggle_terminal()
        pump(qapp, 200)
        dock.terminal_window.close_requested.emit()
        pump(qapp, 200)
        assert not dock.isVisible(), "dock still visible after close request"
        assert window.hero_window._main_vertical_splitter.sizes()[-1] == 0, (
            "splitter kept space after the dock was closed"
        )

    def test_clicking_dock_area_is_safe(self, qapp, qa_window):
        """Clicking inside the dock never raises or hides the window."""
        window = qa_window
        window._toggle_terminal()
        pump(qapp, 200)
        sweep = Sweep("dock click")
        sweep.step("click dock", click, qapp, _dock(window))
        sweep.finish()
        assert_alive(qapp, window)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
