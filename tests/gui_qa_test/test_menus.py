"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Menu live tests: every action declared in menus.json must resolve to a real
callable on the window, safe edit actions must run against an open file, and
dialog actions must run only with native dialogs stubbed.
"""

import json

import pytest

from harness import Sweep, assert_alive, code_editor, pump

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

PLACEHOLDER_ACTIONS = {"generic_callback"}
QUIT_ACTIONS = {"set_exit", "set_close_dreamstudio"}

SAFE_ACTIONS = (
    "set_undo",
    "set_redo",
    "set_copy",
    "set_copy_as_plain_text",
    "set_cut",
    "set_paste",
    "set_select_all",
    "set_unselect_all",
    "set_indent_selection",
    "set_unindent_selection",
    "set_format_code",
    "set_comment_current_line",
    "set_uncomment_current_line",
    "set_duplicate_current_line",
    "set_duplicate_current_selection",
    "set_expand_current_fold",
    "set_expand_all_folds",
    "set_collapse_current_fold",
    "set_collapse_all_folds",
    "set_collapse_includes",
)

DIALOG_ACTIONS = ("set_open_file", "set_save_file_as", "set_save_current_file")


def _menu_actions() -> list[tuple[str, str]]:
    """Collect (menu-title, action-name) pairs from menus.json.

    Returns:
        Flat list of every action declaration in the menu tree.
    """
    from editor.utils.resource_path import resource_path

    with open(resource_path("editor/base/json/menus.json"), encoding="utf-8") as fh:
        data = json.load(fh)

    collected: list[tuple[str, str]] = []

    def walk(menu_name: str, items: list) -> None:
        """Recursively collect actions from *items*.

        Args:
            menu_name: Name of the owning top-level menu.
            items: List of menu entries.
        """
        for entry in items:
            if not entry:
                continue
            if entry.get("submenu"):
                walk(menu_name, entry["submenu"])
                continue
            action = entry.get("action")
            if action:
                collected.append((menu_name, action))

    for menu_name, items in data.items():
        walk(menu_name, items)
    return collected


def _open_sample(qapp, window, workspace_path) -> None:
    """Open the sample file so edit actions have a target.

    Args:
        qapp: The live QApplication instance.
        window: The DreamStudio main window.
        workspace_path: Workspace root containing ``main.py``.
    """
    from pathlib import Path

    tabs = window.hero_window._text_editor_center.tabs
    tabs.open_file_by_path(str(Path(workspace_path) / "main.py"))
    pump(qapp, 150)


class TestMenuActionContract:
    """Every declared menu action must resolve to a window callable."""

    def test_every_menu_action_exists_on_window(self, qapp, qa_window):
        """Each menus.json action must exist on the window.

        NOTE (QA finding): placeholder and unknown action names leave their
        QAction disconnected, so the menu item silently does nothing.
        """
        window = qa_window
        missing: list[str] = []
        for menu_name, action in _menu_actions():
            if action in PLACEHOLDER_ACTIONS:
                missing.append(f"{menu_name}: '{action}' is a placeholder")
                continue
            if not hasattr(window, action):
                missing.append(f"{menu_name}: '{action}' missing on window")
        assert (
            not missing
        ), f"{len(missing)} menu action(s) have no implementation:\n  " + "\n  ".join(
            missing
        )

    def test_menu_qactions_are_connected(self, qapp, qa_window):
        """Every QAction built from menus.json must have a connected slot."""
        from PyQt6.QtWidgets import QMenu

        window = qa_window
        unconnected: list[str] = []
        for menu in window.title_bar.findChildren(QMenu):
            for action in menu.actions():
                if action.isSeparator():
                    continue
                if not action.receivers(action.triggered):
                    unconnected.append(f"{menu.title()}: '{action.text()}'")
        assert (
            not unconnected
        ), f"{len(unconnected)} menu action(s) are disconnected:\n  " + "\n  ".join(
            unconnected
        )

    def test_quit_actions_exist_but_are_not_invoked(self, qapp, qa_window):
        """Quit actions exist; the suite never triggers them."""
        window = qa_window
        for action in QUIT_ACTIONS:
            assert hasattr(window, action), f"quit action {action} missing"
        assert window.isVisible()


class TestSafeMenuActions:
    """Safe edit/code actions must run against an open sample file."""

    def test_safe_actions_run_without_error(self, qapp, qa_window, sample_tree):
        """Undo/copy/comment/duplicate/fold actions run without raising."""
        window = qa_window
        _open_sample(qapp, window, sample_tree)
        sweep = Sweep("safe menu actions")
        for action in SAFE_ACTIONS:
            target = getattr(window, action, None)
            if target is None:
                sweep.note(action, "action missing on window")
                continue
            sweep.step(f"run {action}", target)
            assert_alive(qapp, window)
        sweep.finish()

    def test_comment_action_changes_text(self, qapp, qa_window, sample_tree):
        """Commenting the current line must alter the document text."""
        window = qa_window
        _open_sample(qapp, window, sample_tree)
        editor = code_editor(window.hero_window._text_editor_center.current_editor())
        editor.setCursorPosition(0, 0)
        before = editor.text()
        window.set_comment_current_line()
        pump(qapp, 100)
        after = editor.text()
        assert after != before, "comment action did not change the text"

    def test_duplicate_action_changes_text(self, qapp, qa_window, sample_tree):
        """Duplicating the current line must alter the document text."""
        window = qa_window
        _open_sample(qapp, window, sample_tree)
        editor = code_editor(window.hero_window._text_editor_center.current_editor())
        editor.setCursorPosition(0, 0)
        before = editor.text()
        window.set_duplicate_current_line()
        pump(qapp, 100)
        assert editor.text() != before, "duplicate action did not change the text"


class TestMenuGating:
    """Menu actions are enabled only while their precondition holds."""

    @staticmethod
    def _action(window, name):
        """Return the tracked QAction for *name* after refreshing its state.

        Args:
            window: The live DreamStudio main window.
            name: Action name as declared in ``menus.json``.

        Returns:
            The QAction that the title bar tracks for gating.
        """
        window.title_bar.refresh_action_states()
        action = window.title_bar._menu_actions.get(name)
        assert action is not None, f"menu action '{name}' is not gated"
        return action

    @staticmethod
    def _leaf_actions(window):
        """Yield ``(text, action)`` for every leaf action of the menu bar.

        Args:
            window: The live DreamStudio main window.
        """
        from PyQt6.QtWidgets import QMenu

        for menu in window.title_bar.menubar.findChildren(QMenu):
            for action in menu.actions():
                if action.isSeparator() or action.menu() is not None:
                    continue
                yield action.text(), action

    def test_editor_actions_are_disabled_without_an_open_editor(self, qapp, qa_window):
        """Editor-only actions stay greyed out until a code tab is active."""
        window = qa_window
        for name in (
            "set_cut",
            "set_copy",
            "set_paste",
            "set_undo",
            "set_redo",
            "set_select_all",
            "set_format_code",
            "set_comment_current_line",
            "set_toggle_breakpoint",
            "set_run_current_file",
            "set_expand_all_folds",
        ):
            assert not self._action(
                window, name
            ).isEnabled(), f"'{name}' is enabled without an open editor"

    def test_selection_actions_follow_the_selection(self, qapp, qa_window, sample_tree):
        """Cut/copy are enabled only while text is selected."""
        window = qa_window
        _open_sample(qapp, window, sample_tree)
        editor = code_editor(window.hero_window._text_editor_center.current_editor())

        editor.setCursorPosition(0, 0)
        pump(qapp, 100)
        for name in (
            "set_cut",
            "set_copy",
            "set_delete_selection",
            "set_search_in_selected",
        ):
            assert not self._action(
                window, name
            ).isEnabled(), f"'{name}' is enabled without a selection"

        assert self._action(window, "set_select_all").isEnabled()
        assert self._action(window, "set_comment_current_line").isEnabled()

        editor.setSelection(0, 0, 0, 5)
        pump(qapp, 100)
        for name in ("set_cut", "set_copy", "set_delete_selection"):
            assert self._action(
                window, name
            ).isEnabled(), f"'{name}' stays disabled with a selection"

        editor.setCursorPosition(0, 0)
        pump(qapp, 100)
        assert not self._action(window, "set_cut").isEnabled()

    def test_run_actions_require_a_python_file(self, qapp, qa_window, sample_tree):
        """Run/debug actions unlock only for an on-disk Python file."""
        window = qa_window
        assert not self._action(window, "set_run_current_file").isEnabled()

        _open_sample(qapp, window, sample_tree)
        for name in (
            "set_run_current_file",
            "set_run_without_debugging",
            "set_run_with_arguments",
            "_debug_current_file",
        ):
            assert self._action(
                window, name
            ).isEnabled(), f"'{name}' stays disabled for a Python file"

    def test_breakpoint_actions_follow_breakpoints(self, qapp, qa_window, sample_tree):
        """Enable/disable/remove-all unlock only when breakpoints exist."""
        window = qa_window
        _open_sample(qapp, window, sample_tree)

        for name in (
            "set_enable_all_breakpoints",
            "set_disable_all_breakpoints",
            "set_remove_all_breakpoints",
        ):
            assert not self._action(
                window, name
            ).isEnabled(), f"'{name}' is enabled without breakpoints"

        window.set_toggle_breakpoint()
        pump(qapp, 100)
        for name in (
            "set_enable_all_breakpoints",
            "set_disable_all_breakpoints",
            "set_remove_all_breakpoints",
        ):
            assert self._action(
                window, name
            ).isEnabled(), f"'{name}' stays disabled with a breakpoint"

        window.set_remove_all_breakpoints()
        pump(qapp, 100)
        assert not self._action(window, "set_enable_all_breakpoints").isEnabled()

    def test_unavailable_actions_are_disabled(self, qapp, qa_window):
        """Every action marked unavailable is greyed out with an explanation."""
        from editor.utils.resource_path import resource_path

        window = qa_window
        unavailable = window.title_bar._UNAVAILABLE_ACTIONS
        tooltip = window.title_bar._UNAVAILABLE_TOOLTIP

        with open(resource_path("editor/base/json/menus.json"), encoding="utf-8") as fh:
            data = json.load(fh)

        texts: set[str] = set()

        def walk(items: list) -> None:
            """Collect the labels of unavailable actions.

            Args:
                items: Menu entries to inspect.
            """
            for entry in items:
                if not entry:
                    continue
                if entry.get("submenu"):
                    walk(entry["submenu"])
                    continue
                if entry.get("action") in unavailable:
                    texts.add(entry.get("text"))

        for items in data.values():
            walk(items)

        by_text: dict[str, list] = {}
        for text, action in self._leaf_actions(window):
            by_text.setdefault(text, []).append(action)

        assert texts, "menus.json declares no unavailable actions"
        for text in texts:
            actions = by_text.get(text) or []
            assert actions, f"unavailable action '{text}' is missing from the menu bar"
            for action in actions:
                assert not action.isEnabled(), f"unavailable action '{text}' is enabled"
                assert action.toolTip() == tooltip


class TestDialogMenuActions:
    """Dialog-producing actions run only with native dialogs stubbed."""

    def test_open_file_action_under_stub(self, qapp, qa_window, sample_tree):
        """Open File with a stubbed path opens the sample without blocking."""
        import harness
        from pathlib import Path

        window = qa_window
        target = str(Path(sample_tree) / "main.py")
        with harness.modal_guard(paths=[target]):
            window.set_open_file()
            pump(qapp, 200)
        assert_alive(qapp, window)

    def test_save_file_as_action_under_stub(self, qapp, qa_window, sample_tree):
        """Save As with a stubbed path completes without blocking."""
        import harness
        from pathlib import Path

        window = qa_window
        _open_sample(qapp, window, sample_tree)
        target = str(Path(sample_tree) / "saved_copy.py")
        with harness.modal_guard(paths=[target]):
            window.set_save_file_as()
            pump(qapp, 200)
        assert_alive(qapp, window)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
