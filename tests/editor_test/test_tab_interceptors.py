"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for close interceptors.
"""

import pytest


class TestTabCloseInterceptors:
    """Tests for close interceptors."""

    def test_interceptor_can_abort_close(self, qapp, tab_editor_parent, temp_workspace):
        """An interceptor returning False aborts close_editor."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))

        def abort_interceptor(index, editor):
            return False

        tabs.add_close_interceptor(abort_interceptor)

        tabs.close_editor(0)
        assert tabs.count() == 1

        tabs.remove_close_interceptor(abort_interceptor)
        tabs.close_editor(0)
        assert tabs.count() == 0

    def test_interceptor_exception_does_not_block_close(self, qapp, tab_editor_parent, temp_workspace):
        """An interceptor that raises is ignored (documented behaviour)."""
        from editor.Ironica.tab_editor import DreamTabbedEditor

        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        tabs = DreamTabbedEditor(tab_editor_parent)
        tabs.open_file_by_path(str(test_file))

        def broken_interceptor(index, editor):
            raise RuntimeError("interceptor failure")

        tabs.add_close_interceptor(broken_interceptor)
        tabs.close_editor(0)

        assert tabs.count() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])