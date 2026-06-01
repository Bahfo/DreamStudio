import pyqtgraph as PyGr
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QMainWindow, QApplication, QSpacerItem, QSizePolicy)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize, Qt


class PlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setStyleSheet("background:#1E1E1E;")

        self.central_frame = QHBoxLayout(self)
        self.central_frame.setContentsMargins(5, 5, 5, 5) 
        self.central_frame.setSpacing(5) 

        self.options_menu = QVBoxLayout()
        self.options_menu.setAlignment(Qt.AlignmentFlag.AlignTop) 

        self.zoom_to_fit = self.create_btn("assets/menus/open.png")
        self.zoom_in_out = self.create_btn("assets/menus/find.png")
        self.preferences = self.create_btn("assets/menus/settings.png")
        self.save_graph = self.create_btn("assets/menus/save.png")

        # Add buttons to menu
        self.options_menu.addWidget(self.zoom_to_fit)
        self.options_menu.addSpacing(4)
        self.options_menu.addWidget(self.zoom_in_out)
        self.options_menu.addSpacing(4)
        self.options_menu.addWidget(self.preferences)
        self.options_menu.addSpacing(4)
        self.options_menu.addWidget(self.save_graph)

        self.options_menu.addStretch()
        self.central_frame.addLayout(self.options_menu)
        
        self._plot_graph = PyGr.PlotWidget()
        self._plot_graph.setBackground("#1E1E1E")
        internal_layout = self._plot_graph.plotItem.layout
        internal_layout.setContentsMargins(15, 15, 15, 15)

        self.central_frame.addWidget(self._plot_graph)

    def create_btn(self, icon_path):
        btn = QPushButton()
        btn.setFixedSize(32, 32)
        btn.setIcon(QIcon(icon_path))
        btn.setIconSize(QSize(24, 24))
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                border-radius: 10px;
                padding-top:4px;
                padding-left:2px;
                padding-right:2px;}
            QPushButton:hover{background-color:#333}
        """)
        return btn


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQtGraph Container")
        self.resize(600, 400)
        self.setStyleSheet("background:#1E1E1E;")

        self.widget = PlotWidget(self)
        self.setCentralWidget(self.widget)

if __name__ == "__main__":
    app = QApplication([])
    main = MainWindow()
    main.show()
    app.exec()