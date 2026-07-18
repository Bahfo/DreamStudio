"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Find/Replace Widget for Global Solution Find and Replace.
"""

from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class FindReplace(QFrame):
    """
    A global find and replace popup resembling modern IDE structure.

    Attributes:
        _parent: The parent widget.
        _hang_widget (QWidget): The widget this popup visually hangs from.
    """

    def __init__(self, hanging_widget, parent=None):
        """
        Initializes the FindReplace popup.

        Args:
            hanging_widget: The widget that anchors the popup.
            parent: The parent widget for memory management.
        """
        super().__init__(parent=parent)

        # NOTE: Popup flag makes it act like a menu (auto-closes on click away)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("FindReplaceMenu")
        self.setFixedWidth(600)

        self._parent = parent
        self._hang_widget = hanging_widget
        self._build_ui()

    def _build_ui(self):
        """Builds the internal UI components directly into the frame's layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in Solution")
        main_layout.addWidget(self.search_input)

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
        main_layout.addLayout(options_layout)

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
        main_layout.addWidget(self.replace_container)

        self.btn_toggle_filters = QPushButton("▾ File Filters")
        self.btn_toggle_filters.setCheckable(True)
        self.btn_toggle_filters.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_filters.setObjectName("filterToggle")
        main_layout.addWidget(self.btn_toggle_filters)

        self.filters_container = QWidget()
        self.filters_container.setStyleSheet("background-color: transparent;")
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
        main_layout.addWidget(self.filters_container)

        self.btn_toggle_filters.toggled.connect(self._on_filters_toggled)

        # Separator line replacement for QMenu.addSeparator()
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("menuSeparator")
        main_layout.addWidget(separator)

        self.tip_label = QLabel("TIP: Type to search, navigate by keyboard arrows.")
        self.tip_label.setObjectName("tipLabel")
        main_layout.addWidget(self.tip_label)

    def _on_filters_toggled(self, checked: bool):
        """
        Handles the expansion of the filter UI and resizes the popup window.

        Args:
            checked: True if the filters should be visible, False otherwise.
        """
        self.filters_container.setVisible(checked)
        self.btn_toggle_filters.setText(
            "▴ File Filters" if checked else "▾ File Filters"
        )
        self.adjustSize()

    def _show(self, event=None):
        """Displays the popup precisely below the hanging widget."""
        corner_left = self._hang_widget.rect().bottomLeft()
        global_pos = self._hang_widget.mapToGlobal(corner_left)
        self.move(global_pos)
        self.show()
