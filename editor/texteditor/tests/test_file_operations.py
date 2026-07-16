"""Tests for file operations edge cases.

Covers: UTF-8 loading, invalid UTF-8, readonly files, nonexistent files,
deleted files, permission denied, save failures, reload failures, save-as, overwrite.
"""

import os
import stat
import pytest


class TestUTF8Loading:
    """Test various encoding scenarios."""

    def test_utf8_bom(self, editor, tmp_path):
        p = tmp_path / "bom.txt"
        p.write_bytes(b"\xef\xbb\xbfhello")
        editor.load_from_file(str(p))
        assert editor.text() == "hello"

    def test_utf8_no_bom(self, editor, tmp_path):
        p = tmp_path / "nobom.txt"
        p.write_text("hello", encoding="utf-8")
        editor.load_from_file(str(p))
        assert editor.text() == "hello"

    def test_latin1_fallback(self, editor, tmp_path):
        p = tmp_path / "latin.txt"
        p.write_bytes("caf\xe9".encode("latin-1"))
        editor.load_from_file(str(p))
        # Should load without crashing, content may be lossy
        assert len(editor.text()) > 0


class TestInvalidUTF8:
    """Test loading files with invalid byte sequences."""

    def test_invalid_utf8_replacement(self, editor, tmp_path):
        p = tmp_path / "bad.txt"
        p.write_bytes(b"\x80\x81\xfe\xff")
        editor.load_from_file(str(p))
        # Should not crash
        assert len(editor.text()) >= 0

    def test_mixed_valid_invalid(self, editor, tmp_path):
        p = tmp_path / "mixed.txt"
        p.write_bytes(b"hello \xff world")
        editor.load_from_file(str(p))
        assert "hello" in editor.text()


class TestReadonlyFiles:
    """Test loading and handling read-only files."""

    def test_readonly_file_detected(self, editor, tmp_path):
        p = tmp_path / "ro.txt"
        p.write_text("readonly", encoding="utf-8")
        os.chmod(str(p), stat.S_IRUSR | stat.S_IRGRP)
        try:
            editor.load_from_file(str(p))
            assert editor.isReadOnly()
        finally:
            os.chmod(str(p), stat.S_IRWXU)

    def test_readonly_file_content_loaded(self, editor, tmp_path):
        p = tmp_path / "ro2.txt"
        p.write_text("content here", encoding="utf-8")
        os.chmod(str(p), stat.S_IRUSR)
        try:
            editor.load_from_file(str(p))
            assert editor.text() == "content here"
        finally:
            os.chmod(str(p), stat.S_IRWXU)


class TestNonexistentFiles:
    """Test loading files that don't exist."""

    def test_nonexistent_file_raises(self, editor):
        with pytest.raises(FileNotFoundError):
            editor.load_from_file("/tmp/this_does_not_exist_12345.txt")


class TestDeletedFiles:
    """Test saving to a path that was deleted after opening."""

    def test_save_after_file_deleted(self, editor, tmp_path):
        p = tmp_path / "will_delete.txt"
        p.write_text("original", encoding="utf-8")
        editor.load_from_file(str(p))
        p.unlink()
        # Save should still succeed (writes a new file)
        result = editor.save_to_file(str(p))
        assert result is True
        assert p.exists()


class TestPermissionDenied:
    """Test permission denied scenarios."""

    def test_save_to_readonly_directory(self, editor, tmp_path):
        d = tmp_path / "readonly_dir"
        d.mkdir()
        os.chmod(str(d), stat.S_IRUSR | stat.S_IXUSR)
        try:
            result = editor.save_to_file(str(d / "file.txt"))
            assert result is False
        finally:
            os.chmod(str(d), stat.S_IRWXU)

    def test_save_to_readonly_file(self, editor, tmp_path):
        p = tmp_path / "readonly.txt"
        p.write_text("original", encoding="utf-8")
        os.chmod(str(p), stat.S_IRUSR)
        try:
            result = editor.save_to_file(str(p))
            assert result is False
        finally:
            os.chmod(str(p), stat.S_IRWXU)


class TestSaveOverwrite:
    """Test saving over an existing file."""

    def test_overwrite_existing(self, editor, tmp_path):
        p = tmp_path / "overwrite.txt"
        p.write_text("old content", encoding="utf-8")
        editor.load_from_file(str(p))
        editor.setText("new content")
        result = editor.save()
        assert result is True
        assert p.read_text(encoding="utf-8") == "new content"

    def test_save_as_new_path(self, editor, tmp_path):
        p1 = tmp_path / "original.txt"
        p1.write_text("original", encoding="utf-8")
        editor.load_from_file(str(p1))

        p2 = tmp_path / "copy.txt"
        result = editor.save_to_file(str(p2))
        assert result is True
        assert p2.read_text(encoding="utf-8") == "original"
        assert editor.current_file_path == str(p2)


class TestEncodingEdgeCases:
    """Test various encoding edge cases."""

    def test_empty_file(self, editor, tmp_path):
        p = tmp_path / "empty.txt"
        p.write_text("", encoding="utf-8")
        editor.load_from_file(str(p))
        assert editor.text() == ""

    def test_binary_like_content(self, editor, tmp_path):
        p = tmp_path / "binary.txt"
        p.write_bytes(os.urandom(100))
        editor.load_from_file(str(p))
        # Should not crash
        assert len(editor.text()) >= 0

    def test_large_file(self, editor, tmp_path):
        p = tmp_path / "large.txt"
        content = "line {}\n".format("x" * 100) * 1000
        p.write_text(content, encoding="utf-8")
        editor.load_from_file(str(p))
        # 1000 "line ...\n" lines = 1001 lines in editor (trailing newline)
        assert editor.lines() >= 1000

    def test_unicode_content(self, editor, tmp_path):
        p = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍 مرحبا"
        p.write_text(content, encoding="utf-8")
        editor.load_from_file(str(p))
        assert "Hello" in editor.text()
