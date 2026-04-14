from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from editor.utils.titleBar import DreamStudioTitleBar
from editor.utils.statusBar import StatusBar
from editor.utils.optionsBar import OptionsMenu


class DreamStudio(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DreamStudio")
        self.resize(1000, 800)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self.setStyleSheet("background-color: #004488; font-family:inter, Arial;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title Bar
        self.title_bar = DreamStudioTitleBar(self)
        main_layout.addWidget(self.title_bar)

        # Options Menu
        self.options_menu = OptionsMenu(self)
        main_layout.addWidget(self.options_menu)

        self.workspace = QWidget()
        self.workspace.setStyleSheet("background-color: #1E1F22;")

        workspace_layout = QHBoxLayout(self.workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        main_layout.addWidget(self.workspace)

        # Status Bar
        self.status_bar = StatusBar(self)
        main_layout.addWidget(self.status_bar)
