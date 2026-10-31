"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the real CodeEditor navigation pipeline.
"""

from unittest.mock import MagicMock

import pytest


class TestCodeEditorDefinitionNavigation:
    """Tests for the real CodeEditor navigation pipeline."""

    @staticmethod
    def _editor_with_provider(provider):
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        editor.setText("value = call()\n")
        editor.current_file_path = "/workspace/test.py"
        editor.current_provider = provider
        return editor

    def test_definition_navigation_calls_provider_and_navigates(self, qapp):
        """A single definition target is opened at the returned line."""
        provider = MagicMock()
        provider.has_folding.return_value = False
        provider.has_diagnostics.return_value = False
        provider.get_definition_location.return_value = [("/workspace/other.py", 7, 3)]

        editor = self._editor_with_provider(provider)
        editor._request_async_navigation = MagicMock(return_value=False)
        editor._navigate_to_targets = MagicMock()

        editor.execute_goto_definition(2, 5)

        called_args = provider.get_definition_location.call_args
        # First attempt uses the extended signature; TypeError triggers the
        # three-argument fallback, but a MagicMock accepts any signature.
        assert called_args.args[1:3] == (2, 5)
        editor._navigate_to_targets.assert_called_once_with(
            [("/workspace/other.py", 7, 3)],
            2,
            "/workspace/test.py",
            kind="definition",
        )

    def test_definition_navigation_without_provider_is_noop(self, qapp):
        """No provider means no navigation attempt."""
        editor = self._editor_with_provider(None)
        editor._request_async_navigation = MagicMock(return_value=False)
        editor._navigate_to_targets = MagicMock()

        editor.execute_goto_definition(0, 0)

        editor._navigate_to_targets.assert_not_called()

    def test_definition_navigation_without_targets_shows_failure(self, qapp):
        """An empty provider result triggers the failure notification path."""
        provider = MagicMock()
        provider.get_definition_location.return_value = None

        editor = self._editor_with_provider(provider)
        editor._request_async_navigation = MagicMock(return_value=False)
        editor._show_navigation_failure = MagicMock()

        editor.execute_goto_definition(0, 0)

        editor._show_navigation_failure.assert_called_once()

    def test_single_target_opens_file_at_line(self, qapp):
        """_navigate_to_targets asks the tab container to open the target."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        editor.setText("line\n" * 10)
        editor._parent = MagicMock()
        editor._parent.currentWidget.return_value = editor

        editor._navigate_to_targets(
            [("/workspace/other.py", 7, 3)], 0, "/workspace/test.py"
        )

        editor._parent.open_file_at_line.assert_called_once_with(
            "/workspace/other.py", 7
        )
        assert editor.getCursorPosition() == (7, 3)

    def test_same_file_same_line_target_is_ignored(self, qapp):
        """Navigating to the current line is a no-op."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)
        editor._parent = MagicMock()

        editor._navigate_to_targets(
            [("/workspace/test.py", 4, 0)], 4, "/workspace/test.py"
        )

        editor._parent.open_file_at_line.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
