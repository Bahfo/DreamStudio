import json
import os

from PyQt6.QtWidgets import QFrame, QVBoxLayout
from PyQt6.QtCore import Qt

# Local Imports
from editor.widgets.QToolButton import ToolbarButton


class VerticalSidebar(QFrame):
    """
    A vertical sidebar that houses multiple buttons configured to a certain task.
    Displays buttons stacked vertically with fixed width.
    """

    BAR_POLICIES = {
        "compact": {
            "forbidden_ids": ["sep", "menu"],
            "max_items": 12,
            "required_ids": [],
        },
        "standard": {"forbidden_ids": [], "max_items": 15, "required_ids": []},
    }

    def __init__(self, master, json_file=None, bar_type="standard"):
        super().__init__(master)
        self.master = master
        self.bar_type = bar_type if bar_type in self.BAR_POLICIES else "standard"

        self.setObjectName("VerticalSidebar")
        self.setFrameShape(QFrame.Shape.Panel)
        self.setFixedWidth(45)

        self.sidebar_layout = QVBoxLayout(self)
        self.sidebar_layout.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
        )
        self.sidebar_layout.setContentsMargins(0, 5, 0, 5)
        self.sidebar_layout.setSpacing(2)

        if json_file and os.path.exists(json_file):
            self._build_bar(json_file)

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
                size = tuple(item.get("size", [35, 35]))
                icon_size = tuple(item.get("icon_size", [28, 28]))

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
                if callback_func:
                    btn.setCheckable(True)
                    btn.setChecked(True)
                self.sidebar_layout.addWidget(btn)

            elif widget_id == "stretch":
                self.sidebar_layout.addStretch(1)
