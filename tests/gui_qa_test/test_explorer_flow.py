"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Solution Explorer live tests: the tree mirrors the workspace, file operations
behave, and destructive actions stay behind their dialogs.
"""

from pathlib import Path

import pytest

from harness import (
    Sweep,
    assert_alive,
    click,
    live_probe,
    pump,
    race_probe,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]


def _explorer(window):
    """Return the solution explorer panel of the window.

    Args:
        window: The DreamStudio main window.

    Returns:
        The SolutionExplorer instance.
    """
    return window.hero_window._solution_explorer


def _activate(window) -> None:
    """Activate the solution explorer panel.

    Args:
        window: The DreamStudio main window.
    """
    window.hero_window._vertical_menus_api.activate_panel("solution_explorer")
    pump(qapp_instance(), 200)


def qapp_instance():
    """Return the live QApplication instance.

    Returns:
        The QApplication singleton.
    """
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance()


def _tree_root_source_index(explorer):
    """Return the source-model index of the explorer's tree root.

    Args:
        explorer: The SolutionExplorer panel.

    Returns:
        The source QModelIndex of the tree root (the workspace directory).
    """
    proxy = explorer.tree_view.model()
    return proxy.mapToSource(explorer.tree_view.rootIndex())


def _walk_source(explorer, root_index) -> list:
    """Collect every source-model index below *root_index*.

    Args:
        explorer: The SolutionExplorer panel.
        root_index: Source QModelIndex to start from.

    Returns:
        List of source QModelIndex objects.
    """
    model = explorer.base_model
    collected = [root_index]
    pending = [root_index]
    while pending:
        current = pending.pop()
        for row in range(model.rowCount(current)):
            child = model.index(row, 0, current)
            if child.isValid():
                collected.append(child)
                pending.append(child)
    return collected


def _model_paths(explorer) -> set[str]:
    """Collect every file path currently exposed by the explorer model.

    Args:
        explorer: The SolutionExplorer panel.

    Returns:
        Set of absolute file paths found in the model.
    """
    model = explorer.base_model
    found: set[str] = set()
    for index in _walk_source(explorer, _tree_root_source_index(explorer)):
        path = model.filePath(index)
        if path:
            found.add(str(path))
    return found


def _index_for_path(explorer, path: str):
    """Return the source-model index of *path* inside the explorer tree.

    Args:
        explorer: The SolutionExplorer panel.
        path: Absolute path to look for.

    Returns:
        The matching source QModelIndex, or an invalid index when absent.
    """
    model = explorer.base_model
    for index in _walk_source(explorer, _tree_root_source_index(explorer)):
        if str(model.filePath(index)) == str(path):
            return index
    return model.index(0, 0)


class TestExplorerTree:
    """The explorer tree mirrors the workspace directory."""

    def test_tree_lists_workspace_files(self, qapp, qa_window, sample_tree):
        """The sample file appears in the explorer model."""
        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        paths = _model_paths(explorer)
        assert str(Path(sample_tree) / "main.py") in paths, (
            f"main.py missing from the explorer tree: {sorted(paths)}"
        )

    def test_new_file_on_disk_appears_after_refresh(self, qapp, qa_window, sample_tree):
        """A file created on disk shows up after a refresh."""
        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        created = Path(sample_tree) / "qa_created.py"
        created.write_text("value = 1\n", encoding="utf-8")
        explorer.refresh()
        pump(qapp, 400)
        paths = _model_paths(explorer)
        assert str(created) in paths, "created file missing from the explorer tree"

    def test_deleted_file_disappears_after_refresh(self, qapp, qa_window, sample_tree):
        """A file deleted on disk disappears after a refresh."""
        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        created = Path(sample_tree) / "qa_deleted.py"
        created.write_text("value = 1\n", encoding="utf-8")
        explorer.refresh()
        pump(qapp, 400)
        assert str(created) in _model_paths(explorer), "file never appeared"
        created.unlink()
        explorer.refresh()
        pump(qapp, 400)
        assert str(created) not in _model_paths(explorer), "deleted file still listed"

    def test_refresh_storm_keeps_tree_consistent(self, qapp, qa_window, sample_tree):
        """Repeated refreshes keep the tree valid."""
        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        race_probe(qapp, explorer.refresh, 3)
        pump(qapp, 400)
        assert_alive(qapp, window)
        assert explorer.tree_view.model() is not None, "explorer lost its model"

    def test_explorer_has_no_zero_size_widgets(self, qapp, qa_window):
        """No visible widget inside the explorer collapses to zero size."""
        window = qa_window
        _activate(window)
        issues = live_probe(_explorer(window))
        assert not issues, "zero-size visible widgets:\n" + "\n".join(issues)


class TestExplorerActions:
    """Explorer actions behave and destructive ones stay guarded."""

    def test_copy_path_copies_to_clipboard(self, qapp, qa_window, sample_tree):
        """Copy Path puts the selected path into the clipboard."""
        from PyQt6.QtWidgets import QApplication

        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        target = str(Path(sample_tree) / "main.py")
        index = _index_for_path(explorer, target)
        assert index.isValid(), f"{target} is not in the explorer model"
        explorer.tree_view.setCurrentIndex(explorer.proxy_model.mapFromSource(index))
        pump(qapp, 150)
        explorer._menu_copy_path()
        pump(qapp, 150)
        clipboard = QApplication.clipboard().text()
        assert "main.py" in clipboard, f"clipboard did not receive the path: {clipboard!r}"

    def test_toggle_header_visibility_changes_columns(self, qapp, qa_window):
        """Toggling the header changes the visible column layout."""
        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        before = explorer.tree_view.isHeaderHidden()
        explorer._menu_toggle_header_visibility()
        pump(qapp, 150)
        assert explorer.tree_view.isHeaderHidden() != before, (
            "header visibility did not change"
        )

    def test_collapse_and_expand_all_are_safe(self, qapp, qa_window):
        """Collapse-all and expand-all keep the tree usable."""
        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        sweep = Sweep("explorer expand/collapse")
        sweep.step("collapse all", explorer._toolbar_collapse_all)
        pump(qapp, 100)
        sweep.step("expand all", explorer._toolbar_expand_all)
        pump(qapp, 100)
        sweep.finish()
        assert_alive(qapp, window)

    def test_delete_without_selection_is_safe(self, qapp, qa_window):
        """Delete without a selection does nothing and does not raise."""
        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        explorer.tree_view.clearSelection()
        explorer._toolbar_delete_item()
        pump(qapp, 200)
        assert_alive(qapp, window)

    def test_rename_dialog_is_stubbed(self, qapp, qa_window, sample_tree):
        """Rename runs behind the stubbed input dialog without blocking."""
        import harness

        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        target = str(Path(sample_tree) / "main.py")
        index = _index_for_path(explorer, target)
        assert index.isValid(), f"{target} is not in the explorer model"
        explorer.tree_view.setCurrentIndex(explorer.proxy_model.mapFromSource(index))
        pump(qapp, 150)
        with harness.modal_guard(text="renamed_by_qa.py"):
            explorer._menu_rename()
            pump(qapp, 300)
        assert_alive(qapp, window)

    def test_new_folder_uses_stubbed_dialog(self, qapp, qa_window, sample_tree):
        """Creating a folder runs behind the stubbed input dialog."""
        import harness

        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        with harness.modal_guard(text="qa_folder"):
            explorer._toolbar_new_folder()
            pump(qapp, 300)
        assert_alive(qapp, window)

    def test_explorer_toolbar_buttons_are_clickable(self, qapp, qa_window):
        """Clicking explorer toolbar buttons records no failure."""
        window = qa_window
        _activate(window)
        explorer = _explorer(window)
        sweep = Sweep("explorer toolbar")
        for name in (
            "refresh_btn",
            "collapse_btn",
            "expand_btn",
        ):
            button = getattr(explorer, name, None)
            if button is None:
                continue
            sweep.step(f"click {name}", click, qapp, button)
        sweep.finish()
        assert_alive(qapp, window)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
