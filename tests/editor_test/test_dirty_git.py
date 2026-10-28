"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the dirty flag requesting a VCS status scan.
"""

from unittest.mock import patch

import pytest


class TestDirtyDrivesGit:
    """Tests for the dirty flag requesting a VCS status scan."""

    def test_dirty_true_requests_git_scan(self, qapp, tab_editor_parent):
        """A dirty editor requests a git scan tagged editor:dirty_true."""
        from editor.Ironica.tab_editor import DreamTabbedEditor
        from editor.utils.git_control import status_service

        tabs = DreamTabbedEditor(tab_editor_parent)

        with patch.object(status_service, "get_status_service") as get_service:
            tabs._on_editor_dirty_changed_explicit(tabs, True)

        get_service.return_value.request_scan.assert_called_once_with("editor:dirty_true")

    def test_dirty_false_requests_git_scan(self, qapp, tab_editor_parent):
        """A saved editor requests a git scan tagged editor:dirty_false."""
        from editor.Ironica.tab_editor import DreamTabbedEditor
        from editor.utils.git_control import status_service

        tabs = DreamTabbedEditor(tab_editor_parent)

        with patch.object(status_service, "get_status_service") as get_service:
            tabs._on_editor_dirty_changed_explicit(tabs, False)

        get_service.return_value.request_scan.assert_called_once_with("editor:dirty_false")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])