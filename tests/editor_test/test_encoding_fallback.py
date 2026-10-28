"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the documented encoding fallback chain.
"""

import pytest


class TestEncodingFallback:
    """Tests for the documented encoding fallback chain."""

    def test_utf8_loads(self, qapp, temp_workspace):
        """A plain UTF-8 file loads intact."""
        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "utf8.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        editor = CodeEditor(None)
        editor.load_from_file(str(test_file))

        assert "hello" in editor.text()

    def test_utf8_sig_loads_without_bom(self, qapp, temp_workspace):
        """A UTF-8 BOM file loads and the BOM is stripped."""
        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "utf8_sig.py"
        test_file.write_text("print('hello')", encoding="utf-8-sig")

        editor = CodeEditor(None)
        editor.load_from_file(str(test_file))

        assert editor.text().startswith("print('hello')")

    def test_undecodable_bytes_never_raise(self, qapp, temp_workspace):
        """The final fallback decodes with errors='replace' (invariant E4)."""
        from editor.Ironica.code_editor import CodeEditor

        test_file = temp_workspace / "binary.py"
        test_file.write_bytes(b"print('\xff\xfe')")

        editor = CodeEditor(None)
        editor.load_from_file(str(test_file))

        assert "\ufffd" in editor.text()

    def test_missing_file_raises_file_not_found(self, qapp, temp_workspace):
        """Loading a missing file raises FileNotFoundError."""
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor(None)

        with pytest.raises(FileNotFoundError):
            editor.load_from_file(str(temp_workspace / "missing.py"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])