"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for ResourceManager theme and asset loading.
"""

import pytest


class TestResourceManager:
    """Tests for ResourceManager theme and asset loading."""

    def test_load_theme_falls_back_to_dark(self, project_root):
        """Unknown theme names fall back to dark.qss."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        qss = manager.load_theme("nonexistent_theme")

        assert qss
        assert "QMainWindow" in qss
        assert "background-color" in qss

    def test_load_theme_caches(self, project_root):
        """Second load returns the cached content."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        first = manager.load_theme("dark")
        second = manager.load_theme("dark")

        assert first is second
        assert len(manager._theme_cache) == 1

    def test_available_themes(self, project_root):
        """Available themes lists shipped theme names."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        themes = manager.available_themes()

        assert "dark" in themes
        assert "light" in themes
        assert "tokyonight" in themes
        assert len(themes) >= 14

    def test_get_icon_path_resolves_system_icon(self, project_root):
        """Icon resolution finds a shipped system icon."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        path = manager.get_icon_path("add.png", category="system")

        assert path is not None
        assert path.endswith("add.png")

    def test_get_icon_path_missing_returns_none(self, project_root):
        """Missing icons return None and are tracked."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        path = manager.get_icon_path("definitely_missing_icon.png")

        assert path is None
        assert "system/definitely_missing_icon.png" in manager.missing_resources()

    def test_verify_assets(self, project_root):
        """Asset verification reports every expected directory as present."""
        from config.resources import ResourceManager

        manager = ResourceManager(base_dir=str(project_root))
        result = manager.verify_assets()

        assert isinstance(result, dict)
        assert result
        assert all(result.values()), f"Missing asset directories: {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])