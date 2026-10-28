"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for editor navigation: the per-tab facade delegation.
"""

from unittest.mock import MagicMock

import pytest


class TestEditorAPINavigationDelegation:
    """EditorAPI navigation methods must invoke their matching handler."""

    @staticmethod
    def _api():
        from editor.Ironica.api import EditorAPI

        editor = MagicMock()
        editor.isReadOnly.return_value = False
        return EditorAPI(editor), editor

    def test_goto_definition_delegates_to_definition_handler(self):
        """goto_definition calls execute_goto_definition."""
        api, editor = self._api()

        api.goto_definition(4, 2)

        editor.execute_goto_definition.assert_called_once_with(4, 2)

    def test_goto_declaration_delegates_to_declaration_handler(self):
        """Contract gap: goto_declaration must not reuse the definition handler."""
        api, editor = self._api()

        api.goto_declaration(4, 2)

        editor.execute_goto_definition.assert_not_called()
        editor.execute_goto_declaration.assert_called_once_with(4, 2)

    def test_goto_implementation_delegates_to_implementation_handler(self):
        """Contract gap: goto_implementation must use its own handler."""
        api, editor = self._api()

        api.goto_implementation(4, 2)

        editor.execute_goto_definition.assert_not_called()
        editor.execute_goto_implementation.assert_called_once_with(4, 2)

    @pytest.mark.parametrize(
        "method_name",
        [
            "goto_usage",
            "goto_reference",
            "find_usages",
            "goto_implementation_file",
        ],
    )
    def test_documented_navigation_methods_exist(self, qapp, method_name):
        """Contract gap: methods documented in editor-model.md are missing."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        assert hasattr(api, method_name), f"EditorAPI.{method_name} is documented but not implemented"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])