from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QLineEdit, QWidgetAction, QLabel

import logging
import json


class CommandWindow(QMenu):
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent=parent)
        self._theme_manager = theme_manager
        self.setFixedWidth(600)
        self._build_actions()
        self._apply_style()

    def _apply_style(self):
        t = self._theme_manager
        self.setStyleSheet(
            f"""
            QMenu {{
                background-color: {t.color("menu.background")};
                color: {t.color("menu.text")};
                border: 1px solid {t.color("menu.border")};
                padding: 6px 0px;
                font-family: 'inter', Arial;
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 8px 28px 8px 18px;
                background: transparent;
            }}
            QMenu::item:selected {{
                background-color: {t.color("menu.selected")};
            }}
            QMenu::separator {{
                height: 1px;
                background: {t.color("menu.separator")};
                margin: 6px 10px;
            }}
            QMenu::right-arrow {{
                image: none;
            }}
            
            QLineEdit {{
                background-color: transparent;
                color: {t.color("menu.text")};
                border: none;
                padding: 8px 18px;
                font-family: 'inter', Arial;
                font-size: 13px;
            }}
        """
        )

    def retheme(self, t):
        self._theme_manager = t
        self._apply_style()

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
        self.tip_label.setStyleSheet(
            """background-color: transparent; 
            padding: 8px 18px 8px 18px;
            font-size: 12px; 
            font-family: 'inter';"""
        )
        tip_action.setDefaultWidget(self.tip_label)
        self.addAction(tip_action)

        self._command_actions = []
        self._load_commands_list()
        self.search_input.textChanged.connect(self._filter_commands)

    def _load_commands_list(self):
        try:
            with open("editor/utils/tools/commands_list.json", "r") as file:
                commands = json.load(file)
            for command, display in commands.items():
                action = QAction(command, self)
                action.setData(display)
                self.addAction(action)
                self._command_actions.append(action)

        except Exception as e:
            self.addAction(f"Error loading commands: {e}").setEnabled(False)

    def _filter_commands(self, text):
        """Triggered automatically every time the user types a letter."""
        search_text = text.lower()

        for action in self._command_actions:
            is_match = search_text in action.text().lower()
            action.setVisible(is_match)
