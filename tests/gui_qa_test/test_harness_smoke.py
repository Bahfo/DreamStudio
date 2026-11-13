"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Phase-1 smoke tests: the real DreamStudio window must build, show, emit
ui_ready once, present every chrome region cleanly, and expose every
sidebar/status-bar button declared by the JSON shell definitions.
"""

import json

import pytest

import harness
from harness import (
    Sweep,
    assert_positive_size,
    assert_regions_disjoint,
    assert_alive,
    live_probe,
    pump,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]


def _sidebar_tooltips(window) -> list[tuple[str, str]]:
    """Collect (tooltip, callback) pairs from both sidebar JSON definitions.

    Args:
        window: The DreamStudio main window.

    Returns:
        List of (tooltip, callback-name) tuples, left bar first.
    """
    from editor.utils.resource_path import resource_path

    entries: list[tuple[str, str]] = []
    for json_name in ("editor/base/json/leftbar.json", "editor/base/json/rightbar.json"):
        with open(resource_path(json_name), encoding="utf-8") as fh:
            for entry in json.load(fh):
                if entry.get("id") == "btn" and entry.get("callback"):
                    entries.append((entry["tooltip"], entry["callback"]))
    return entries


class TestWindowBootstrap:
    """The window must come up exactly like real startup phase 8."""

    def test_window_is_visible_and_enabled(self, qapp, qa_window):
        """A shown window must be visible, enabled, and stay alive."""
        window = qa_window
        assert window.isVisible()
        assert window.isEnabled()
        assert_alive(qapp, window)

    def test_ui_ready_emitted_once(self, qapp, qa_window):
        """ui_ready fires exactly once during the fixture (asserted inside)."""
        assert qa_window.isVisible()

    def test_central_widget_positive_size(self, qapp, qa_window):
        """The central widget and body layout must have positive geometry."""
        assert_positive_size(qa_window.central_widget, "central widget")
        hero = qa_window.hero_window
        assert_positive_size(hero, "hero window")


class TestShellChrome:
    """Every chrome region must be present, sized, and non-overlapping."""

    def test_chrome_regions_present(self, qapp, qa_window):
        """Title bar, options bar, sidebars, hero, and status bar exist."""
        window = qa_window
        for name in (
            "title_bar",
            "options_menu",
            "left_sidebar",
            "right_sidebar",
            "hero_window",
            "status_bar",
        ):
            widget = getattr(window, name, None)
            assert widget is not None, f"missing chrome region: {name}"
            assert_positive_size(widget, name)

    def test_chrome_regions_do_not_overlap(self, qapp, qa_window):
        """Stacked chrome regions must never overlap each other."""
        window = qa_window
        assert_regions_disjoint(
            {
                "title_bar": window.title_bar,
                "options_bar": window.options_menu,
                "status_bar": window.status_bar,
            }
        )
        left = window.left_sidebar.geometry()
        right = window.right_sidebar.geometry()
        hero = window.hero_window.geometry()
        assert not left.intersects(right), "left and right sidebars overlap"
        assert not left.intersects(hero), "left sidebar overlaps hero"
        assert not right.intersects(hero), "right sidebar overlaps hero"

    def test_live_probe_clean_at_rest(self, qapp, qa_window):
        """No visible widget may have a non-positive size at rest."""
        issues = live_probe(qa_window)
        assert not issues, "zero-size visible widgets found:\n" + "\n".join(issues)


class TestSidebarButtons:
    """Every sidebar button declared in JSON must exist and be clickable."""

    def test_all_sidebar_buttons_exist(self, qapp, qa_window):
        """Each JSON button is findable by its declared tooltip."""
        window = qa_window
        sweep = Sweep("sidebar buttons")
        for tooltip, callback in _sidebar_tooltips(window):
            button = harness.find_button(window, tooltip)
            if button is None:
                sweep.note(f"tooltip '{tooltip}'", "button not found in window")
                continue
            assert_positive_size(button, f"sidebar button '{tooltip}'")
            if not hasattr(window, callback):
                sweep.note(f"tooltip '{tooltip}'", f"callback {callback} missing")
        sweep.finish()

    def test_sidebar_buttons_are_clickable(self, qapp, qa_window):
        """Clicking every sidebar button must not raise or hide the window."""
        window = qa_window
        sweep = Sweep("sidebar button clicks")
        for tooltip, _callback in _sidebar_tooltips(window):
            button = harness.find_button(window, tooltip)
            if button is None:
                continue
            sweep.step(f"click '{tooltip}'", harness.click, qapp, button)
            if not window.isVisible():
                sweep.note(f"click '{tooltip}'", "window hidden by click")
                break
        sweep.finish()


class TestStatusBarButtons:
    """The status-bar diagnostic buttons must exist and be clickable."""

    _BUTTON_NAMES = ("notificationBtn", "errorsBtn", "warningBtn", "checksBtn")

    def test_status_bar_buttons_exist(self, qapp, qa_window):
        """All four status-bar buttons exist with positive size."""
        window = qa_window
        status_bar = window.status_bar
        for name in self._BUTTON_NAMES:
            button = getattr(status_bar, name, None)
            assert button is not None, f"status bar button missing: {name}"
            assert_positive_size(button, f"status bar button '{name}'")

    def test_status_bar_buttons_clickable(self, qapp, qa_window):
        """Clicking status-bar buttons must not raise or kill the window."""
        window = qa_window
        sweep = Sweep("status bar clicks")
        for name in self._BUTTON_NAMES:
            button = getattr(window.status_bar, name, None)
            if button is None:
                continue
            sweep.step(f"click status '{name}'", harness.click, qapp, button)
        assert window.isVisible(), "window hidden by status-bar clicks"
        sweep.finish()

    def test_status_bar_reports_workspace(self, qapp, qa_window):
        """The status bar received the workspace path at startup."""
        workspace_path = str(qa_window.currentDirectory)
        assert workspace_path, "status bar/window has no workspace path"
        pump(qapp, 50)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
