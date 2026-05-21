import json
import logging
import pathlib
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

THEME_DIR = pathlib.Path("assets/themes")

LIGHT_COLORS = {
    "window.background": "#F3F3F3",
    "window.text": "#333333",
    "widget.background": "#FFFFFF",
    "widget.border": "#E0E0E0",
    "widget.text": "#333333",
    "widget.text_bright": "#1A1A1A",
    "widget.accent": "#0066B8",
    "tab.background": "#F3F3F3",
    "tab.selected_bg": "#E0E0E0",
    "tab.selected_border": "#C0C0C0",
    "tab.hover_bg": "#E8E8E8",
    "tab.hover_border": "#C0C0C0",
    "tab.inactive_bg": "#F3F3F3",
    "tab.inactive_border": "#F3F3F3",
    "tab.text_selected": "#1A1A1A",
    "tab.text_inactive": "#666666",
    "tab.dirty_dot": "#333333",
    "sidebar.background": "#F0F0F0",
    "sidebar.text": "#333333",
    "sidebar.button_bg": "transparent",
    "sidebar.button_hover": "#D0D0D0",
    "button.background": "transparent",
    "button.hover": "#D0D0D0",
    "button.text": "#333333",
    "optionsbar.background": "#E8E8E8",
    "optionsbar.separator": "#CCCCCC",
    "statusbar.background": "#E8E8E8",
    "statusbar.text": "#333333",
    "titlebar.background": "#005A9E",
    "titlebar.text": "#FFFFFF",
    "editor.background": "#FFFFFF",
    "editor.text": "#333333",
    "editor.selection_bg": "#ADD6FF",
    "editor.selection_fg": "#1A1A1A",
    "editor.caret": "#1A1A1A",
    "editor.margin_bg": "#F3F3F3",
    "editor.margin_fg": "#666666",
    "editor.line_number": "#858585",
    "input.background": "#FFFFFF",
    "input.border": "#CCCCCC",
    "input.focus_border": "#0066B8",
    "input.text": "#333333",
    "input.placeholder": "#999999",
    "scrollbar.bg": "transparent",
    "scrollbar.fg": "#C0C0C0",
    "scrollbar.hover": "#A0A0A0",
    "treeview.background": "#F0F0F0",
    "treeview.text": "#333333",
    "treeview.highlight": "#B3D4F7",
    "treeview.header_bg": "#E0E0E0",
    "treeview.header_text": "#666666",
    "terminal.background": "#FFFFFF",
    "terminal.text": "#333333",
    "terminal.input_bg": "#F5F5F5",
    "terminal.input_border": "#CCCCCC",
    "terminal.selection": "#ADD6FF",
    "find_replace.background": "#F5F5F5",
    "find_replace.border": "#CCCCCC",
    "find_replace.input_bg": "#FFFFFF",
    "find_replace.result_match": "#333333",
    "find_replace.result_no_match": "#FF5555",
    "hints.background": "#E8E8E8",
    "hints.text": "#0066B8",
    "hints.desc": "#333333",
    "splitter.handle": "#CCCCCC",
    "splitter.handle_pressed": "#0066B8",
    "workspace_splitter": "#CCCCCC",
    "ether_ai.background": "#F3F3F3",
    "welcome.background": "transparent",
    "welcome.title": "#1A1A1A",
    "welcome.subtitle": "#666666",
    "welcome.start_label": "#1A1A1A",
    "welcome.action": "#0066B8",
    "welcome.action_hover": "#005A9E",
    "welcome.footer": "#666666",
    "menu.background": "#FFFFFF",
    "menu.text": "#333333",
    "menu.border": "#CCCCCC",
    "menu.selected": "#D4E3F3",
    "menu.separator": "#E0E0E0",
    "menubar.background": "transparent",
    "menubar.text": "#D1D1D1",
    "menubar.text_bright": "#FFFFFF",
    "menubar.selected": "rgba(63, 65, 69, 0.2)",
    "titlebar.btn_hover": "rgba(255, 255, 255, 0.1)",
    "tab.hover_dark": "#444444",
    "sidebar.button_hover_dark": "#333333",
    "welcome.background_dark": "transparent",
    "hints.key_bg": "#3C3C3C",
    "notifications.button_hover": "#333333",
    "terminal.prompt": "#569CD6",
    "leftmost.background": "#E8E8E8",
    "minimap.background": "#F5F5F5",
    "minimap.border": "#E0E0E0",
    "tooltip.background": "#FFFFFF",
    "tooltip.text": "#333333",
    "tooltip.border": "#CCCCCC",
    "syntax.string": "#A31515",
    "syntax.comment": "#008000",
    "syntax.number": "#098658",
    "syntax.keyword": "#0000FF",
    "syntax.definition": "#795E26",
    "syntax.import": "#AF00DB",
    "syntax.type": "#267F99",
    "syntax.function": "#795E26",
    "syntax.operator": "#000000",
    "syntax.json_key": "#001080",
    "syntax.collection": "#0451A5",
    "syntax.meta": "#808080",
    "syntax.iterator": "#098658",
    "syntax.exception": "#F14C4C",
    "syntax.warning": "#FF8C00",
    "syntax.execution_logic": "#795E26",
    "syntax.logic": "#0000FF",
}

DARK_COLORS = {
    "window.background": "#1E1E1E",
    "window.text": "#CCCCCC",
    "widget.background": "#252526",
    "widget.border": "#3C3C3C",
    "widget.text": "#CCCCCC",
    "widget.text_bright": "#FFFFFF",
    "widget.accent": "#007ACC",
    "tab.background": "#1E1E1E",
    "tab.selected_bg": "#25324D",
    "tab.selected_border": "#35538F",
    "tab.hover_bg": "#2D2D2D",
    "tab.hover_border": "#3C3F41",
    "tab.inactive_bg": "#1E1E1E",
    "tab.inactive_border": "#1E1E1E",
    "tab.text_selected": "#FFFFFF",
    "tab.text_inactive": "#AFB1B3",
    "tab.dirty_dot": "#FFFFFF",
    "sidebar.background": "#171717",
    "sidebar.text": "#CCCCCC",
    "sidebar.button_bg": "transparent",
    "sidebar.button_hover": "#333333",
    "button.background": "transparent",
    "button.hover": "#333333",
    "button.text": "#FFFFFF",
    "optionsbar.background": "#25272B",
    "optionsbar.separator": "#444444",
    "statusbar.background": "#25272B",
    "statusbar.text": "#FFFFFF",
    "titlebar.background": "#00438A",
    "titlebar.text": "#FFFFFF",
    "editor.background": "#1E1E1E",
    "editor.text": "#D4D4D4",
    "editor.selection_bg": "#264F78",
    "editor.selection_fg": "#FFFFFF",
    "editor.caret": "#FFFFFF",
    "editor.margin_bg": "#1E1E1E",
    "editor.margin_fg": "#D4D4D4",
    "editor.line_number": "#858585",
    "input.background": "#3C3C3C",
    "input.border": "#3C3C3C",
    "input.focus_border": "#007ACC",
    "input.text": "#D4D4D4",
    "input.placeholder": "#858585",
    "scrollbar.bg": "transparent",
    "scrollbar.fg": "#424242",
    "scrollbar.hover": "#555555",
    "treeview.background": "#171717",
    "treeview.text": "#afb1b3",
    "treeview.highlight": "#2d476d",
    "treeview.header_bg": "#313335",
    "treeview.header_text": "#afb1b3",
    "terminal.background": "#1e1e1e",
    "terminal.text": "#d4d4d4",
    "terminal.input_bg": "#252526",
    "terminal.input_border": "#3c3c3c",
    "terminal.selection": "#264f78",
    "find_replace.background": "#252526",
    "find_replace.border": "#454545",
    "find_replace.input_bg": "#3C3C3C",
    "find_replace.result_match": "#C5C5C5",
    "find_replace.result_no_match": "#FF5555",
    "hints.background": "#2D2D2D",
    "hints.text": "#569CD6",
    "hints.desc": "#CCCCCC",
    "splitter.handle": "#2a2a2a",
    "splitter.handle_pressed": "#3a7bd5",
    "workspace_splitter": "#1a1a1a",
    "ether_ai.background": "#1E1E1E",
    "welcome.background": "transparent",
    "welcome.title": "#FFFFFF",
    "welcome.subtitle": "#cccccc",
    "welcome.start_label": "#FFFFFF",
    "welcome.action": "#3794ef",
    "welcome.action_hover": "#4daafc",
    "welcome.footer": "#cccccc",
    "menu.background": "#2B2D30",
    "menu.text": "#D1D1D1",
    "menu.border": "#3F4145",
    "menu.selected": "#2E436E",
    "menu.separator": "#3F4145",
    "menubar.background": "transparent",
    "menubar.text": "#D1D1D1",
    "menubar.text_bright": "#FFFFFF",
    "menubar.selected": "rgba(63, 65, 69, 0.2)",
    "titlebar.btn_hover": "rgba(255, 255, 255, 0.1)",
    "tab.hover_dark": "#444444",
    "sidebar.button_hover_dark": "#333333",
    "welcome.background_dark": "transparent",
    "hints.key_bg": "#2D2D2D",
    "notifications.button_hover": "#333333",
    "terminal.prompt": "#569CD6",
    "leftmost.background": "#25272B",
    "minimap.background": "#252526",
    "minimap.border": "#2A2A2A",
    "tooltip.background": "#2B2D30",
    "tooltip.text": "#D1D1D1",
    "tooltip.border": "#3F4145",
    "syntax.string": "#CE9178",
    "syntax.comment": "#6A9955",
    "syntax.number": "#B5CEA8",
    "syntax.keyword": "#569CD6",
    "syntax.definition": "#4FC1FF",
    "syntax.import": "#C586C0",
    "syntax.type": "#4EC9B0",
    "syntax.function": "#DCDCAA",
    "syntax.operator": "#D4D4D4",
    "syntax.json_key": "#9CDCFE",
    "syntax.collection": "#9CDCFE",
    "syntax.meta": "#808080",
    "syntax.iterator": "#B5CEA8",
    "syntax.exception": "#F44747",
    "syntax.warning": "#FFCC66",
    "syntax.execution_logic": "#DCDCAA",
    "syntax.logic": "#569CD6",
}


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._current_theme: str = "dark"
        self._data: dict = {}
        self._load_theme(self._current_theme)

    def _load_theme(self, name: str) -> None:
        if name == "dark":
            self._data = dict(DARK_COLORS)
        elif name == "light":
            self._data = dict(LIGHT_COLORS)
        else:
            path = THEME_DIR / f"{name}.json"
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._data = json.load(f).get("colors", {})
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load theme '{name}': {e}")
                self._data = dict(DARK_COLORS)

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
