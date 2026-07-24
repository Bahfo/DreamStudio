import json
import os

from PyQt6.QtWidgets import QFrame, QHBoxLayout
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt

# Local Imports
from editor.Ironica.utils.debug_frame import DebugControlFrame
from editor.widgets.QOptionsMenu import ToolbarMenuButton
from editor.widgets.QToolButton import ToolbarButton
from editor.widgets.QSeparator import Separator


class OptionsMenu(QFrame):
    BAR_POLICIES = {
        "compact": {
            "forbidden_ids": [],
            "max_items": 25,
            "required_ids": [],
        },
        "standard": {"forbidden_ids": [], "max_items": 30, "required_ids": []},
        "context_menu": {
            "forbidden_ids": [],
            "max_items": 10,
            "required_ids": [],
        },
    }

    def __init__(self, master, json_file=None, bar_type="standard"):
        super().__init__(master)
        self.master = master
        self.bar_type = bar_type if bar_type in self.BAR_POLICIES else "standard"

        self.setObjectName("OptionsMenu")
        self.setFrameShape(QFrame.Shape.Panel)
        self.setFixedHeight(35)

        self.optionsMenu_layout = QHBoxLayout(self)
        self.optionsMenu_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.optionsMenu_layout.setContentsMargins(5, 0, 5, 0)

        if json_file and os.path.exists(json_file):
            self._build_bar(json_file)
        # TODO: Add a guard method of json is not found

        # Method to add the debug session without activation so it floats inside the hero
        # container without guards.
        # Debug control frame is hidden until a debug session is active.
        # Parented to the main window (self.master) so it can be positioned
        # and dragged across the entire window, not just the options bar.
        self.debug_frame = DebugControlFrame(self.master)
        self.debug_frame.hide()

    def _validate_config(self, menu_data: list) -> None:
        """
        Validates the entire JSON structure against the selected bar_type rules
        before any UI widgets are instantiated.
        """
        policy = self.BAR_POLICIES[self.bar_type]

        present_ids = [item.get("id") for item in menu_data if "id" in item]

        for forbidden in policy["forbidden_ids"]:
            if forbidden in present_ids:
                raise ValueError(
                    f"Strict Rule Violation: Bar type '{self.bar_type}' "
                    f"is forbidden from containing '{forbidden}' elements."
                )

        if len(menu_data) > policy["max_items"]:
            raise ValueError(
                f"Strict Rule Violation: Bar type '{self.bar_type}' "
                f"exceeds max item limit of {policy['max_items']} (found {len(menu_data)})."
            )

        for required in policy["required_ids"]:
            if required not in present_ids:
                raise ValueError(
                    f"Strict Rule Violation: Bar type '{self.bar_type}' "
                    f"requires at least one '{required}' element."
                )

    def _build_bar(self, json_file):
        """Reads JSON contents, runs strict validations, and maps components."""
        try:
            with open(json_file, "r", encoding="utf-8") as file:
                menu_data = json.load(file)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e}")
            return

        try:
            self._validate_config(menu_data)
        except ValueError as error:
            print(f"UI Generation Aborted: {error}")
            return

        for item in menu_data:
            widget_id = item.get("id")

            if widget_id == "btn":
                icon_path = item.get("icon_path", "")
                tooltip = item.get("tooltip", "")
                size = tuple(item.get("size", [26, 26]))
                icon_size = tuple(item.get("icon_size", [16, 16]))

                callback_name = item.get("callback")
                callback_func = None
                if callback_name and hasattr(self.master, callback_name):
                    callback_func = getattr(self.master, callback_name)

                btn = ToolbarButton(
                    icon_path=icon_path,
                    tooltip=tooltip,
                    fixed_size=size,
                    icon_size=icon_size,
                    callback=callback_func,
                )
                self.optionsMenu_layout.addWidget(btn)

                # Keep a reference to the debug button so the session can
                # disable/re-enable it (Edge Case 3 — button state collision).
                if tooltip == "Debug Current File":
                    self._debug_button = btn

            elif widget_id == "sep":
                width = item.get("width", 2)
                height = item.get("height", 25)

                sep = Separator(_width=width, _height=height)
                self.optionsMenu_layout.addWidget(sep)

            elif widget_id == "menu":
                text = item.get("text", "")
                icon_path = item.get("icon_path", None)
                tooltip = item.get("tooltip", "")
                size = tuple(item.get("size", [100, 30]))
                icon_size = tuple(item.get("icon_size", [16, 16]))

                menu_btn = ToolbarMenuButton(
                    text=text,
                    icon_path=icon_path,
                    tooltip=tooltip,
                    fixed_size=size,
                    icon_size=icon_size,
                )

                for option in item.get("options", []):
                    if option.get("type") == "separator":
                        menu_btn.menu.addSeparator()
                    else:
                        opt_text = option.get("text", "")
                        opt_icon = option.get("icon_path", None)
                        opt_shortcut = option.get("shortcut", "")
                        opt_callback = option.get("callback")

                        action = QAction(opt_text, menu_btn.menu)
                        if opt_icon and os.path.exists(opt_icon):
                            action.setIcon(QIcon(opt_icon))
                        if opt_shortcut:
                            action.setShortcut(opt_shortcut)

                        if opt_callback and hasattr(self.master, opt_callback):
                            action.triggered.connect(getattr(self.master, opt_callback))

                        menu_btn.menu.addAction(action)

                self.optionsMenu_layout.addWidget(menu_btn)

            elif widget_id == "stretch":
                self.optionsMenu_layout.addStretch(1)

            elif widget_id == "frame":
                self.frame = QHBoxLayout()
                self.frame.setContentsMargins(0, 0, 0, 0)
                self.optionsMenu_layout.addLayout(self.frame)
