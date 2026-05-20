from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QPushButton,
    QLineEdit,
    QWidget,
    QFrame,
    QLabel,
)


class SourceControl(QFrame):
    def __init__(self, _parent=None):
        super().__init__(_parent)
        self._parent = _parent
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #171717; border: none;")

        # Setup main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(12)
        commit_section = QVBoxLayout()
        commit_section.setSpacing(6)

        self.main_layout.addSpacing(10)
        self.search_label = QLabel("SOURCE CONTROL")
        self.search_label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        self.main_layout.addWidget(self.search_label)
        self.main_layout.addSpacing(10)

        # Commit message text field
        self.commit_input = QLineEdit()
        self.commit_input.setPlaceholderText("Commit message (Ctrl+Enter to commit)")
        self.commit_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #007acc; }
        """)

        self.btn_commit = QPushButton("Commit")
        self.btn_commit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_commit.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #1177bb; }
        """)
        self.btn_commit.clicked.connect(self.handle_commit)

        commit_section.addWidget(self.commit_input)
        commit_section.addWidget(self.btn_commit)
        self.main_layout.addLayout(commit_section)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)

        self.staged_section = GitSectionHeader("STAGED CHANGES")
        self.unstaged_section = GitSectionHeader("CHANGES")
        self.untracked_section = GitSectionHeader("UNTRACKED FILES")

        self.staged_files_layout = QVBoxLayout()
        self.unstaged_files_layout = QVBoxLayout()
        self.untracked_files_layout = QVBoxLayout()

        self.scroll_layout.addWidget(self.staged_section)
        self.scroll_layout.addLayout(self.staged_files_layout)

        self.scroll_layout.addWidget(self.unstaged_section)
        self.scroll_layout.addLayout(self.unstaged_files_layout)

        self.scroll_layout.addWidget(self.untracked_section)
        self.scroll_layout.addLayout(self.untracked_files_layout)
        self.scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        self.main_layout.addWidget(scroll_area)
        self.refresh_git_status()

    def handle_commit(self):
        """Action handler for parsing text box input to pass into git commit -m."""
        message = self.commit_input.text().strip()
        if not message:
            return
        print(f"Executing: git commit -m '{message}'")
        self.commit_input.clear()
        self.refresh_git_status()

    # TODO: Implement git in backend logic
    def refresh_git_status(self):
        """
        Stub loader where the backend logic queries git status
        and updates the section sub-layouts with GitFileRow items.
        """
        pass


class GitSectionHeader(QWidget):
    """Collapsible/Interactive styled header row for tracking state buckets."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            color: #969696;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 0.5px;
        """)

        self.badge_label = QLabel("0")
        self.badge_label.setStyleSheet("color: #969696; font-size: 11px;")

        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.badge_label)


class GitFileRow(QWidget):
    """
    Component layout skeleton representing a file row inside a staging bucket.
    Contains filepath strings on the left, action buttons on hover, and git codes (A, M, D) on the right.
    """

    def __init__(self, file_path, git_status_code, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        self.path_label = QLabel(file_path)
        self.path_label.setStyleSheet("color: #cccccc; font-size: 12px;")

        self.status_label = QLabel(git_status_code)

        color_map = {"M": "#e2c08d", "A": "#73c991", "D": "#f14c4c", "U": "#4ec9b0"}
        status_color = color_map.get(git_status_code, "#cccccc")
        self.status_label.setStyleSheet(
            f"color: {status_color}; font-weight: bold; font-size: 12px;"
        )

        layout.addWidget(self.path_label)
        layout.addStretch()
        layout.addWidget(self.status_label)

        self.setStyleSheet("""
            GitFileRow:hover { background-color: #2a2d2e; }
            QLabel { background-color: transparent; }
        """)
