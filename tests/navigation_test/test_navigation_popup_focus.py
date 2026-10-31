"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Regression tests for the C++ multi-target navigation popup and editor focus.
"""

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QMainWindow
from PyQt6.Qsci import QsciScintilla

from editor.Ironica.plugins.cpp.navigation.engine import NavigationResult
from editor.Ironica.plugins.cpp.navigation.popup import (
    NavigationPopup,
    NavigationResultDelegate,
)


def _results(count: int = 4) -> list[NavigationResult]:
    """Return deterministic navigation results for popup tests."""
    return [
        NavigationResult(
            file_path=f"/tmp/ref_{index}.cpp",
            line=index,
            col=0,
            display_name="",
            kind="reference",
        )
        for index in range(count)
    ]


def _make_editor(qapp) -> tuple[QMainWindow, QsciScintilla]:
    """Create a shown editor that owns keyboard focus."""
    window = QMainWindow()
    editor = QsciScintilla(window)
    window.setCentralWidget(editor)
    window.resize(800, 600)
    window.show()
    window.activateWindow()
    editor.setFocus()
    qapp.processEvents()
    return window, editor


def _show_popup(editor, qapp, on_select=None) -> NavigationPopup:
    """Create and show a popup anchored to *editor*."""
    popup = NavigationPopup(editor.window())
    popup.set_results(_results(), on_select=on_select)
    popup.show_at_cursor(editor)
    qapp.processEvents()
    return popup


class TestNavigationPopupFocus:
    """The navigation popup must never steal focus from the editor."""

    def test_show_at_cursor_keeps_editor_focused(self, qapp):
        """Showing the popup leaves keyboard focus in the editor."""
        window, editor = _make_editor(qapp)
        popup = _show_popup(editor, qapp)
        try:
            assert editor.hasFocus()
            assert not popup.isActiveWindow()
            assert qapp.focusWidget() is editor
        finally:
            popup.hide()
            window.close()

    def test_arrow_keys_move_selection_while_editor_keeps_focus(self, qapp):
        """Down/Up move the popup selection without focusing the list view."""
        window, editor = _make_editor(qapp)
        popup = _show_popup(editor, qapp)
        try:
            QTest.keyClick(editor, Qt.Key.Key_Down)
            qapp.processEvents()
            assert popup.list_view.currentIndex().row() == 1
            assert editor.hasFocus()

            QTest.keyClick(editor, Qt.Key.Key_Up)
            qapp.processEvents()
            assert popup.list_view.currentIndex().row() == 0
            assert editor.hasFocus()
        finally:
            popup.hide()
            window.close()

    def test_return_commits_selection_and_restores_focus(self, qapp):
        """Enter chooses the highlighted result and leaves the editor focused."""
        window, editor = _make_editor(qapp)
        selected = []
        popup = _show_popup(editor, qapp, on_select=selected.append)
        try:
            QTest.keyClick(editor, Qt.Key.Key_Down)
            QTest.keyClick(editor, Qt.Key.Key_Return)
            qapp.processEvents()

            assert not popup.isVisible()
            assert len(selected) == 1
            assert selected[0].file_path == "/tmp/ref_1.cpp"
            assert editor.hasFocus()
        finally:
            popup.hide()
            window.close()

    def test_escape_dismisses_popup_and_restores_typing(self, qapp):
        """Escape closes the popup, emits cancelled, and typing still works."""
        window, editor = _make_editor(qapp)
        cancelled = []
        popup = _show_popup(editor, qapp)
        popup.cancelled.connect(lambda: cancelled.append(True))
        try:
            QTest.keyClick(editor, Qt.Key.Key_Escape)
            qapp.processEvents()

            assert not popup.isVisible()
            assert cancelled == [True]
            assert editor.hasFocus()

            QTest.keyClicks(editor, "ok")
            qapp.processEvents()
            assert editor.text() == "ok"
        finally:
            popup.hide()
            window.close()

    def test_outside_click_dismisses_popup(self, qapp):
        """A click outside the popup dismisses it and keeps editor focus."""
        window, editor = _make_editor(qapp)
        popup = _show_popup(editor, qapp)
        try:
            QTest.mouseClick(
                editor.viewport(),
                Qt.MouseButton.LeftButton,
                pos=QPoint(500, 400),
            )
            qapp.processEvents()

            assert not popup.isVisible()
            assert editor.hasFocus()
        finally:
            popup.hide()
            window.close()


class TestNavigationPopupPresentation:
    """The popup must show the correct label, size, and lifetime."""

    def test_reference_results_are_labelled_reference(self, qapp):
        """Reference results use the Reference label, not the generic Target."""
        popup = NavigationPopup(None)
        try:
            popup.set_results(_results())
            assert popup.model.item(0).text().startswith("Reference  ")
        finally:
            popup.deleteLater()

    def test_popup_hides_completion_hint_bar_and_sizes_to_rows(self, qapp):
        """Navigation results hide the completion hint bar and get a row height."""
        popup = NavigationPopup(None)
        try:
            popup.set_results(_results(3))
            assert popup.hint_bar.isHidden()
            assert popup.height() >= 3 * NavigationResultDelegate.ROW_HEIGHT
        finally:
            popup.deleteLater()

    def test_code_editor_reuses_one_navigation_popup(self, qapp):
        """CodeEditor keeps a single popup instance across invocations."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        try:
            targets = [("/tmp/a.cpp", 1, 0), ("/tmp/a.cpp", 2, 0)]
            editor._show_navigation_popup(targets, kind="reference")
            popup = editor._navigation_popup
            assert popup is not None
            assert popup.model.item(0).text().startswith("Reference  ")

            editor._show_navigation_popup(targets, kind="reference")
            assert editor._navigation_popup is popup
        finally:
            popup = getattr(editor, "_navigation_popup", None)
            if popup is not None:
                popup.hide()
                popup.deleteLater()
            editor.deleteLater()


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
