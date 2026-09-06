"""
ResourceManager: theme, icon, font, and static asset loading.

Uses fallbacks for missing resources. Never terminates startup
because an optional asset is unavailable.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_FALLBACK_THEME = "dark.qss"


class ResourceManager:
    """Loads and verifies application resources with fallback support."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir
        self._qss_dir = os.path.join(base_dir, "editor", "qss")
        self._assets_dir = os.path.join(base_dir, "assets")
        self._system_icons_dir = os.path.join(self._assets_dir, "system")
        self._menu_icons_dir = os.path.join(self._assets_dir, "menus")
        self._type_icons_dir = os.path.join(self._assets_dir, "types")
        self._editor_icons_dir = os.path.join(self._assets_dir, "editor")

        self._theme_cache: dict[str, str] = {}
        self._missing: list[str] = []
        logger.info("ResourceManager initialized for %s", base_dir)

    # ------------------------------------------------------------------
    # Theme loading
    # ------------------------------------------------------------------

    def load_theme(self, theme_name: str = "dark") -> str:
        """Load a QSS theme by name. Falls back to dark.qss on failure."""
        qss_file = f"{theme_name}.qss"
        qss_path = os.path.join(self._qss_dir, qss_file)

        if qss_path in self._theme_cache:
            return self._theme_cache[qss_path]

        content = self._read_file(qss_path)
        if content is None:
            logger.warning("Theme '%s' not found, falling back to '%s'", theme_name, _FALLBACK_THEME)
            fallback_path = os.path.join(self._qss_dir, _FALLBACK_THEME)
            content = self._read_file(fallback_path)
            if content is None:
                logger.error("Fallback theme '%s' also missing", _FALLBACK_THEME)
                return ""

        self._theme_cache[qss_path] = content
        logger.info("Theme loaded: %s", theme_name)
        return content

    def available_themes(self) -> list[str]:
        """Return list of available theme names (without extension)."""
        try:
            files = os.listdir(self._qss_dir)
        except OSError:
            return []
        return sorted(f.replace(".qss", "") for f in files if f.endswith(".qss"))

    # ------------------------------------------------------------------
    # Icon loading
    # ------------------------------------------------------------------

    def get_icon_path(self, icon_name: str, category: str = "system") -> Optional[str]:
        """Resolve an icon path. Returns None if missing (never crashes)."""
        dir_map = {
            "system": self._system_icons_dir,
            "menus": self._menu_icons_dir,
            "types": self._type_icons_dir,
            "editor": self._editor_icons_dir,
        }
        base = dir_map.get(category, self._system_icons_dir)
        path = os.path.join(base, icon_name)
        if os.path.isfile(path):
            return path
        # Handle names without extension or with different extension
        name_without_ext, ext = os.path.splitext(icon_name)
        if ext.lower() != ".png":
            path_png = os.path.join(base, name_without_ext + ".png")
            if os.path.isfile(path_png):
                return path_png
        self._missing.append(f"{category}/{icon_name}")
        logger.warning("Icon not found: %s/%s", category, icon_name)
        return None

    # ------------------------------------------------------------------
    # Asset verification
    # ------------------------------------------------------------------

    def verify_assets(self) -> dict[str, bool]:
        """Verify that key asset directories exist."""
        checks = {
            "qss_dir": os.path.isdir(self._qss_dir),
            "assets_dir": os.path.isdir(self._assets_dir),
            "system_icons": os.path.isdir(self._system_icons_dir),
            "menu_icons": os.path.isdir(self._menu_icons_dir),
            "type_icons": os.path.isdir(self._type_icons_dir),
            "editor_icons": os.path.isdir(self._editor_icons_dir),
        }
        for name, exists in checks.items():
            if not exists:
                logger.warning("Asset directory missing: %s", name)
        return checks

    def missing_resources(self) -> list[str]:
        """Return list of resources that were requested but not found."""
        return list(self._missing)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _read_file(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Cannot read %s: %s", path, exc)
            return None
