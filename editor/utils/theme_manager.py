import json
import logging
import pathlib

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

THEME_DIR = pathlib.Path("assets/themes")


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._current_theme: str = "dark"
        self._data: dict = {}
        self._load_theme(self._current_theme)

    def _load_theme(self, name: str) -> None:
        path = THEME_DIR / f"{name}.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._data = json.load(f).get("colors", {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load theme '{name}': {e}")
            self._data = {}

    def color(self, key: str, fallback: str = "#000000") -> str:
        return self._data.get(key, fallback)

    @property
    def name(self) -> str:
        return self._current_theme

    def switch_to(self, name: str) -> None:
        if name == self._current_theme:
            return
        self._load_theme(name)
        self._current_theme = name
        self.theme_changed.emit(name)
        logger.info("Switched to theme: %s", name)

    def toggle(self) -> str:
        next_theme = "light" if self._current_theme == "dark" else "dark"
        self.switch_to(next_theme)
        return next_theme


class SyntaxThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self, theme_manager: ThemeManager, parent: QObject = None):
        super().__init__(parent)
        self._main = theme_manager
        self._current_theme: str = "dark"
        self._data: dict = {}
        self._load_theme(self._current_theme)

    def _load_theme(self, name: str) -> None:
        path = THEME_DIR / f"{name}.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._data = json.load(f).get("colors", {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load syntax theme '{name}': {e}")
            self._data = {}

    def color(self, key: str, fallback: str = "#000000") -> str:
        if key.startswith("syntax."):
            return self._data.get(key, self._main.color(key, fallback))
        return self._main.color(key, fallback)

    @property
    def name(self) -> str:
        return self._current_theme

    def switch_to(self, name: str) -> None:
        if name == self._current_theme:
            return
        self._load_theme(name)
        self._current_theme = name
        self.theme_changed.emit(name)
        logger.info("Switched to syntax theme: %s", name)

    def toggle(self) -> str:
        next_theme = "light" if self._current_theme == "dark" else "dark"
        self.switch_to(next_theme)
        return next_theme
