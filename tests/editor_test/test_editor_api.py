"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the EditorAPI per-tab facade.
"""

import pytest


class TestEditorAPIFacade:
    """Tests for the EditorAPI per-tab facade."""

    def test_editor_api_requires_editor(self, qapp):
        """EditorAPI rejects a None editor."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        with pytest.raises(ValueError):
            EditorAPI(None)

        editor = QsciScintilla()
        api = EditorAPI(editor)
        assert api.editor is editor

    def test_read_only_blocks_mutations(self, qapp):
        """Mutating methods no-op on a read-only editor."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        editor = QsciScintilla()
        editor.setText("original")
        editor.setReadOnly(True)

        api = EditorAPI(editor)
        api.cut()
        api.paste()
        api.delete()
        api.indent()
        api.unindent()
        api.duplicate_line()

        assert editor.text() == "original"

    def test_clipboard_methods_exist(self, qapp):
        """Clipboard methods exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        for name in (
            "cut",
            "copy",
            "copy_as_plain_text",
            "paste",
            "delete",
            "select_all",
            "select_none",
        ):
            assert hasattr(api, name), name

    def test_history_methods_exist(self, qapp):
        """Undo/redo exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        assert hasattr(api, "undo")
        assert hasattr(api, "redo")

    def test_structure_methods_exist(self, qapp):
        """Structural editing methods exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        for name in (
            "indent",
            "unindent",
            "format_code",
            "comment_line",
            "comment",
            "uncomment_line",
            "uncomment",
            "duplicate_line",
            "duplicate_selection",
        ):
            assert hasattr(api, name), name

    def test_navigation_methods_exist(self, qapp):
        """Implemented navigation methods exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        for name in (
            "goto_definition",
            "goto_declaration",
            "goto_implementation",
        ):
            assert hasattr(api, name), name

    def test_folding_methods_exist(self, qapp):
        """Folding methods exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        for name in (
            "expand_current",
            "expand_all",
            "collapse_current",
            "smart_collapse",
            "collapse_includes",
        ):
            assert hasattr(api, name), name

    def test_file_methods_exist(self, qapp):
        """load_file/save exist on EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        assert hasattr(api, "load_file")
        assert hasattr(api, "save")

    def test_set_language_method_exists(self, qapp):
        """Contract gap: documented set_language() is absent from EditorAPI."""
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.api import EditorAPI

        api = EditorAPI(QsciScintilla())

        assert hasattr(api, "set_language")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])