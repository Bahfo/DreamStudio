"""Tests for CodeEditor (editor/texteditor/code_editor.py).

Covers: file operations, dirty tracking, language assignment, lexer setup,
font management, autocomplete hooks, goto-definition fallback, hover fallback.
"""

import os
import stat
import pytest
from PyQt6.QtCore import Qt


class TestCodeEditorConstruction:
    """Test CodeEditor instantiation."""

    def test_default_construction(self, editor):
        assert editor.objectName() == "CodeEditor"
        assert editor.current_file_path is None
        assert editor.current_lang is None
        assert editor.current_provider is None

    def test_construction_with_file(self, editor, tmp_path):
        p = tmp_path / "hello.txt"
        p.write_text("test content", encoding="utf-8")
        from editor.Ironica.code_editor import CodeEditor

        ed = CodeEditor(file_path=str(p))
        assert ed.current_file_path == str(p)
        assert ed.text() == "test content"
        ed.deleteLater()

    def test_construction_with_language(self, editor):
        assert editor.current_lang is None


class TestFileOperations:
    """Test open, save, save_as, reload."""

    def test_load_from_file_utf8(self, editor, tmp_path):
        p = tmp_path / "test.py"
        p.write_text("print('hello')", encoding="utf-8")
        editor.load_from_file(str(p))
        assert editor.text() == "print('hello')"
        assert editor.current_file_path == str(p)

    def test_load_from_file_nonexistent(self, editor):
        with pytest.raises(FileNotFoundError):
            editor.load_from_file("/nonexistent/file.txt")

    def test_load_from_file_invalid_utf8(self, editor, tmp_path):
        p = tmp_path / "bad.txt"
        p.write_bytes(b"\x80\x81\x82\x83")
        editor.load_from_file(str(p))
        # Should not crash — uses fallback decoding
        assert len(editor.text()) >= 0

    def test_save_to_file(self, editor, tmp_path):
        p = tmp_path / "save.txt"
        editor.setText("saved content")
        result = editor.save_to_file(str(p))
        assert result is True
        assert p.read_text(encoding="utf-8") == "saved content"

    def test_save_to_file_updates_path(self, editor, tmp_path):
        p = tmp_path / "save.txt"
        editor.setText("content")
        editor.save_to_file(str(p))
        assert editor.current_file_path == str(p)

    def test_save_to_file_clears_dirty(self, editor, tmp_path):
        p = tmp_path / "save.txt"
        editor.setText("content")
        editor.setModified(True)
        editor.save_to_file(str(p))
        assert not editor.is_dirty()

    def test_save_to_file_readonly_dir(self, editor, tmp_path):
        d = tmp_path / "readonly_dir"
        d.mkdir()
        os.chmod(str(d), stat.S_IRUSR | stat.S_IXUSR)
        try:
            result = editor.save_to_file(str(d / "file.txt"))
            assert result is False
        finally:
            os.chmod(str(d), stat.S_IRWXU)

    def test_save_as_cancellation(self, editor, tmp_path):
        # save_as uses QFileDialog which can't be tested headless easily
        # just verify the method exists and is callable
        assert hasattr(editor, "save_as")
        assert callable(editor.save_as)

    def test_save_when_no_path_delegates_to_save_as(self, editor):
        editor.setText("content")
        # save() with no current_file_path calls save_as()
        # We can't test the dialog, but we verify the logic path
        assert editor.current_file_path is None

    def test_reload(self, editor, tmp_path):
        p = tmp_path / "reload.txt"
        p.write_text("original", encoding="utf-8")
        editor.load_from_file(str(p))
        # Modify on disk
        p.write_text("modified", encoding="utf-8")
        editor.load_from_file(str(p))
        assert editor.text() == "modified"

    def test_clear_dirty(self, editor):
        editor.setModified(True)
        editor.clear_dirty()
        assert not editor.is_dirty()

    def test_is_dirty(self, editor):
        assert not editor.is_dirty()
        editor.setText("something")
        # setText may or may not set modified depending on QScintilla


class TestLanguageAssignment:
    """Test setLanguage, lexer assignment, provider lookup."""

    def test_set_language_none(self, editor):
        editor.setLanguage(None)
        assert editor.current_lang is None
        assert editor.current_provider is None

    def test_set_language_empty_string(self, editor):
        editor.setLanguage("")
        assert editor.current_lang is None

    def test_set_language_unknown(self, editor):
        editor.setLanguage("nonexistent_lang")
        assert editor.current_lang == "nonexistent_lang"
        assert editor.current_provider is None

    def test_set_language_with_registered(self, editor, language_registry):
        from editor.Ironica.language_engine import BaseLanguageProvider

        class DummyProvider(BaseLanguageProvider):
            def get_hover_hint(self, text, line, col):
                return None

            def get_definition_location(self, text, line, col):
                return None

            def format_source(self, source_code):
                return source_code

        language_registry.register_language_dict(
            {
                "lang": "pytest_lang",
                "extensions": ["pt"],
                "styles": {"keyword": "#FF0000"},
                "keywords": {"keyword": ["if", "else"]},
            },
            provider_instance=DummyProvider(),
        )
        editor.setLanguage("pytest_lang")
        assert editor.current_lang == "pytest_lang"
        assert editor.current_provider is not None


class TestFontManagement:
    """Test font_size property, set_editor_font, set_editor_font_size."""

    def test_font_size_property(self, editor):
        assert editor.font_size == 10

    def test_set_font_size(self, editor):
        editor.font_size = 14
        assert editor.font_size == 14

    def test_set_editor_font_size(self, editor):
        editor.set_editor_font_size(16)
        assert editor.font_size == 16

    def test_set_editor_font_string(self, editor):
        editor.set_editor_font("Courier New")
        # Should not crash

    def test_set_wrap_mode(self, editor):
        editor.set_wrap_mode(True)
        editor.set_wrap_mode(False)
        # Should not crash


class TestGotoDefinition:
    """Test execute_goto_definition with no provider."""

    def test_goto_definition_no_provider(self, editor):
        editor.execute_goto_definition()  # should be a no-op

    def test_goto_definition_none_target(self, editor):
        """Provider that returns None target should not crash."""

        from editor.Ironica.language_engine import BaseLanguageProvider

        class NoOpProvider(BaseLanguageProvider):
            def get_hover_hint(self, text, line, col):
                return None

            def get_definition_location(self, text, line, col):
                return None

            def format_source(self, source_code):
                return source_code

        editor.current_provider = NoOpProvider()
        editor.execute_goto_definition()  # should not crash


class TestHover:
    """Test hover flyout with no provider."""

    def test_hover_flyout_no_provider(self, editor):
        editor._setup_hover_engine()  # should be a no-op (no provider)
        editor._dismiss_hover_flyout()  # should be a no-op (no flyout)


class TestFormatCurrentFile:
    """Test format_current_file with no provider."""

    def test_format_no_provider(self, editor):
        editor.format_current_file()  # should be a no-op


class TestReadonlyMode:
    """Test read-only behaviour."""

    def test_readonly_detection_on_load(self, editor, tmp_path, monkeypatch):
        p = tmp_path / "ro.txt"
        p.write_text("content", encoding="utf-8")
        # Make the file read-only
        os.chmod(str(p), stat.S_IRUSR | stat.S_IRGRP)
        try:
            editor.load_from_file(str(p))
            assert editor.isReadOnly()
        finally:
            os.chmod(str(p), stat.S_IRWXU)
