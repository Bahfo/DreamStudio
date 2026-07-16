from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QLabel, QLineEdit, QWidgetAction

import json
import logging

logger = logging.getLogger(__name__)


class CommandWindow(QMenu):
    def __init__(self, hanging_widget, parent=None):
        # hanging_widget: The widget that the commands window will hang under.
        # Must be of type QPushButton or any type of its instance.
        super().__init__(parent=parent)
        self.setFixedWidth(600)
        self._build_actions()
        self._parent = parent
        self._hang_widget = hanging_widget

    def _build_actions(self):
        search_action = QWidgetAction(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type a command...")
        search_action.setDefaultWidget(self.search_input)
        self.addAction(search_action)
        self.addSeparator()

        tip_action = QWidgetAction(self)
        self.tip_label = QLabel(
            "TIP: Type to search a command, navigate by keyboard arrows."
        )
        self.tip_label.setStyleSheet("""background-color: transparent;
            padding: 8px 18px 8px 18px;
            font-size: 12px;
            font-family: 'Segoe UI';""")
        tip_action.setDefaultWidget(self.tip_label)
        self.addAction(tip_action)

        self._command_actions = []
        self._load_commands_list()
        self.search_input.textChanged.connect(self._filter_commands)

    def _load_commands_list(self):
        try:
            with open("editor/utils/tools/json/commands_list.json", "r") as file:
                commands = json.load(file)
            for command, display in commands.items():
                action = QAction(command, self)
                action.setData(display)
                action.triggered.connect(
                    lambda checked=False, c=command: self._on_choosing_command(c)
                )
                self.addAction(action)
                self._command_actions.append(action)

        except Exception as e:
            logger.error("Failed to load commands: %s", e)
            err_action = QAction(f"Error loading commands: {e}", self)
            err_action.setEnabled(False)
            self.addAction(err_action)

    def _filter_commands(self, text):
        """Triggered automatically every time the user types a letter."""
        search_text = text.lower()
        for action in self._command_actions:
            is_match = search_text in action.text().lower()
            action.setVisible(is_match)

    def _on_choosing_command(self, command):
        logger.info("Executing command: %s", command)

    def _show(self, event):
        corner_left = self._hang_widget.rect().bottomLeft()
        global_pos = self._hang_widget.mapToGlobal(corner_left)
        self.exec(global_pos)
