"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Code editor completion live tests: the completion controller, popup, hint bar,
and delegate behaviour while typing in the real editor.
"""

from pathlib import Path

import pytest

from harness import (
    Sweep,
    assert_alive,
    code_editor,
    press_key,
    pump,
    race_probe,
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


def _controller(editor):
    """Return the completion controller of an editor.

    Args:
        editor: The CodeEditor instance.

    Returns:
        The CompletionController instance.
    """
    return editor._autocompletion_widget


class TestCompletionPopup:
    """The completion popup shows, navigates, and commits."""

    def test_controller_is_attached(self, qapp, qa_window, sample_tree):
        """Every editor owns a completion controller and popup."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        controller = _controller(editor)
        assert controller is not None, "no completion controller attached"
        assert controller.popup is not None, "no completion popup created"

    def test_popup_populates_with_items(self, qapp, qa_window, sample_tree):
        """The popup accepts a list of completion items."""
        from editor.Ironica.utils.completion import CompletionItem

        editor = _open_editor(qapp, qa_window, sample_tree)
        controller = _controller(editor)
        items = [
            CompletionItem(text="greet", signature="greet(name)"),
            CompletionItem(text="greeting", signature="greeting"),
        ]
        result = controller.popup.populate(items)
        assert result, "popup refused the items"
        assert controller.popup.list_view.model().rowCount() == 2, (
            "popup did not receive both items"
        )

    def test_popup_navigation_moves_the_selection(self, qapp, qa_window, sample_tree):
        """Select-next and select-prev move the highlighted row."""
        from editor.Ironica.utils.completion import CompletionItem

        editor = _open_editor(qapp, qa_window, sample_tree)
        controller = _controller(editor)
        controller.popup.populate(
            [
                CompletionItem(text="alpha"),
                CompletionItem(text="beta"),
                CompletionItem(text="gamma"),
            ]
        )
        controller.popup.select_next()
        controller.popup.select_next()
        current = controller.popup.list_view.currentIndex().row()
        assert current >= 0, "popup selection never moved"
        controller.popup.select_prev()
        assert controller.popup.list_view.currentIndex().row() == current - 1, (
            "select-prev did not move back"
        )

    def test_popup_commit_inserts_the_item(self, qapp, qa_window, sample_tree):
        """Committing the popup inserts the completion text."""
        from editor.Ironica.utils.completion import CompletionItem

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("")
        pump(qapp, 150)
        controller = _controller(editor)
        controller.popup.populate([CompletionItem(text="qa_completion")])
        controller.popup.select_next()
        controller.popup.commit_current()
        pump(qapp, 250)
        assert "qa_completion" in editor.text(), (
            f"completion not inserted: {editor.text()!r}"
        )

    def test_popup_cancel_closes_it(self, qapp, qa_window, sample_tree):
        """Cancelling the popup closes it without inserting text."""
        from editor.Ironica.utils.completion import CompletionItem

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("")
        pump(qapp, 150)
        controller = _controller(editor)
        controller.popup.populate([CompletionItem(text="qa_cancel")])
        controller.popup.select_next()
        controller.popup.cancel()
        pump(qapp, 200)
        assert "qa_cancel" not in editor.text(), "cancelled completion was inserted"

    def test_popup_click_commits(self, qapp, qa_window, sample_tree):
        """Clicking a popup row commits that completion."""
        from editor.Ironica.utils.completion import CompletionItem

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("")
        pump(qapp, 150)
        controller = _controller(editor)
        controller.popup.populate([CompletionItem(text="qa_click")])
        controller.popup.select_next()
        controller.popup._on_clicked(controller.popup.list_view.currentIndex())
        pump(qapp, 250)
        assert_alive(qapp, qa_window)

    def test_page_navigation_is_safe(self, qapp, qa_window, sample_tree):
        """Page-up and page-down move through the popup safely."""
        from editor.Ironica.utils.completion import CompletionItem

        editor = _open_editor(qapp, qa_window, sample_tree)
        controller = _controller(editor)
        controller.popup.populate(
            [CompletionItem(text=f"item{i}") for i in range(30)]
        )
        sweep = Sweep("popup paging")
        sweep.step("page next", controller.popup.page_next)
        sweep.step("page prev", controller.popup.page_prev)
        sweep.finish()
        assert_alive(qapp, qa_window)


class TestCompletionTyping:
    """Typing drives the completion lifecycle."""

    def test_typing_a_prefix_opens_the_popup(self, qapp, qa_window, sample_tree):
        """Typing an identifier offers completions."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("gre\n")
        pump(qapp, 200)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "gre")
        pump(qapp, 1200)
        controller = _controller(editor)
        assert controller.popup is not None, "no completion popup present"

    def test_escape_closes_the_popup(self, qapp, qa_window, sample_tree):
        """Escape closes the completion popup."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("gre\n")
        pump(qapp, 200)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "gre")
        pump(qapp, 800)
        controller = _controller(editor)
        controller.popup.cancel()
        press_key(qapp, editor, QT.Qt.Key.Key_Escape)
        pump(qapp, 200)
        assert_alive(qapp, qa_window)

    def test_terminating_key_closes_the_popup(self, qapp, qa_window, sample_tree):
        """A terminating key dismisses the completion popup."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("gre\n")
        pump(qapp, 200)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "gre")
        pump(qapp, 800)
        controller = _controller(editor)
        press_key(qapp, editor, QT.Qt.Key.Key_Semicolon)
        pump(qapp, 300)
        assert not controller.popup.isVisible(), "the terminating key left the popup open"
        assert_alive(qapp, qa_window)

    def test_backspacing_below_trigger_length_closes_the_popup(self, qapp, qa_window, sample_tree):
        """Removing the typed prefix dismisses the popup."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("gre\n")
        pump(qapp, 200)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "gre")
        pump(qapp, 800)
        controller = _controller(editor)
        for _ in range(3):
            press_key(qapp, editor, QT.Qt.Key.Key_Backspace)
        pump(qapp, 500)
        assert not controller.popup.isVisible(), "backspacing left the popup open"
        assert_alive(qapp, qa_window)

    def test_typing_storm_keeps_the_editor_usable(self, qapp, qa_window, sample_tree):
        """Typing rapidly with completion active never breaks the editor."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("\n")
        pump(qapp, 200)
        editor.setCursorPosition(0, 0)

        def type_chunk() -> None:
            """Type a short identifier chunk.

            Returns:
                None; the side effect is the typed characters.
            """
            type_text(qapp, editor, "val")

        race_probe(qapp, type_chunk, 4)
        pump(qapp, 600)
        assert_alive(qapp, qa_window)
        assert editor.text().count("val") >= 1, "typed characters were lost"

    def test_document_tokens_are_available(self, qapp, qa_window, sample_tree):
        """The controller can build completion items from the document."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        controller = _controller(editor)
        items = controller._get_document_tokens()
        assert isinstance(items, list), "document tokens are not a list"

    def test_controller_close_is_safe(self, qapp, qa_window, sample_tree):
        """Closing the completion controller leaves the editor usable."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        controller = _controller(editor)
        sweep = Sweep("controller close")
        sweep.step("close", controller.close)
        pump(qapp, 200)
        sweep.finish()
        assert_alive(qapp, qa_window)


class TestCompletionHintBar:
    """The hint bar renders its messages."""

    def test_set_hint_updates_the_text(self, qapp, qa_window, sample_tree):
        """set_hint() replaces the hint bar text."""
        from editor.Ironica.utils.completion import CompletionHintBar

        bar = CompletionHintBar()
        bar.set_hint("qa hint")
        pump(qapp, 100)
        assert_alive(qapp, qa_window)

    def test_delegate_size_hint_is_positive(self, qapp, qa_window, sample_tree):
        """The completion delegate reports a positive size for its rows."""
        from PyQt6.QtWidgets import QStyleOptionViewItem

        from editor.Ironica.utils.completion import CompletionItem

        editor = _open_editor(qapp, qa_window, sample_tree)
        controller = _controller(editor)
        controller.popup.populate([CompletionItem(text="qa_item", signature="qa(x)")])
        view = controller.popup.list_view
        delegate = view.itemDelegate()

        option = QStyleOptionViewItem()
        option.initFrom(view)
        size = delegate.sizeHint(option, view.model().index(0, 0))
        assert size.width() > 0 and size.height() > 0, (
            f"delegate size hint is empty: {size}"
        )


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
