"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Find/Replace Widget for Global Solution Find and Replace.
"""

from editor import *

# Local Imports
from editor.utils.find_replace.search_engine import SearchWorker

logger = logging.getLogger(__name__)


class FindReplace(QFrame):
    """
    A global find and replace popup resembling modern IDE structure.

    Attributes:
        _parent: The parent widget.
        _hang_widget (QWidget): The widget this popup visually hangs from.
    """

    def __init__(self, hanging_widget, current_directory, parent=None):
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
        self.current_directory = current_directory
        self._build_ui()

        self.searchWorker = None
        self._connect_signals()

    def _build_ui(self):
        """Builds the internal UI components directly into the frame's layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in Solution")
        search_row.addWidget(self.search_input)

        self.btn_clear = QPushButton("\u2715")
        self.btn_clear.setFixedSize(24, 24)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setToolTip("Clear results and inputs")
        self.btn_clear.setObjectName("btnClear")
        search_row.addWidget(self.btn_clear)

        main_layout.addLayout(search_row)

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

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("menuSeparator")
        main_layout.addWidget(separator)

        self.tip_label = QLabel("TIP: Type to search, navigate by keyboard arrows.")
        self.tip_label.setObjectName("tipLabel")
        main_layout.addWidget(self.tip_label)

        self.results_list = QListWidget()
        self.results_list.setObjectName("resultsList")
        self.results_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.results_list.setVisible(False)
        self.results_list.setUniformItemSizes(True)
        self.results_list.setMaximumHeight(700)
        self.results_list.adjustSize()
        self.results_list.setStyleSheet("""
            QListWidget {
              border: none;
              outline: none;
              padding: 2px;
            }
            QListWidget::item {
              padding: 4px 8px;
              height: 22px;
              border: none;
            }
        """)
        main_layout.addWidget(self.results_list)

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

    def _connect_signals(self):
        """Connect UI events to the search logic."""
        self.search_input.returnPressed.connect(self.start_search)
        self.btn_clear.clicked.connect(self._clear_all)
        self.results_list.itemDoubleClicked.connect(self._on_result_clicked)

    def start_search(self):
        term = self.search_input.text()
        if not term:
            return

        if self.searchWorker and self.searchWorker.isRunning():
            self.searchWorker.cancel()
            self.searchWorker.wait()

        self.results_list.clear()
        self.results_list.setVisible(True)
        self.results_list.addItem(f"Searching for '{term}")
        self._update_results_height()

        self.adjustSize()

        self.searchWorker = SearchWorker(
            directory=self.current_directory,
            term=term,
            match_case=self.btn_match_case.isChecked(),
            match_word=self.btn_match_word.isChecked(),
            is_regex=self.btn_regex.isChecked(),
            includes=self.include_input.text(),
            excludes=self.exclude_input.text(),
        )

        self.searchWorker.match_found.connect(self.on_match_found)
        self.searchWorker.finished.connect(self.on_search_finished)
        self.searchWorker.error.connect(self.on_search_error)

        # Start the thread
        self.searchWorker.start()

    def on_match_found(self, filepath, line_num, line_content):
        """Fired every time the worker finds a match."""
        if self.results_list.count() == 1 and self.results_list.item(
            0
        ).text().startswith("Searching"):
            self.results_list.clear()

        filename = os.path.basename(filepath)
        display_text = f"{filename}:{line_num} - {line_content}"
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, filepath)
        item.setData(Qt.ItemDataRole.UserRole + 1, line_num)
        self.results_list.addItem(item)
        self._update_results_height()

    def on_search_finished(self, total_matches):
        if self.results_list.count() > 0 and self.results_list.item(
            0
        ).text().startswith("Searching"):
            self.results_list.clear()

        if total_matches == 0:
            self.results_list.addItem("No matches found.")
        else:
            self.tip_label.setText(f"Found {total_matches} matches.")

    def on_search_error(self, error_msg):
        self.results_list.addItem(f"Error: {error_msg}")

    def _on_result_clicked(self, item: QListWidgetItem):
        """Navigate to the file and line of the clicked search result."""
        filepath = item.data(Qt.ItemDataRole.UserRole)
        line_num = item.data(Qt.ItemDataRole.UserRole + 1)
        if filepath is None or line_num is None:
            return

        if self._parent is not None and hasattr(self._parent, "tab_editors"):
            self._parent.tab_editors.open_file_at_line(filepath, line_num - 1)
            self.hide()

    def _clear_all(self):
        """Cancel any running search, clear all inputs and results."""
        if self.searchWorker and self.searchWorker.isRunning():
            self.searchWorker.cancel()
            self.searchWorker.wait()

        self.search_input.clear()
        self.replace_input.clear()
        self.include_input.clear()
        self.exclude_input.clear()
        self.results_list.clear()
        self.results_list.setVisible(False)
        self._update_results_height()
        self.tip_label.setText("TIP: Type to search, navigate by keyboard arrows.")
        self.adjustSize()

    def _update_results_height(self, max_visible_items: int = 14):
        count = self.results_list.count()
        if count == 0:
            self.results_list.setFixedHeight(0)
        else:
            row_h = self.results_list.sizeHintForRow(0)
            if row_h <= 0:
                row_h = 30

            visible_rows = min(count, max_visible_items)
            frame_borders = self.results_list.frameWidth() * 2 + 4
            target_height = (visible_rows * row_h) + frame_borders
            self.results_list.setFixedHeight(target_height)

        self.adjustSize()
