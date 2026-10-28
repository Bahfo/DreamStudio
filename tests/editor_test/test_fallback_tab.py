"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for FallBack tabs when a file cannot be shown normally.
"""

from unittest.mock import patch

import pytest


class TestFallbackTab:
    """Tests for FallBack tabs when a file cannot be shown normally."""

    def test_binary_file_opens_binary_editor(self, qapp, tab_editor_parent, temp_workspace):
        """ELF paths are routed to add_binary_editor."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "binary"
        test_file.write_bytes(b"\x7fELF")

        tabs = DreamTabbedEditor(tab_editor_parent)

        with (
            patch.object(DreamTabbedEditor, "_is_elf_binary", return_value=True),
            patch.object(DreamTabbedEditor, "add_binary_editor") as add_binary,
        ):
            tabs.open_file_by_path(str(test_file))

        add_binary.assert_called_once()

    def test_decode_error_opens_fallback(self, qapp, tab_editor_parent, temp_workspace):
        """A UnicodeDecodeError during load creates a FallBack tab."""
        from editor.Ironica.code_editor import CodeEditor
        from editor.Ironica.tab_editor import DreamTabbedEditor, FallBack

        test_file = temp_workspace / "bad.py"
        test_file.write_bytes(b"\xff\xfe")

        tabs = DreamTabbedEditor(tab_editor_parent)

        error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        with patch.object(CodeEditor, "load_from_file", side_effect=error):
            tabs.open_file_by_path(str(test_file))

        assert tabs.count() == 1
        assert isinstance(tabs.widget(0), FallBack)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])