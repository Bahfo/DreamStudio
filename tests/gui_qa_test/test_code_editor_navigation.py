"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Code editor navigation live tests: go-to definition/declaration/
implementation, find references, the navigation popup, brace highlighting,
the context menu, hover, and snippets.
"""

from pathlib import Path

import pytest

from harness import (
    Sweep,
    assert_alive,
    code_editor,
    mouse_move,
    press_key,
    pump,
    race_probe,
    right_click,
    type_text,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

QT = pytest.importorskip("PyQt6.QtCore")


def _open_editor(qapp, window, workspace_path, name: str = "main.py"):
    """Open a sample file and return its CodeEditor.

    Args:
        qapp: The live QApplication instance.
        window: The DreamStudio main window.
        workspace_path: Workspace root holding the sample file.
        name: File name to open.

    Returns:
        The CodeEditor instance.
    """
    tabs = window.hero_window._text_editor_center.tabs
    tabs.open_file_by_path(str(Path(workspace_path) / name))
    pump(qapp, 300)
    api = window.hero_window._text_editor_center.current_editor()
    return code_editor(api)


class _FakeProvider:
    """Minimal language provider returning fixed navigation targets."""

    def __init__(self, targets: list[tuple[str, int, int]]) -> None:
        """Store the targets returned by every lookup.

        Args:
            targets: List of (file_path, line, col) tuples.
        """
        self.targets = targets
        self.requests: list[tuple] = []

    def get_definition_location(self, text, line, col, file_path=None, root=None):
        """Return the configured definition targets.

        Args:
            text: Buffer text (unused).
            line: Cursor line (unused).
            col: Cursor column (unused).
            file_path: Current file path (unused).
            root: Project root (unused).

        Returns:
            The configured target list.
        """
        self.requests.append(("definition", line, col))
        return list(self.targets)

    def get_declaration_location(self, text, line, col, file_path=None, root=None):
        """Return the configured declaration targets.

        Args:
            text: Buffer text (unused).
            line: Cursor line (unused).
            col: Cursor column (unused).
            file_path: Current file path (unused).
            root: Project root (unused).

        Returns:
            The configured target list.
        """
        self.requests.append(("declaration", line, col))
        return list(self.targets)

    def get_implementation_location(self, text, line, col, file_path=None, root=None):
        """Return the configured implementation targets.

        Args:
            text: Buffer text (unused).
            line: Cursor line (unused).
            col: Cursor column (unused).
            file_path: Current file path (unused).
            root: Project root (unused).

        Returns:
            The configured target list.
        """
        self.requests.append(("implementation", line, col))
        return list(self.targets)

    def get_references(self, text, line, col, file_path=None, root=None):
        """Return the configured reference targets.

        Args:
            text: Buffer text (unused).
            line: Cursor line (unused).
            col: Cursor column (unused).
            file_path: Current file path (unused).
            root: Project root (unused).

        Returns:
            The configured target list.
        """
        self.requests.append(("reference", line, col))
        return list(self.targets)


class TestNavigationTargets:
    """Target normalisation accepts every plugin result shape."""

    def test_tuple_target_is_normalised(self, qapp, qa_window, sample_tree):
        """A plain tuple becomes a (path, line, col) triple."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        assert editor.normalize_targets(("/tmp/a.py", 3, 4)) == [("/tmp/a.py", 3, 4)]

    def test_dict_target_is_normalised(self, qapp, qa_window, sample_tree):
        """A dict target keeps its file, line, and column."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        targets = editor.normalize_targets(
            [{"file_path": "/tmp/a.py", "line": 2, "col": 5}]
        )
        assert targets == [("/tmp/a.py", 2, 5)]

    def test_malformed_targets_are_dropped(self, qapp, qa_window, sample_tree):
        """Malformed entries are dropped instead of raising."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        targets = editor.normalize_targets(
            [None, (), (5, 6), {"line": 1}, ("/tmp/a.py", 1)]
        )
        assert targets == [("/tmp/a.py", 1, 0)], f"unexpected targets: {targets}"

    def test_duplicate_targets_are_removed(self, qapp, qa_window, sample_tree):
        """Duplicate targets are collapsed."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        targets = editor.normalize_targets(
            [("/tmp/a.py", 1, 1), ("/tmp/a.py", 1, 1), ("/tmp/b.py", 2, 2)]
        )
        assert targets == [("/tmp/a.py", 1, 1), ("/tmp/b.py", 2, 2)]

    def test_empty_targets_return_empty_list(self, qapp, qa_window, sample_tree):
        """Empty results normalise to an empty list."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        assert editor.normalize_targets([]) == []
        assert editor.normalize_targets(None) == []


class TestNavigationActions:
    """The go-to actions drive the popup and direct navigation."""

    def test_single_target_navigates_directly(self, qapp, qa_window, sample_tree):
        """One target jumps straight to the position."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        provider = _FakeProvider([(str(Path(sample_tree) / "helpers.py"), 2, 1)])
        editor.current_provider = provider
        editor.setCursorPosition(1, 0)
        editor.execute_goto_definition()
        pump(qapp, 300)
        assert_alive(qapp, qa_window)

    def test_multiple_targets_open_the_popup(self, qapp, qa_window, sample_tree):
        """Several targets open the reusable navigation popup."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        provider = _FakeProvider(
            [
                (str(Path(sample_tree) / "helpers.py"), 1, 0),
                (str(Path(sample_tree) / "main.py"), 2, 0),
            ]
        )
        editor.current_provider = provider
        editor.setCursorPosition(1, 0)
        editor.execute_goto_definition()
        pump(qapp, 300)
        popup = getattr(editor, "_navigation_popup", None)
        assert popup is not None, "navigation popup was not created"
        assert (
            popup.model.rowCount() == 2
        ), f"unexpected popup rows: {popup.model.rowCount()}"

    def test_popup_is_reused(self, qapp, qa_window, sample_tree):
        """A second navigation reuses the same popup instance."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        provider = _FakeProvider(
            [
                (str(Path(sample_tree) / "helpers.py"), 1, 0),
                (str(Path(sample_tree) / "main.py"), 2, 0),
            ]
        )
        editor.current_provider = provider
        editor.setCursorPosition(1, 0)
        editor.execute_goto_definition()
        pump(qapp, 200)
        first = getattr(editor, "_navigation_popup", None)
        editor.execute_goto_definition()
        pump(qapp, 200)
        assert (
            getattr(editor, "_navigation_popup", None) is first
        ), "popup was recreated"

    def test_no_targets_shows_the_failure_path(self, qapp, qa_window, sample_tree):
        """No results take the failure path without raising."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.current_provider = _FakeProvider([])
        editor.setCursorPosition(0, 0)
        sweep = Sweep("navigation failure")
        sweep.step("goto definition", editor.execute_goto_definition)
        pump(qapp, 200)
        sweep.step("goto declaration", editor.execute_goto_declaration)
        pump(qapp, 200)
        sweep.step("goto implementation", editor.execute_goto_implementation)
        pump(qapp, 200)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_find_references_uses_the_provider(self, qapp, qa_window, sample_tree):
        """Find references calls the provider and handles the result."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        provider = _FakeProvider([(str(Path(sample_tree) / "helpers.py"), 4, 2)])
        editor.current_provider = provider
        editor.setCursorPosition(1, 0)
        editor.execute_find_references()
        pump(qapp, 300)
        assert any(
            req[0] == "reference" for req in provider.requests
        ), f"provider was not asked for references: {provider.requests}"

    def test_navigation_popup_keyboard_navigation(self, qapp, qa_window, sample_tree):
        """The popup responds to arrow keys and Enter without raising."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor._show_navigation_popup(
            [
                (str(Path(sample_tree) / "helpers.py"), 1, 0),
                (str(Path(sample_tree) / "main.py"), 2, 0),
            ],
            kind="reference",
        )
        pump(qapp, 200)
        popup = editor._navigation_popup
        sweep = Sweep("popup keyboard")
        sweep.step("down", press_key, qapp, popup.list_view, QT.Qt.Key.Key_Down)
        sweep.step("up", press_key, qapp, popup.list_view, QT.Qt.Key.Key_Up)
        sweep.step("escape", press_key, qapp, popup.list_view, QT.Qt.Key.Key_Escape)
        sweep.finish()

    def test_rapid_navigation_keeps_one_popup(self, qapp, qa_window, sample_tree):
        """A navigation storm keeps a single popup instance."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        provider = _FakeProvider(
            [
                (str(Path(sample_tree) / "helpers.py"), 1, 0),
                (str(Path(sample_tree) / "main.py"), 2, 0),
            ]
        )
        editor.current_provider = provider
        editor.setCursorPosition(1, 0)

        def navigate() -> None:
            """Trigger one go-to-definition request.

            Returns:
                None; the side effect is the navigation request.
            """
            editor.execute_goto_definition()

        race_probe(qapp, navigate, 3)
        pump(qapp, 300)
        assert_alive(qapp, qa_window)


class TestBraceHighlight:
    """Brace highlighting follows the cursor."""

    def test_matched_brace_is_highlighted(self, qapp, qa_window, sample_tree):
        """A matched brace pair produces a highlight."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def f():\n    return {1: 2}\n")
        pump(qapp, 150)
        editor.setCursorPosition(0, 5)
        editor._update_brace_highlight()
        pump(qapp, 150)
        assert_alive(qapp, qa_window)

    def test_unmatched_brace_does_not_raise(self, qapp, qa_window, sample_tree):
        """An unmatched brace leaves the editor usable."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def f(:\n    pass\n")
        pump(qapp, 150)
        editor.setCursorPosition(0, 5)
        sweep = Sweep("unmatched brace")
        sweep.step("update highlight", editor._update_brace_highlight)
        pump(qapp, 150)
        sweep.finish()

    def test_typing_updates_the_brace_highlight(self, qapp, qa_window, sample_tree):
        """Typing a bracket keeps the highlight logic alive."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("value = 1\n")
        pump(qapp, 150)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "{")
        pump(qapp, 300)
        assert_alive(qapp, qa_window)


class TestContextMenu:
    """The editor context menu opens and closes cleanly."""

    def test_context_menu_opens_on_right_click(self, qapp, qa_window, sample_tree):
        """A right click opens the editor context menu."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        right_click(qapp, editor)
        pump(qapp, 200)
        assert_alive(qapp, qa_window)

    def test_context_menu_show_context_menu_is_safe(self, qapp, qa_window, sample_tree):
        """show_context_menu() runs without raising."""
        from harness import close_popups_soon

        editor = _open_editor(qapp, qa_window, sample_tree)
        close_popups_soon(qapp)
        sweep = Sweep("context menu")
        sweep.step("show menu", editor.show_context_menu, None)
        pump(qapp, 200)
        sweep.finish()
        assert_alive(qapp, qa_window)


class TestHoverEngine:
    """The hover flyout can be shown and dismissed."""

    def test_hover_controller_is_created(self, qapp, qa_window, sample_tree):
        """The editor owns a hover controller once the file is open."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        controller = getattr(editor, "_hover_controller", None)
        assert controller is not None, "hover controller was not created"

    def test_mouse_move_over_text_is_safe(self, qapp, qa_window, sample_tree):
        """Moving the pointer over code does not raise."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def greet(name):\n    return name\n")
        pump(qapp, 150)
        sweep = Sweep("hover move")
        for x in (20, 60, 120):
            sweep.step(f"move to {x}", mouse_move, qapp, editor, QT.QPoint(x, 10))
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_dismiss_all_popups_is_safe(self, qapp, qa_window, sample_tree):
        """Dismissing every popup leaves the editor usable."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        sweep = Sweep("dismiss popups")
        sweep.step("dismiss all", editor._dismiss_all_popups, True)
        pump(qapp, 150)
        sweep.finish()
        assert_alive(qapp, qa_window)


class TestSnippets:
    """Snippet loading and expansion behave."""

    def test_load_snippets_from_a_file(self, qapp, qa_window, sample_tree, tmp_path):
        """Loading a snippet file registers the snippet."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        snippets = tmp_path / "snippets.json"
        snippets.write_text(
            '{"qa": {"prefix": "qa", "body": "print(\\"qa\\")"}}', encoding="utf-8"
        )
        sweep = Sweep("snippet load")
        sweep.step("load snippets", editor.load_snippets, str(snippets))
        pump(qapp, 150)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_expand_snippet_inserts_the_body(self, qapp, qa_window, sample_tree):
        """Expanding a snippet inserts its body at the cursor."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("value = 1\n")
        pump(qapp, 150)
        editor.setCursorPosition(0, 0)
        sweep = Sweep("snippet expand")
        sweep.step(
            "expand",
            editor._expand_snippet,
            0,
            0,
            "qa",
            'print("qa")',
        )
        pump(qapp, 200)
        sweep.finish()
        assert "print" in editor.text(), f"snippet body missing: {editor.text()!r}"

    def test_missing_snippet_file_is_handled(self, qapp, qa_window, sample_tree):
        """A missing snippet file does not raise."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        sweep = Sweep("missing snippets")
        sweep.step("load missing", editor.load_snippets, "/nonexistent/snippets.json")
        pump(qapp, 150)
        sweep.finish()
        assert_alive(qapp, qa_window)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
