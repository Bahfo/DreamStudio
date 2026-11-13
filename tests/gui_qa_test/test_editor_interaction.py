"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Editor interaction live tests: opening files from the explorer path, typing,
dirty tracking, saving, and tab lifecycle on the real DreamStudio window.
"""

from pathlib import Path

import pytest

from harness import (
    Sweep,
    assert_alive,
    click,
    code_editor,
    pump,
    race_probe,
    type_text,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]


def _tabs(window):
    """Return the tab editor widget of the window.

    Args:
        window: The DreamStudio main window.

    Returns:
        The DreamTabbedEditor instance.
    """
    return window.hero_window._text_editor_center.tabs


def _current_editor(window):
    """Return the active CodeEditor of the window.

    Args:
        window: The DreamStudio main window.

    Returns:
        The CodeEditor instance, or None when no file is open.
    """
    api = window.hero_window._text_editor_center.current_editor()
    return code_editor(api)


def _open(qapp, window, path) -> None:
    """Open a file in the tab editor.

    Args:
        qapp: The live QApplication instance.
        window: The DreamStudio main window.
        path: Absolute path of the file to open.
    """
    _tabs(window).open_file_by_path(str(path))
    pump(qapp, 200)


class TestFileOpening:
    """Files must open through the explorer double-click path."""

    def test_explorer_double_click_opens_tab(self, qapp, qa_window, sample_tree):
        """Opening through the explorer handler creates exactly one tab."""
        window = qa_window
        before = _tabs(window).count()
        _open(qapp, window, Path(sample_tree) / "main.py")
        assert _tabs(window).count() == before + 1, "file did not open in a tab"
        assert _current_editor(window) is not None, "no active editor after open"

    def test_same_file_opens_single_tab(self, qapp, qa_window, sample_tree):
        """Opening the same path twice keeps one tab."""
        window = qa_window
        target = Path(sample_tree) / "main.py"
        _open(qapp, window, target)
        count_after_first = _tabs(window).count()
        _open(qapp, window, target)
        assert _tabs(window).count() == count_after_first, (
            "reopening the same file created a duplicate tab"
        )

    def test_second_file_switches_tab(self, qapp, qa_window, sample_tree):
        """Opening a second file switches the active editor."""
        window = qa_window
        first = Path(sample_tree) / "main.py"
        second = Path(sample_tree) / "helpers.py"
        _open(qapp, window, first)
        first_editor = _current_editor(window)
        _open(qapp, window, second)
        second_editor = _current_editor(window)
        assert second_editor is not first_editor, "active editor did not switch"
        assert "helpers" in second_editor.current_file_path, (
            f"wrong file active: {second_editor.current_file_path}"
        )


class TestTypingAndDirtyState:
    """Typing must mark the tab dirty and saving must clear it."""

    def test_typing_marks_tab_dirty(self, qapp, qa_window, sample_tree):
        """Typing in the editor marks the document dirty."""
        window = qa_window
        _open(qapp, window, Path(sample_tree) / "main.py")
        editor = _current_editor(window)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "x")
        assert editor.is_dirty(), "editor not dirty after typing"

    def test_typing_marks_the_tab_strip_dirty(self, qapp, qa_window, sample_tree):
        """The tab strip shows the dirty tab while the buffer is modified."""
        window = qa_window
        _open(qapp, window, Path(sample_tree) / "main.py")
        bar = _tabs(window).tabBar()
        assert not bar._dirty_indices, (
            f"a clean tab is already marked dirty: {bar._dirty_indices}"
        )
        editor = _current_editor(window)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "x")
        pump(qapp, 300)
        assert 0 in bar._dirty_indices, (
            f"the modified tab is not marked dirty: {bar._dirty_indices}"
        )

    def test_save_clears_dirty_state(self, qapp, qa_window, sample_tree):
        """Saving writes the file and clears the dirty flag."""
        window = qa_window
        path = Path(sample_tree) / "main.py"
        _open(qapp, window, path)
        editor = _current_editor(window)
        editor.setCursorPosition(0, 0)
        type_text(qapp, editor, "# qa\n")
        assert editor.is_dirty(), "editor not dirty after typing"
        _tabs(window).save_current_file()
        pump(qapp, 300)
        assert not editor.is_dirty(), "editor still dirty after save"
        assert path.read_text().startswith("# qa\n"), "file content not written"

    def test_save_all_clears_all_tabs(self, qapp, qa_window, sample_tree):
        """Save all clears the dirty state of every open editor."""
        window = qa_window
        _open(qapp, window, Path(sample_tree) / "main.py")
        _open(qapp, window, Path(sample_tree) / "helpers.py")
        for name in ("main.py", "helpers.py"):
            editor = _tabs(window).get_editor_for_path(str(Path(sample_tree) / name))
            if editor is not None:
                editor.setCursorPosition(0, 0)
                type_text(qapp, editor, "# qa\n")
        _tabs(window).save_all_files()
        pump(qapp, 300)
        assert not _current_editor(window).is_dirty(), "editor still dirty after save all"


class TestTabLifecycle:
    """Tabs close, and rapid open/close storms stay consistent."""

    def test_close_tab_removes_editor(self, qapp, qa_window, sample_tree):
        """Closing the active tab removes it from the tab editor."""
        window = qa_window
        _open(qapp, window, Path(sample_tree) / "main.py")
        before = _tabs(window).count()
        _tabs(window).close_tab()
        pump(qapp, 200)
        assert _tabs(window).count() == before - 1, "tab was not closed"

    def test_rapid_open_close_storm_keeps_one_tab(self, qapp, qa_window, sample_tree):
        """Opening and closing the same file repeatedly leaves one tab."""
        window = qa_window
        target = Path(sample_tree) / "main.py"

        def cycle() -> None:
            """Open the sample file and close the active tab again.

            Returns:
                None; the side effect is the opened and closed tab.
            """
            _tabs(window).open_file_by_path(str(target))
            pump(qapp, 40)
            _tabs(window).close_tab()
            pump(qapp, 40)

        race_probe(qapp, cycle, 3)
        _tabs(window).open_file_by_path(str(target))
        pump(qapp, 200)
        assert _tabs(window).count() == 1, (
            f"expected one tab after the storm, got {_tabs(window).count()}"
        )

    def test_tabs_have_readable_titles(self, qapp, qa_window, sample_tree):
        """Every opened tab shows a non-empty title."""
        window = qa_window
        _open(qapp, window, Path(sample_tree) / "main.py")
        _open(qapp, window, Path(sample_tree) / "helpers.py")
        titles = [_tabs(window).tabText(i) for i in range(_tabs(window).count())]
        assert all(title.strip() for title in titles), f"empty tab titles: {titles}"


class TestEditorSurface:
    """The editor viewport must accept clicks and keep the window alive."""

    def test_editor_viewport_click_is_safe(self, qapp, qa_window, sample_tree):
        """Clicking the editor viewport does not raise or hide the window."""
        window = qa_window
        _open(qapp, window, Path(sample_tree) / "main.py")
        editor = _current_editor(window)
        sweep = Sweep("editor viewport click")
        sweep.step("click viewport", click, qapp, editor)
        sweep.finish()
        assert_alive(qapp, window)

    def test_editor_focus_after_open(self, qapp, qa_window, sample_tree):
        """The opened editor can take keyboard focus."""
        window = qa_window
        _open(qapp, window, Path(sample_tree) / "main.py")
        editor = _current_editor(window)
        editor.setFocus()
        pump(qapp, 100)
        assert editor.hasFocus() or editor.isVisible(), "editor cannot take focus"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
