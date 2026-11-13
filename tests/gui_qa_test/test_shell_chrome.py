"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shell chrome live tests: title bar, options bar, sidebars, and status bar of
the real DreamStudio window, driven with QTest events.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness
from harness import (
    Sweep,
    assert_alive,
    assert_positive_size,
    click,
    find_button,
    live_probe,
    poke,
    pump,
    toggle_contract,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]


def _json_entries(json_name: str) -> list[dict]:
    """Load a shell JSON definition from the repository assets.

    Args:
        json_name: Resource path of the JSON file.

    Returns:
        List of parsed JSON entries.
    """
    from editor.utils.resource_path import resource_path

    with open(resource_path(json_name), encoding="utf-8") as fh:
        return json.load(fh)


def _sidebar_entries() -> list[tuple[str, str]]:
    """Return (tooltip, callback) pairs from both sidebar definitions.

    Returns:
        Left sidebar entries followed by right sidebar entries.
    """
    entries: list[tuple[str, str]] = []
    for name in ("editor/base/json/leftbar.json", "editor/base/json/rightbar.json"):
        for entry in _json_entries(name):
            if entry.get("id") == "btn" and entry.get("callback"):
                entries.append((entry["tooltip"], entry["callback"]))
    return entries


def _options_bar_buttons(window) -> list[tuple[str, object]]:
    """Return (tooltip, callback) pairs declared by the options bar JSON.

    Args:
        window: The DreamStudio main window.

    Returns:
        List of (tooltip, callback-value) tuples in declaration order.
    """
    entries = []
    for entry in _json_entries("editor/base/json/optionbar.json"):
        if entry.get("id") == "btn":
            entries.append((entry["tooltip"], entry.get("callback")))
    return entries


def _open_sample(qapp, window, workspace_path) -> None:
    """Open the sample file in the editor so edit operations have a target.

    Args:
        qapp: The live QApplication instance.
        window: The DreamStudio main window.
        workspace_path: Workspace root containing ``main.py``.
    """
    from pathlib import Path

    tabs = window.hero_window._text_editor_center.tabs
    tabs.open_file_by_path(str(Path(workspace_path) / "main.py"))
    pump(qapp, 100)


class TestTitleBar:
    """The title bar must render, size cleanly, and host safe controls."""

    def test_title_bar_present_and_sized(self, qapp, qa_window):
        """The title bar exists with positive size and a clean subtree."""
        assert_positive_size(qa_window.title_bar, "title bar")
        assert not live_probe(qa_window.title_bar)

    def test_control_buttons_exist(self, qapp, qa_window):
        """Minimize, maximize, and close controls exist (never clicked)."""
        title_bar = qa_window.title_bar
        for name in ("btn_minimize", "btn_maximize", "btn_close"):
            button = getattr(title_bar, name, None)
            assert button is not None, f"missing title-bar control: {name}"
            assert_positive_size(button, f"title-bar control '{name}'")

    def test_maximize_toggles_window_state(self, qapp, qa_window):
        """Clicking maximize changes state; clicking again restores it."""
        window = qa_window
        button = window.title_bar.btn_maximize
        normal = window.isMaximized()
        click(qapp, button)
        assert window.isMaximized() != normal, "maximize click changed nothing"
        click(qapp, button)
        assert window.isMaximized() == normal, "second click did not restore"
        assert_alive(qapp, window)

    def test_free_trial_button_clickable(self, qapp, qa_window):
        """The free-trial button clicks without raising or hiding the window."""
        button = qa_window.title_bar.free_trial_btn
        click(qapp, button)
        assert qa_window.isVisible(), "window hidden by free-trial click"

    def test_title_bar_search_field_present(self, qapp, qa_window):
        """The IDE search line edit exists and accepts typing."""
        search = qa_window.title_bar._ide_search
        assert_positive_size(search, "title-bar search field")
        harness.type_text(qapp, search, "qa")
        assert search.text() == "qa", "search field did not accept typing"


class TestOptionsBar:
    """Every options-bar button must exist and safe ones must click."""

    def test_all_declared_buttons_exist(self, qapp, qa_window):
        """Each optionbar.json button is findable by tooltip."""
        window = qa_window
        sweep = Sweep("options bar buttons")
        for tooltip, callback in _options_bar_buttons(window):
            button = find_button(window.options_menu, tooltip)
            if button is None:
                sweep.note(f"tooltip '{tooltip}'", "button not found")
                continue
            assert_positive_size(button, f"options-bar button '{tooltip}'")
            if callback and callback is not False:
                if not hasattr(window, callback):
                    sweep.note(
                        f"tooltip '{tooltip}'", f"callback {callback} missing on window"
                    )
        sweep.finish()

    def test_safe_button_clicks(self, qapp, qa_window, sample_tree):
        """Safe editor/clipboard buttons click without raising.

        NOTE: the save buttons may open a native save dialog, so the whole
        sweep runs with dialogs stubbed to the temp workspace.
        """
        window = qa_window
        _open_sample(qapp, window, sample_tree)
        safe_tooltips = {
            "Create a new file",
            "Cut selected text",
            "Copy selected text",
            "Paste text",
            "Undo action",
            "Redo action",
            "Save current file",
            "Save all files",
            "Ether AI",
            "Make File Read-Only",
        }
        sweep = Sweep("options bar safe clicks")
        with harness.modal_guard(paths=[str(Path(sample_tree) / "main.py")]):
            for tooltip, callback in _options_bar_buttons(window):
                if callback is False or tooltip not in safe_tooltips:
                    continue
                button = find_button(window.options_menu, tooltip)
                if button is not None:
                    sweep.step(f"click '{tooltip}'", click, qapp, button)
                    assert_alive(qapp, window)
        sweep.finish()

    def test_dialog_buttons_exist(self, qapp, qa_window):
        """Dialog-producing buttons exist; invocation is covered under stubs."""
        window = qa_window
        for tooltip in ("Open an existing file",):
            button = find_button(window.options_menu, tooltip)
            assert button is not None, f"options-bar button '{tooltip}' missing"

    def test_open_file_button_returns_cancelled(self, qapp, qa_window):
        """Open File with a stubbed cancel dialog leaves the window alive."""
        button = find_button(qa_window.options_menu, "Open an existing file")
        with harness.modal_guard(cancel=True):
            click(qapp, button)
        assert_alive(qapp, qa_window)

    def test_new_solution_buttons_inert(self, qapp, qa_window):
        """Buttons with disabled callbacks click without any effect or crash."""
        window = qa_window
        sweep = Sweep("inert options-bar buttons")
        for tooltip, callback in _options_bar_buttons(window):
            if callback is not False:
                continue
            button = find_button(window.options_menu, tooltip)
            if button is None:
                sweep.note(f"tooltip '{tooltip}'", "button not found")
                continue
            sweep.step(f"click inert '{tooltip}'", click, qapp, button)
        sweep.finish()
        assert window.isVisible()

    def test_theme_actions_apply_without_error(self, qapp, qa_window):
        """Every theme setter runs; the window survives the restyle."""
        window = qa_window
        sweep = Sweep("theme actions")
        sweep.step("theme by name", window._set_theme_by_name, "dark")
        for name in sorted(dir(window)):
            if not name.startswith("_set_theme_") or name == "_set_theme_by_name":
                continue
            sweep.step(f"theme {name}", getattr(window, name))
            assert_alive(qapp, window)
            assert window.isVisible(), f"window hidden after {name}"
        sweep.finish()

    def test_run_menu_actions_exist(self, qapp, qa_window):
        """Run/debug/config actions exist but are not invoked here."""
        window = qa_window
        for callback in (
            "_run_current_file",
            "_run_and_debug_file",
            "_config_run_options",
        ):
            assert hasattr(window, callback), f"run action {callback} missing"

    def test_find_in_file_button_opens_find_replace(self, qapp, qa_window):
        """The 'Find in File' button must reveal the find/replace widget.

        NOTE (QA finding): the JSON wires this button to ``_toggle_nodes_editor``.
        If the find/replace widget does not appear, the tooltip contract is
        broken and this test records the defect.
        """
        window = qa_window
        button = find_button(window.options_menu, "Find in File")
        click(qapp, button)
        window._find_replace_window = getattr(window, "_find_replace_window", None)
        assert window._find_replace_window is not None, "find/replace never created"
        assert (
            window._find_replace_window.isVisible()
        ), "Find in File button did not show the find/replace widget"


class TestSidebarToggles:
    """Every sidebar button must toggle its declared target contract."""

    _PANEL_TARGETS = {
        "Solution Explorer": "solution_explorer",
        "Version Control": "source_control",
        "Outline": "file_outline",
        "Toggle Properties": "properties",
        "TODOs Search": "todo_search",
    }

    def test_panel_toggles_flip_visibility(self, qapp, qa_window):
        """Panel sidebar buttons flip the matching VerticalMenusAPI panel."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        sweep = Sweep("sidebar panel toggles")
        for tooltip, callback in _sidebar_entries():
            panel_id = self._PANEL_TARGETS.get(tooltip)
            if panel_id is None:
                continue
            button = find_button(window, tooltip)
            if button is None:
                sweep.note(f"tooltip '{tooltip}'", "button not found")
                continue
            result = sweep.step(
                f"toggle '{tooltip}'",
                toggle_contract,
                qapp,
                getattr(window, callback),
                lambda pid=panel_id: api.is_visible(pid),
                2,
            )
            if result is not None:
                sweep.step(f"restore '{tooltip}' hidden", getattr(window, callback))
        sweep.finish()

    def test_terminal_toggle_flips_dock(self, qapp, qa_window):
        """The terminal button flips the lower dock visibility."""
        window = qa_window
        container = window.hero_window._lower_widget

        def dock_visible() -> bool:
            """Return True when the lower dock is visible.

            Returns:
                Dock visibility flag.
            """
            return container.isVisible()

        toggle_contract(qapp, window._toggle_terminal, dock_visible, 2)

    def test_python_console_toggle_adds_tab(self, qapp, qa_window):
        """The Python shell button adds exactly one 'Python Shell' tab.

        NOTE (QA finding): a second toggle is expected to focus the existing
        shell; adding a second shell tab records the defect. The shell widget
        itself is stubbed because it starts a Jupyter kernel, which blocks in
        offscreen mode.
        """
        import unittest.mock

        from PyQt6.QtWidgets import QWidget

        class _ShellStub(QWidget):
            """Stand-in for the Jupyter-backed Python shell widget."""

        window = qa_window
        tabs = window.hero_window._text_editor_center.tabs
        before = tabs.count()
        with unittest.mock.patch("editor.api.editor_api.PythonShell", _ShellStub):
            click(qapp, find_button(window, "Python Interpreter Shell"))
        assert tabs.count() == before + 1, "Python Shell tab not added"
        titles = [tabs.tabText(i) for i in range(tabs.count())]
        assert (
            titles.count("Python Shell") == 1
        ), f"duplicate Python Shell tabs: {titles}"

    def test_settings_toggle_adds_tab(self, qapp, qa_window):
        """The Settings button adds a 'Settings' tab without raising."""
        window = qa_window
        tabs = window.hero_window._text_editor_center.tabs
        before = tabs.count()
        click(qapp, find_button(window, "Settings"))
        assert tabs.count() == before + 1, "Settings tab not added"
        titles = [tabs.tabText(i) for i in range(tabs.count())]
        assert "Settings" in titles, f"Settings tab missing: {titles}"


class TestStatusBarToggles:
    """Status-bar buttons must flip their panels via real clicks."""

    def test_notification_button_toggles_panel(self, qapp, qa_window):
        """The notification button flips the notifications panel."""
        window = qa_window
        api = window.hero_window._vertical_menus_api
        button = window.status_bar.notificationBtn
        toggle_contract(
            qapp,
            lambda: click(qapp, button),
            lambda: api.is_visible("notifications"),
            2,
        )

    def test_errors_button_toggles_problems(self, qapp, qa_window):
        """The errors button flips the lower Problems dock."""
        window = qa_window
        button = window.status_bar.errorsBtn
        container = window.hero_window._lower_widget
        toggle_contract(
            qapp, lambda: click(qapp, button), lambda: container.isVisible(), 2
        )

    def test_checks_button_shows_problems(self, qapp, qa_window):
        """The checks button reveals the Problems dock with the checks group."""
        window = qa_window
        button = window.status_bar.checksBtn
        container = window.hero_window._lower_widget
        problems = container.problems_window
        click(qapp, button)
        assert container.isVisible(), "checks button did not open the Problems dock"
        assert (
            problems.filter_group() == "checks"
        ), f"unexpected filter group: {problems.filter_group()}"

    def test_poke_status_bar_clean(self, qapp, qa_window):
        """A full status-bar click sweep records no failure."""
        sweep = Sweep("status bar poke")
        poke(qapp, qa_window.status_bar, sweep)
        sweep.finish()
        assert_alive(qapp, qa_window)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
