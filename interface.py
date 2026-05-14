"""
(C) COPYRIGHT - 2026 Excellent Technologies Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by Excellent Technologies Co.

DreamStudio is an Integrated Development Environment Developed Mainly for C++,
and Python.

The main purpose of DreamStudio is mainly to maintain and develop Excellent
Technologies Applications and Software. It is mainly established as a software
to complete the BlueSea Operating System EcoSystem.

DreamStudio is a software written by its original author Bahaa Nofal. His idea is
to establish a personal EcoSystem for usage separated from tracking and stay in
a comfort zone for daily users.
"""

# Written by Bahaa Nofal 2-2026

import os, sys
from PyQt6.QtWidgets import (
    QStackedWidget,
    QApplication,
    QGridLayout,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QFrame,
    QLabel,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

### Local Imports
from editor.widgets.QTitleBar import TitleBar
from editor.widgets.QExitDialog import ExitDialog
from editor.widgets.QActivityButton import ActivityButton


class WelcomeInterface(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(1000, 700)
        self.setWindowTitle("Welcome to DreamStudio")
        self.setStyleSheet("background-color: #1E1E1E; font-family: inter, Arial;")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.center_on_screen()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.setup_layout()

    def setup_layout(self):
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title Bar
        self.title_bar = self.title_bar = TitleBar(self, "   Welcome to DreamStudio")
        main_layout.addWidget(self.title_bar)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        self.body_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addLayout(self.body_layout, stretch=1)

        self.leftmost_bar = QFrame()
        self.leftmost_bar.setFixedWidth(300)
        self.leftmost_bar.setStyleSheet("""background: #1B1B1B;""")

        #### The Three Main Layouts
        self.stacked_layout = QStackedWidget()

        # layouts
        self.welcome_layout = WelcomeFrame()
        self.new_proj_layout = QWidget()
        self.marketplace_layout = QWidget()
        self.news_and_articles = NewsAndArticles()

        #### Leftmost Layout

        self.leftmost_layout = QVBoxLayout(self.leftmost_bar)
        self.leftmost_layout.setContentsMargins(10, 15, 10, 5)
        self.leftmost_layout.setSpacing(10)
        self.leftmost_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        new_project_btn = QPushButton("New Project")
        new_project_btn.setFixedSize(280, 40)
        new_project_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_project_btn.setStyleSheet("""
            QPushButton{
            color: white;
            background-color: transparent;
            border: none;
            text-align: left;
            border-radius: 4px;
            padding-left: 15px;
            font-size: 14px;}
            QPushButton:hover{
            background-color:#444;}
            
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }""")
        self.leftmost_layout.addWidget(new_project_btn)

        marketplace_btn = QPushButton("MarketPlace")
        marketplace_btn.setFixedSize(280, 40)
        marketplace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        marketplace_btn.setStyleSheet("""
            QPushButton{
            color: white;
            background-color: transparent;
            padding-left: 15px;
            border: none;
            border-radius: 4px;
            text-align: left;
            font-size: 14px;}
            QPushButton:hover{
            background-color:#444;}
            
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }""")
        self.leftmost_layout.addWidget(marketplace_btn)

        community_btn = QPushButton("Community")
        community_btn.setFixedSize(280, 40)
        community_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        community_btn.setStyleSheet("""
            QPushButton{
            color: white;
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding-left: 15px;
            text-align: left;
            font-size: 14px;}
            QPushButton:hover{
            background-color:#444;}
            
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }""")
        self.leftmost_layout.addWidget(community_btn)

        #### `New Project` Layout
        self.new_proj_v_layout = QVBoxLayout()
        self.new_proj_v_layout.setContentsMargins(20, 20, 20, 20)
        self.new_proj_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Section 1: Desktop Projects ---
        self.desktop_label = QLabel("Desktop Projects:")
        self.desktop_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;"
        )
        self.new_proj_v_layout.addWidget(self.desktop_label)

        self.desktop_grid = QGridLayout()
        self.desktop_grid.setSpacing(15)
        self.desktop_grid.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_cpp = ActivityButton(
            "assets/activities/desktop_activity_2.svg", "Desktop Project with C++"
        )
        self.desktop_grid.addWidget(self.btn_cpp, 0, 0)

        self.btn_python = ActivityButton(
            "assets/activities/desktop_activity_1.svg", "Desktop Project with Python"
        )
        self.desktop_grid.addWidget(self.btn_python, 0, 1)

        self.new_proj_v_layout.addLayout(self.desktop_grid)

        # --- Spacer between sections ---
        self.new_proj_v_layout.addSpacing(30)

        # --- Section 2: Console Projects ---
        self.console_label = QLabel("Console Projects:")
        self.console_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;"
        )
        self.new_proj_v_layout.addWidget(self.console_label)

        self.console_grid = QGridLayout()
        self.console_grid.setSpacing(15)
        self.console_grid.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_con1 = ActivityButton(
            "assets/activities/console_activity_1.svg", "EXConsole Activity with C++"
        )
        self.console_grid.addWidget(self.btn_con1, 0, 0)

        self.btn_con2 = ActivityButton(
            "assets/activities/console_activity_2.svg", "EXConsole Activity with Python"
        )
        self.console_grid.addWidget(self.btn_con2, 0, 1)

        self.new_proj_v_layout.addLayout(self.console_grid)

        self.new_proj_layout.setLayout(self.new_proj_v_layout)
        self.stacked_layout.addWidget(self.welcome_layout)
        self.stacked_layout.addWidget(self.new_proj_layout)
        self.stacked_layout.addWidget(self.news_and_articles)

        self.body_layout.addWidget(self.leftmost_bar)
        self.body_layout.addWidget(self.stacked_layout)

        ### Actions
        new_project_btn.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(1))
        community_btn.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(2))

    def center_on_screen(self):
        """Calculates the screen center and moves the window there."""
        screen_geometry = self.screen().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()

        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def mousePressEvent(self, event):
        win = self.window()
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - win.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        win = self.window()
        if self.offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if win.isMaximized():
                cursor_x = event.globalPosition().toPoint().x()
                max_width = win.width()
                width_ratio = cursor_x / max_width

                win.showNormal()
                normal_width = win.width()
                new_x = int(cursor_x - (normal_width * width_ratio))
                new_y = event.globalPosition().toPoint().y() - self.offset.y()

                win.move(new_x, new_y)

                self.offset = event.globalPosition().toPoint() - win.pos()
                return

            win.move(event.globalPosition().toPoint() - self.offset)
            event.accept()

    def closeEvent(self, event):
        dialog = ExitDialog(self)
        # .exec() returns QDialog.DialogCode.Accepted (1) or Rejected (0)
        if dialog.exec():
            event.accept()
        else:
            event.ignore()


class WelcomeFrame(QFrame):
    """A Welcome Frame once initializing DreamStudio"""

    def __init__(self, _parent=None):
        super().__init__(_parent)
        self._parent = _parent

        self.setStyleSheet("background-color: transparent; border: none;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 20)
        main_layout.setSpacing(10)

        title = QLabel("DreamStudio 2026")
        title.setStyleSheet("""color: #ffffff; 
            font-size: 42px; 
            font-weight: 300; 
            font-family: montserrat, Arial; """)

        subtitle = QLabel("Welcome to")
        subtitle.setStyleSheet("""
            color: #cccccc; 
            font-size: 20px;
            padding-left: 0px;""")

        main_layout.addWidget(subtitle)
        main_layout.addWidget(title)
        main_layout.addSpacing(20)

        start_label = QLabel(
            "Start building by selecting `New Project` Tab, or view the marketplace for extensions."
        )
        start_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            padding-top: 10px;
        """)

        main_layout.addWidget(start_label)
        main_layout.addSpacing(6)
        main_layout.addStretch()

        footer = QHBoxLayout()
        footer.setSpacing(0)
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addStretch()

        main_layout.addLayout(footer)


class NewsAndArticles(QFrame):
    def __init__(self):
        super().__init__()
        self.resize(1000, 700)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        self.view = QWebEngineView()
        self.view.setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: #1e1e2e;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }

            QScrollBar::handle:vertical {
                background: #45475a;
                min-height: 30px;
                border-radius: 5px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }

            QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }

            QScrollBar::add-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
        """)

        file_path = os.path.abspath(
            "/home/bahaa/Desktop/apps/DreamJetPack/internet/techNews/news.html"
        )
        self.view.setUrl(QUrl.fromLocalFile(file_path))

        self.view.loadFinished.connect(self.inject_data_and_ui)
        main_layout.addWidget(self.view)

    def inject_data_and_ui(self):
        json_path = "/home/bahaa/Desktop/apps/DreamJetPack/internet/techNews/news.json"
        with open(json_path, "r") as f:
            news_json = f.read()

        self.view.page().runJavaScript(f"window.INJECTED_NEWS = {news_json};")
        js_path = "/home/bahaa/Desktop/apps/DreamJetPack/internet/techNews/news.js"
        with open(js_path, "r") as f:
            app_js = f.read()

        self.view.page().runJavaScript(app_js)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DreamStudio")
    window = WelcomeInterface()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
