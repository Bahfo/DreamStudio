"""
ConfigurationService: JSON-based configuration management.

Responsibilities:
- load / save / validate / repair / default / migrate
- never crash on missing or corrupt config
- recreate invalid config automatically when possible
- preserve user settings whenever safe
"""

import os
import json
import copy
import logging
import platform
import getpass
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR_NAME = ".configs"
CONFIG_FILE_NAME = "config.json"
CONFIG_VERSION = 2

DEFAULT_CONFIG: dict[str, Any] = {
    "version": CONFIG_VERSION,
    "general_info": {
        "module": "DreamStudio",
        "version": "1.0.0",
        "system": platform.system(),
        "node": platform.node(),
        "machine": platform.machine(),
        "user": getpass.getuser(),
    },
    "editor": {
        "theme": "dark",
        "font_family": "Segoe UI",
        "font_size": 12,
    },
    "workspace": {
        "last_directory": "",
    },
}


class ConfigurationService:
    """Manages JSON-based application configuration with fault tolerance."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir
        self._config_dir = os.path.join(base_dir, CONFIG_DIR_NAME)
        self._config_path = os.path.join(self._config_dir, CONFIG_FILE_NAME)
        self._data: dict[str, Any] = {}
        logger.info("ConfigurationService initialized for %s", self._config_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        """Load configuration, repairing or regenerating as needed."""
        self._ensure_config_dir()

        if not os.path.isfile(self._config_path):
            logger.warning("Config file not found, creating default config")
            self._data = copy.deepcopy(DEFAULT_CONFIG)
            self.save()
            return self._data

        try:
            with open(self._config_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to parse config file: %s", exc)
            self._data = self._repair_from_file(raw=None)
            return self._data

        if not isinstance(raw, dict):
            logger.warning("Config is not a dict, regenerating defaults")
            self._data = copy.deepcopy(DEFAULT_CONFIG)
            self.save()
            return self._data

        self._data = self._migrate(raw)
        self._data = self._validate(self._data)
        logger.info("Configuration loaded successfully (version %s)", self._data.get("version"))
        return self._data

    def save(self) -> None:
        """Persist current configuration to disk."""
        self._ensure_config_dir()
        try:
            with open(self._config_path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=4)
            logger.info("Configuration saved")
        except OSError as exc:
            logger.error("Failed to save config: %s", exc)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a top-level config value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a top-level config value and persist."""
        self._data[key] = value
        self.save()

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_config_dir(self) -> None:
        try:
            os.makedirs(self._config_dir, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create config directory %s: %s", self._config_dir, exc)
            raise

    def _migrate(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Apply version migrations. Returns merged dict."""
        version = raw.get("version", 1)
        if version < 2:
            logger.info("Migrating config from version %d to %d", version, CONFIG_VERSION)
            migrated = copy.deepcopy(DEFAULT_CONFIG)
            migrated["editor"].update(raw.get("editor", {}))
            migrated["workspace"].update(raw.get("workspace", {}))
            migrated["version"] = CONFIG_VERSION
            self._data = migrated
            self.save()
            return migrated
        return raw

    def _validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Ensure required sections exist, filling defaults where absent.
        Preserves unknown top-level keys so user additions survive."""
        merged = copy.deepcopy(data)
        for key, default_val in DEFAULT_CONFIG.items():
            if key not in merged:
                merged[key] = copy.deepcopy(default_val)
            elif isinstance(default_val, dict) and isinstance(merged[key], dict):
                section = copy.deepcopy(default_val)
                section.update(merged[key])
                merged[key] = section
        merged["version"] = CONFIG_VERSION
        return merged

    def _repair_from_file(self, raw: Any) -> dict[str, Any]:
        """Attempt to salvage partial config; fall back to defaults."""
        logger.warning("Attempting config repair")
        if isinstance(raw, dict):
            repaired = self._validate(raw)
            self._data = repaired
            self.save()
            return repaired
        self._data = copy.deepcopy(DEFAULT_CONFIG)
        self.save()
        return self._data
