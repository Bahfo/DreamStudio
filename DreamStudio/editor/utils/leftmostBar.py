from PyQt6.QtWidgets import (
    QFrame,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QWidget,
)
from PyQt6.QtCore import Qt, QSize


class LeftMostBar(QFrame):
    def __init__(self, master, side_panel):
        super().__init__(master)
        self.side_panel = side_panel
        self.setFixedWidth(50)
        self.setStyleSheet("background-color: #25272B; border: none;")

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.explorerBtn = self.create_nav_button("assets/explorer.png", 0)
        self.searchBtn = self.create_nav_button("assets/search.png", 1)

    def create_nav_button(self, icon_path, index):
        btn = QPushButton()
        btn.setFixedSize(40, 40)
        btn.clicked.connect(lambda: self.toggle_panel(index))
        self.layout.addWidget(btn)
        return btn

    def toggle_panel(self, index):
        if self.side_panel.isVisible() and self.side_panel.currentIndex() == index:
            self.side_panel.hide()
        else:
            self.side_panel.setCurrentIndex(index)
            self.side_panel.show()


class SidePanel(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(250)
        self.setStyleSheet(
            "background-color: #1E1F22; border-right: 1px solid #323232;"
        )

        self.addWidget(QLabel("Project Explorer TreeView Here"))
        self.addWidget(QLabel("Global Search Results Here"))

        self.hide()
