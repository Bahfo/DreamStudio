import os, sys, logging

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
    QLineEdit,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap

from editor.widgets.QTitleBar import TitleBar
from editor.widgets.QExitDialog import ExitDialog

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_DIR = os.path.join(BASE_DIR, "project_manifests")

PROJECT_ICON_MAP = {
    "empty_python_project": "dreamStudio_icon.png",
    "tensorflow_ml_project": "tensorflow.png",
    "pytorch_ml_project": "pytorch.png",
    "fastapi_api_project": "fastapi.svg",
    "pyqt6_ui_project": "qt.png",
    "flask_server_project": "flask.png",
    "kivy_mobile_project": "beeware.png",
}

ICON_DIR = os.path.join(BASE_DIR, "icon_src")


PYTHON_PROJECT_TYPES = [
    {
        "type": "empty_python_project",
        "name": "Empty Python Project",
        "desc": "A bare, structured Python baseline",
        "manifest": os.path.join(MANIFEST_DIR, "empty_python_project.yaml"),
    },
    {
        "type": "tensorflow_ml_project",
        "name": "TensorFlow ML",
        "desc": "Deep learning infrastructure with TensorFlow",
        "manifest": os.path.join(MANIFEST_DIR, "machine_learning_tensorflow.yaml"),
    },
    {
        "type": "pytorch_ml_project",
        "name": "PyTorch ML",
        "desc": "Deep learning with the PyTorch ecosystem",
        "manifest": os.path.join(MANIFEST_DIR, "machine_learning_pytorch.yaml"),
    },
    {
        "type": "fastapi_api_project",
        "name": "FastAPI Web API",
        "desc": "Async backend engine powered by FastAPI",
        "manifest": os.path.join(MANIFEST_DIR, "fast_api_python.yaml"),
    },
    {
        "type": "pyqt6_ui_project",
        "name": "PyQt6 Desktop UI",
        "desc": "Desktop application boilerplate with PyQt6",
        "manifest": os.path.join(MANIFEST_DIR, "user_interface_pyqt.yaml"),
    },
    {
        "type": "flask_server_project",
        "name": "Flask Server",
        "desc": "Server project powered by the Flask framework",
        "manifest": os.path.join(MANIFEST_DIR, "server_flask.yaml"),
    },
    {
        "type": "kivy_mobile_project",
        "name": "Kivy Mobile App",
        "desc": "Cross-platform mobile application with Kivy",
        "manifest": os.path.join(MANIFEST_DIR, "mobile_application_kivy.yaml"),
    },
]


class ProjectCard(QPushButton):
    def __init__(self, project_info, parent=None):
        super().__init__(parent)
        self._info = project_info
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(210, 160)
        self.setFlat(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        self.setLayout(layout)

        icon_filename = PROJECT_ICON_MAP.get(project_info["type"], "dreamStudio_icon.png")
        icon_path = os.path.join(ICON_DIR, icon_filename)
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            pixmap = QPixmap(os.path.join(ICON_DIR, "dreamStudio_icon.png"))
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedHeight(80)
        scaled = pixmap.scaled(76, 76, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        icon_label.setPixmap(scaled)
        icon_label.setStyleSheet("background: transparent;")

        name_label = QLabel(project_info["name"])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("""
            color: #A9B7C6;
            font-size: 12px;
            font-weight: bold;
            background: transparent;
            padding: 2px 4px;
        """)

        desc_label = QLabel(project_info["desc"])
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            color: #8A8A8A;
            font-size: 10px;
            background: transparent;
            padding: 0px 4px;
        """)

        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        layout.addWidget(desc_label)

        self.setStyleSheet("""
            ProjectCard, ProjectCard:focus, ProjectCard:pressed, ProjectCard:checked {
                background: transparent;
                border: 1px solid #3C3C3C;
                border-radius: 8px;
            }
            ProjectCard:hover {
                border: 1px solid #4A6FA5;
                background: rgba(74, 111, 165, 0.08);
            }
            ProjectCard:checked {
                border: 1px solid #4A6FA5;
                background: rgba(74, 111, 165, 0.15);
            }
        """)

    @property
    def project_info(self):
        return self._info


class ProjectDetailsPage(QWidget):
    def __init__(self, project_info, parent=None):
        super().__init__(parent)
        self._info = project_info

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        back_layout = QHBoxLayout()
        self.back_btn = QPushButton("  Back")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setFixedSize(100, 32)
        self.back_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background: transparent;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                font-size: 13px;
                text-align: left;
                padding-left: 8px;
            }
            QPushButton:hover { background: #333; }
        """)
        back_layout.addWidget(self.back_btn)
        back_layout.addStretch()
        layout.addLayout(back_layout)

        header = QLabel(f"Create New: {project_info['name']}")
        header.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: 300;")
        layout.addWidget(header)

        desc = QLabel(project_info["desc"])
        desc.setStyleSheet("color: #8A8A8A; font-size: 13px;")
        layout.addWidget(desc)

        layout.addSpacing(16)

        name_label = QLabel("Project Name")
        name_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("my_project_name")
        self.name_input.setFixedHeight(36)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: #25272B;
                color: white;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #4A6FA5; }
        """)
        layout.addWidget(self.name_input)

        location_label = QLabel("Project Location")
        location_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        layout.addWidget(location_label)

        loc_row = QHBoxLayout()
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText(os.path.expanduser("~/DreamStudioProjects"))
        self.location_input.setFixedHeight(36)
        self.location_input.setStyleSheet("""
            QLineEdit {
                background: #25272B;
                color: white;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #4A6FA5; }
        """)
        loc_row.addWidget(self.location_input)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setFixedSize(90, 36)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background: #2D2D2D;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background: #3D3D3D; }
        """)
        loc_row.addWidget(self.browse_btn)
        layout.addLayout(loc_row)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.create_btn = QPushButton("Create Project")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_btn.setFixedSize(160, 40)
        self.create_btn.setEnabled(False)
        self.create_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background: #4A6FA5;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #3A5F95; }
            QPushButton:disabled { background: #3C3C3C; color: #666; }
        """)
        btn_row.addWidget(self.create_btn)
        layout.addLayout(btn_row)

        self.name_input.textChanged.connect(self._validate)
        self.location_input.textChanged.connect(self._validate)
        self.browse_btn.clicked.connect(self._browse_location)

    def _validate(self):
        valid = bool(self.name_input.text().strip()) and bool(self.location_input.text().strip())
        self.create_btn.setEnabled(valid)

    def _browse_location(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Location")
        if path:
            self.location_input.setText(path)

    @property
    def project_info(self):
        return self._info

    def collect_input(self):
        return {
            "name": self.name_input.text().strip(),
            "location": self.location_input.text().strip(),
        }


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

        self._details_pages = []
        self._transitioning = False
        self.setup_layout()

    def setup_layout(self):
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = TitleBar(self, "   Welcome to DreamStudio")
        main_layout.addWidget(self.title_bar)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        self.body_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addLayout(self.body_layout, stretch=1)

        self.leftmost_bar = QFrame()
        self.leftmost_bar.setFixedWidth(300)
        self.leftmost_bar.setStyleSheet("background: #1B1B1B;")

        self.stacked_layout = QStackedWidget()

        self.welcome_layout = WelcomeFrame()
        self.new_proj_layout = QWidget()

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
            QPushButton:hover{background-color: rgba(255, 255, 255, 0.1);}""")
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
            QPushButton:hover{background-color: rgba(255, 255, 255, 0.1);}""")
        self.leftmost_layout.addWidget(marketplace_btn)

        self._build_new_project_page()
        self._build_details_pages()

        self.stacked_layout.addWidget(self.welcome_layout)
        self.stacked_layout.addWidget(self.new_proj_layout)
        for page in self._details_pages:
            self.stacked_layout.addWidget(page)

        self.body_layout.addWidget(self.leftmost_bar)
        self.body_layout.addWidget(self.stacked_layout)

        new_project_btn.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(1))

    def _build_new_project_page(self):
        self.new_proj_v_layout = QVBoxLayout()
        self.new_proj_v_layout.setContentsMargins(20, 20, 20, 20)
        self.new_proj_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        python_label = QLabel("Python Projects:")
        python_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;"
        )
        self.new_proj_v_layout.addWidget(python_label)

        python_grid = QGridLayout()
        python_grid.setSpacing(15)
        python_grid.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._project_cards = []
        for i, info in enumerate(PYTHON_PROJECT_TYPES):
            card = ProjectCard(info)
            card.clicked.connect(lambda checked, idx=i: self._on_project_card_clicked(idx))
            self._project_cards.append(card)
            row, col = divmod(i, 3)
            python_grid.addWidget(card, row, col)

        self.new_proj_v_layout.addLayout(python_grid)
        self.new_proj_v_layout.addSpacing(30)
        self.new_proj_v_layout.addStretch()

        self.new_proj_layout.setLayout(self.new_proj_v_layout)

    def _build_details_pages(self):
        for info in PYTHON_PROJECT_TYPES:
            page = ProjectDetailsPage(info)
            page.back_btn.clicked.connect(self._on_back_to_projects)
            page.create_btn.clicked.connect(lambda checked, pi=info: self._on_create_project(pi))
            self._details_pages.append(page)

    def _on_back_to_projects(self):
        self.stacked_layout.setCurrentIndex(1)
        for card in self._project_cards:
            card.setChecked(False)

    def _on_project_card_clicked(self, index):
        details_index = 2 + index
        if 0 <= details_index < self.stacked_layout.count():
            self.stacked_layout.setCurrentIndex(details_index)

    def _on_create_project(self, project_info):
        page = self._details_pages[PYTHON_PROJECT_TYPES.index(project_info)]
        input_data = page.collect_input()
        name = input_data["name"]
        location = input_data["location"]

        project_path = os.path.join(location, name)
        if os.path.exists(project_path):
            QMessageBox.warning(self, "Conflict", f"Path already exists:\n{project_path}")
            return

        manifest_path = project_info["manifest"]
        if not os.path.isfile(manifest_path):
            QMessageBox.critical(self, "Error", f"Manifest not found:\n{manifest_path}")
            return

        self._launch_ide(manifest_path, project_path, project_info["type"])

    def _launch_ide(self, manifest_path, project_path, project_type):
        from editor.ui_build import DreamStudio

        os.makedirs(project_path, exist_ok=True)

        self._transitioning = True
        self.ide_window = DreamStudio()
        self.ide_window.show()
        self.ide_window.title_bar.toggle_maximize()
        self.close()

        QApplication.processEvents()

        self.ide_window.bootstrap_project(manifest_path, project_path, project_type)

    def center_on_screen(self):
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
        if self._transitioning:
            event.accept()
            return
        dialog = ExitDialog(self)
        if dialog.exec():
            event.accept()
        else:
            event.ignore()


class WelcomeFrame(QFrame):
    def __init__(self, _parent=None):
        super().__init__(_parent)
        self._parent = _parent
        self.setStyleSheet("background-color: transparent; border: none;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 20)
        main_layout.setSpacing(10)

        title = QLabel("DreamStudio 2026")
        title.setStyleSheet("""
            color: #ffffff;
            font-size: 42px;
            font-weight: 300;
            font-family: montserrat, Arial;
        """)

        subtitle = QLabel("Welcome to")
        subtitle.setStyleSheet("""
            color: #cccccc;
            font-size: 20px;
            padding-left: 0px;
        """)

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


TOOLTIP_STYLE = """
QToolTip {
    background-color: #25272B;
    color: #FFFFFF;
    border: none;
    padding: 6px 5px;
    font-family: inter;
    font-size: 12px;
}
"""


def main():
    from editor.init import initialize

    app = QApplication(sys.argv)
    app.setApplicationName("DreamStudio")
    app.setStyleSheet(TOOLTIP_STYLE)
    window = WelcomeInterface()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
