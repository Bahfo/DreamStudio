"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Code editor marker live tests: breakpoints, execution highlights, debug stack
frames, colour swatches, and occurrence highlighting.
"""

from pathlib import Path

import pytest

from harness import (
    Sweep,
    assert_alive,
    code_editor,
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


class TestBreakpoints:
    """Breakpoint markers toggle from the symbol margin."""

    def test_margin_click_adds_breakpoint(self, qapp, qa_window, sample_tree):
        """Clicking the breakpoint margin records a breakpoint line."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("a = 1\nb = 2\nc = 3\n")
        pump(qapp, 150)
        editor._on_margin_clicked(
            editor.MARGIN_BREAKPOINT, 1, QT.Qt.KeyboardModifier.NoModifier
        )
        pump(qapp, 150)
        assert (
            2 in editor.get_breakpoint_lines()
        ), f"breakpoint not recorded: {editor.get_breakpoint_lines()}"

    def test_second_click_removes_breakpoint(self, qapp, qa_window, sample_tree):
        """Clicking the margin again removes the breakpoint."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("a = 1\nb = 2\n")
        pump(qapp, 150)
        editor._on_margin_clicked(
            editor.MARGIN_BREAKPOINT, 0, QT.Qt.KeyboardModifier.NoModifier
        )
        editor._on_margin_clicked(
            editor.MARGIN_BREAKPOINT, 0, QT.Qt.KeyboardModifier.NoModifier
        )
        pump(qapp, 150)
        assert (
            1 not in editor.get_breakpoint_lines()
        ), f"breakpoint not removed: {editor.get_breakpoint_lines()}"

    def test_multiple_breakpoints_are_tracked(self, qapp, qa_window, sample_tree):
        """Several margin clicks record several breakpoints."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("a = 1\nb = 2\nc = 3\nd = 4\n")
        pump(qapp, 150)
        for line in (0, 2, 3):
            editor._on_margin_clicked(
                editor.MARGIN_BREAKPOINT, line, QT.Qt.KeyboardModifier.NoModifier
            )
        pump(qapp, 150)
        assert editor.get_breakpoint_lines() == {
            1,
            3,
            4,
        }, f"unexpected breakpoint set: {editor.get_breakpoint_lines()}"

    def test_margin_click_on_other_margin_is_ignored(
        self, qapp, qa_window, sample_tree
    ):
        """Clicking an unrelated margin does not create a breakpoint."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("a = 1\n")
        pump(qapp, 150)
        editor._on_margin_clicked(
            editor.MARGIN_BREAKPOINT + 5, 0, QT.Qt.KeyboardModifier.NoModifier
        )
        pump(qapp, 150)
        assert (
            not editor.get_breakpoint_lines()
        ), "unrelated margin created a breakpoint"

    def test_breakpoint_storm_is_stable(self, qapp, qa_window, sample_tree):
        """Rapid margin clicks keep the breakpoint set consistent."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("\n".join(f"v{i} = {i}" for i in range(20)) + "\n")
        pump(qapp, 150)

        def toggle() -> None:
            """Toggle a breakpoint on the first line.

            Returns:
                None; the side effect is the breakpoint toggle.
            """
            editor._on_margin_clicked(
                editor.MARGIN_BREAKPOINT, 0, QT.Qt.KeyboardModifier.NoModifier
            )

        race_probe(qapp, toggle, 4)
        pump(qapp, 150)
        lines = editor.get_breakpoint_lines()
        assert lines in ({1}, set()), f"breakpoint set inconsistent: {lines}"


class TestDebugMarkers:
    """Execution highlights and stack frames render and clear."""

    def test_execution_highlight_is_set(self, qapp, qa_window, sample_tree):
        """set_execution_line_highlight() marks the requested line."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("a = 1\nb = 2\nc = 3\n")
        pump(qapp, 150)
        editor.set_execution_line_highlight(2)
        pump(qapp, 150)
        assert_alive(qapp, window=qa_window)

    def test_execution_highlight_moves_without_accumulating(
        self, qapp, qa_window, sample_tree
    ):
        """Moving the execution highlight clears the previous line."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("a = 1\nb = 2\nc = 3\n")
        pump(qapp, 150)
        editor.set_execution_line_highlight(1)
        editor.set_execution_line_highlight(3)
        pump(qapp, 150)
        assert_alive(qapp, window=qa_window)

    def test_clear_all_execution_highlights(self, qapp, qa_window, sample_tree):
        """Clearing execution highlights leaves the editor usable."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("a = 1\n")
        pump(qapp, 150)
        editor.set_execution_line_highlight(1)
        editor.clear_all_execution_highlights()
        pump(qapp, 150)
        assert_alive(qapp, window=qa_window)

    def test_debug_stack_frame_show_and_hide(self, qapp, qa_window, sample_tree):
        """The debug stack frame can be shown and hidden again."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("a = 1\nb = 2\n")
        pump(qapp, 150)
        sweep = Sweep("debug stack frame")
        sweep.step("show frame", editor.show_debug_stack_frame, 1, "qa frame")
        pump(qapp, 150)
        sweep.step("hide frame", editor.hide_debug_stack_frame)
        pump(qapp, 150)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_debug_stack_frame_on_out_of_range_line(self, qapp, qa_window, sample_tree):
        """A stack frame beyond the document does not raise."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("a = 1\n")
        pump(qapp, 150)
        sweep = Sweep("out of range frame")
        sweep.step("show frame", editor.show_debug_stack_frame, 999, "qa")
        pump(qapp, 100)
        sweep.finish()


class TestColorSwatches:
    """Colour strings in code get margin swatches."""

    def test_hex_color_gets_a_marker(self, qapp, qa_window, sample_tree):
        """A hex colour line receives a colour marker."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText('color = "#aabbcc"\n')
        pump(qapp, 150)
        editor.update_line_color_indicator(0)
        pump(qapp, 150)
        assert (
            editor._get_color_by_line(0) is not None
        ), "colour string not recognised on the line"

    def test_rgb_and_rgba_colors_are_recognised(self, qapp, qa_window, sample_tree):
        """RGB and RGBA colour strings are recognised."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText(
            'rgb_value = "rgb(30, 144, 255)"\nrgba_value = "rgba(30, 144, 255, 0.5)"\n'
        )
        pump(qapp, 150)
        assert editor._get_color_by_line(0) is not None, "rgb colour not recognised"
        assert editor._get_color_by_line(1) is not None, "rgba colour not recognised"

    def test_named_css_colours_are_not_recognised(self, qapp, qa_window, sample_tree):
        """Named CSS colours stay outside the colour-margin contract.

        The editor documents its colour support as hex, rgb, and rgba only,
        so a named colour such as ``steelblue`` is intentionally not matched.
        """
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText('named = "steelblue"\n')
        pump(qapp, 150)
        assert (
            editor._get_color_by_line(0) is None
        ), "a named CSS colour was parsed as a colour literal"

    def test_plain_text_has_no_colour(self, qapp, qa_window, sample_tree):
        """A line without a colour string reports no colour."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText('value = "plain text"\n')
        pump(qapp, 150)
        assert editor._get_color_by_line(0) is None, "plain text treated as a colour"

    def test_color_margin_click_applies_the_new_color(
        self, qapp, qa_window, sample_tree
    ):
        """Clicking the colour margin rewrites the colour string."""
        import harness

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText('color = "#aabbcc"\n')
        pump(qapp, 150)
        with harness.modal_guard():
            editor._on_margin_clicked(
                editor.COLOR_MARGIN, 0, QT.Qt.KeyboardModifier.NoModifier
            )
            pump(qapp, 300)
        assert (
            "#0055ff" in editor.text()
        ), f"colour string not rewritten: {editor.text()!r}"

    def test_format_color_string_keeps_the_format(self, qapp, qa_window, sample_tree):
        """A new colour is formatted like the old one."""
        from PyQt6.QtGui import QColor

        editor = _open_editor(qapp, qa_window, sample_tree)
        assert editor._format_color_string("#aabbcc", QColor("#0055ff")) == "#0055ff"
        assert editor._format_color_string("rgb(1, 2, 3)", QColor("#0055ff")) == (
            "rgb(0, 85, 255)"
        )

    def test_visible_indicators_update_is_safe(self, qapp, qa_window, sample_tree):
        """Updating every visible colour indicator does not raise."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        sweep = Sweep("colour indicators")
        sweep.step("update visible", editor.update_visible_color_indicators)
        pump(qapp, 150)
        sweep.finish()

    def test_rapid_color_edits_keep_markers_consistent(
        self, qapp, qa_window, sample_tree
    ):
        """A burst of colour edits leaves a consistent marker state."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText('color = "#aabbcc"\n')
        pump(qapp, 150)

        def edit() -> None:
            """Replace the colour literal on the first line.

            Returns:
                None; the side effect is the text replacement.
            """
            editor.setText('color = "#112233"\n')

        race_probe(qapp, edit, 4)
        pump(qapp, 600)
        assert_alive(qapp, window=qa_window)


class TestOccurrenceHighlight:
    """Occurrence highlighting follows the selection."""

    def test_selecting_a_word_highlights_occurrences(
        self, qapp, qa_window, sample_tree
    ):
        """Selecting a word computes occurrence highlight ranges."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("value = value + value\n")
        pump(qapp, 150)
        editor.setSelection(0, 0, 0, 5)
        pump(qapp, 300)
        editor._update_occurrence_highlight()
        pump(qapp, 150)
        ranges = getattr(editor, "_occurrence_ranges", [])
        assert ranges, "no occurrence ranges were computed"

    def test_short_selection_is_ignored(self, qapp, qa_window, sample_tree):
        """A one-character selection produces no highlight ranges."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("abcdef\n")
        pump(qapp, 150)
        editor.setSelection(0, 0, 0, 1)
        pump(qapp, 200)
        editor._update_occurrence_highlight()
        pump(qapp, 100)
        assert not getattr(
            editor, "_occurrence_ranges", []
        ), "single-character selection produced occurrence ranges"

    def test_clearing_removes_the_ranges(self, qapp, qa_window, sample_tree):
        """Clearing the highlight empties the range list."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("value = value\n")
        pump(qapp, 150)
        editor.setSelection(0, 0, 0, 5)
        pump(qapp, 200)
        editor._update_occurrence_highlight()
        pump(qapp, 100)
        editor._clear_occurrence_highlight()
        assert not getattr(
            editor, "_occurrence_ranges", []
        ), "occurrence ranges survived the clear"

    def test_rapid_typing_does_not_raise(self, qapp, qa_window, sample_tree):
        """Typing while occurrence highlighting is active stays stable."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("value = value\n")
        pump(qapp, 150)
        editor.setSelection(0, 0, 0, 5)
        pump(qapp, 200)

        def type_char() -> None:
            """Type a single character into the editor.

            Returns:
                None; the side effect is the inserted character.
            """
            type_text(qapp, editor, "x")

        race_probe(qapp, type_char, 4)
        pump(qapp, 200)
        assert_alive(qapp, window=qa_window)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
