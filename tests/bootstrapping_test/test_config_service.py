"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for ConfigurationService loading and validation.
"""

import json

import pytest


class TestConfigurationService:
    """Tests for ConfigurationService loading and validation."""

    def test_load_creates_default_config(self, temp_config_dir):
        """load() creates .configs/config.json with defaults when missing."""
        from config.config import ConfigurationService

        config_dir = temp_config_dir / ".configs"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        assert not config_file.exists()

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()

        assert config_file.exists()
        assert config["version"] == 2
        assert config["editor"]["theme"] == "dark"
        assert config["workspace"]["last_directory"] == ""

    def test_load_existing_config_merges_defaults(self, temp_config_dir):
        """Loading existing config keeps user values and fills defaults."""
        from config.config import ConfigurationService

        config_dir = temp_config_dir / ".configs"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        existing = {
            "version": 2,
            "editor": {"theme": "light"},
            "workspace": {"last_directory": "/home/user"},
        }
        config_file.write_text(json.dumps(existing))

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()

        assert config["editor"]["theme"] == "light"
        assert "font_family" in config["editor"]
        assert "font_size" in config["editor"]
        assert config["workspace"]["last_directory"] == "/home/user"

    def test_save_persists_current_data(self, temp_config_dir):
        """save() persists the in-memory config to disk."""
        from config.config import ConfigurationService

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()
        config["editor"]["theme"] = "tokyonight"
        service.save()

        saved = json.loads((temp_config_dir / ".configs" / "config.json").read_text())
        assert saved["editor"]["theme"] == "tokyonight"

    def test_repair_corrupt_config(self, temp_config_dir):
        """Corrupt config is repaired and the original backed up."""
        from config.config import ConfigurationService

        config_dir = temp_config_dir / ".configs"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text("{ invalid json")

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()

        assert config["version"] == 2
        assert "editor" in config
        assert (temp_config_dir / ".configs" / "config.json.corrupt.bak").exists()
        assert json.loads(config_file.read_text())["version"] == 2

    def test_get_and_set_top_level_sections(self, temp_config_dir):
        """get/set operate on top-level configuration sections."""
        from config.config import ConfigurationService

        service = ConfigurationService(base_dir=str(temp_config_dir))
        service.load()

        editor = service.get("editor")
        assert editor["theme"] == "dark"
        assert service.get("missing", default="fallback") == "fallback"

        service.set("editor", {**editor, "theme": "light"})
        reloaded = ConfigurationService(base_dir=str(temp_config_dir))
        assert reloaded.load()["editor"]["theme"] == "light"

    def test_migrates_version_one_config(self, temp_config_dir):
        """Version 1 configs are migrated to schema version 2."""
        from config.config import ConfigurationService

        config_dir = temp_config_dir / ".configs"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": 1, "editor": {"theme": "monokai"}}))

        service = ConfigurationService(base_dir=str(temp_config_dir))
        config = service.load()

        assert config["version"] == 2
        assert config["editor"]["theme"] == "monokai"
        assert json.loads(config_file.read_text())["version"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])