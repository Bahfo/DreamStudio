"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Find/Replace Widget for Global Solution Find and Replace.
"""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMenu,
    QLabel,
    QFrame,
    QWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidgetAction,
)
from PyQt6.QtCore import Qt

import logging

logger = logging.getLogger(__name__)


class FindReplace(QMenu):
    def __init__(self, hanging_widget, parent=None):
        # hanging_widget: The widget that the items.
        # Must be of type QPushButton or any type of its instance.
        super().__init__(parent=parent)
        self.setFixedWidth(600)
        self._build_actions()
        self._parent = parent
        self._hang_widget = hanging_widget

    def _build_actions(self):
        form_action = QWidgetAction(self)
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in Solution")
        form_layout.addWidget(self.search_input)

        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0, 0, 0, 4)
        options_layout.setSpacing(6)

        self.btn_match_case = QPushButton("Aa")
        self.btn_match_word = QPushButton('""')
        self.btn_regex = QPushButton(".*")

        for btn in (self.btn_match_case, self.btn_match_word, self.btn_regex):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            options_layout.addWidget(btn)

        options_layout.addStretch()
        form_layout.addLayout(options_layout)

        self.replace_container = QFrame()
        self.replace_container.setObjectName("replaceContainer")
        rc_layout = QHBoxLayout(self.replace_container)
        rc_layout.setContentsMargins(2, 2, 4, 2)
        rc_layout.setSpacing(4)

        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with")
        self.replace_input.setObjectName("replaceInput")

        self.btn_replace_all = QPushButton("Replace All")
        self.btn_replace_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_replace_all.setObjectName("btnReplaceAll")

        rc_layout.addWidget(self.replace_input)
        rc_layout.addWidget(self.btn_replace_all)
        form_layout.addWidget(self.replace_container)

        self.btn_toggle_filters = QPushButton("▾ File Filters")
        self.btn_toggle_filters.setCheckable(True)
        self.btn_toggle_filters.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_filters.setObjectName("filterToggle")
        form_layout.addWidget(self.btn_toggle_filters)

        self.filters_container = QWidget()
        f_layout = QVBoxLayout(self.filters_container)
        f_layout.setContentsMargins(8, 0, 0, 0)
        f_layout.setSpacing(6)

        self.include_input = QLineEdit()
        self.include_input.setPlaceholderText("Files to include (e.g. *.py, *.json)")

        self.exclude_input = QLineEdit()
        self.exclude_input.setPlaceholderText("Files to exclude (e.g. *test*, venv/)")

        f_layout.addWidget(self.include_input)
        f_layout.addWidget(self.exclude_input)
        self.filters_container.setVisible(False)
        form_layout.addWidget(self.filters_container)

        self.btn_toggle_filters.toggled.connect(
            lambda checked: (
                self.filters_container.setVisible(checked),
                self.btn_toggle_filters.setText(
                    "▴ File Filters" if checked else "▾ File Filters"
                ),
            )
        )

        form_action.setDefaultWidget(form_widget)
        self.addAction(form_action)
        self.addSeparator()

        tip_action = QWidgetAction(self)
        self.tip_label = QLabel("TIP: Type to search, navigate by keyboard arrows.")
        self.tip_label.setObjectName("tipLabel")
        tip_action.setDefaultWidget(self.tip_label)
        self.addAction(tip_action)

    def _show(self, event):
        corner_left = self._hang_widget.rect().bottomLeft()
        global_pos = self._hang_widget.mapToGlobal(corner_left)
        self.exec(global_pos)
