from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from editor.utils.titleBar import DreamStudioTitleBar


class DreamStudio(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DreamStudio")
        self.resize(1000, 600)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self.setStyleSheet("background-color: #004488; font-family:inter, Arial;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = DreamStudioTitleBar(self)
        main_layout.addWidget(self.title_bar)

        self.workspace = QWidget()
        self.workspace.setStyleSheet("background-color: #1E1F22;")

        workspace_layout = QVBoxLayout(self.workspace)
        placeholder_label = QLabel("Main Workspace")
        placeholder_label.setStyleSheet("color: #777777; font-size: 24px;")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        workspace_layout.addWidget(placeholder_label)

        main_layout.addWidget(self.workspace)
