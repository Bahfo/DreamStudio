from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QPainter, QPixmap, QLinearGradient, QColor, QBrush


class WelcomeAction(QPushButton):
    def __init__(self, text, parent=None, _event=None):
        super().__init__(text, parent)
        self._event = _event

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(200)
        self.setStyleSheet(
            """
            QPushButton {
                text-align: left;
                color: #3794ef;
                background: transparent;
                border: none;
                font-size: 14px;
                padding-left: 10px;
                padding-top: 10px;
            }
            QPushButton:hover {
                text-decoration: underline;
                color: #4daafc;
            }
        """
        )
        if self._event is not None:
            self.clicked.connect(self._event)


class WalkthroughCard(QFrame):
    def __init__(self, title, description, parent=None):
        super().__init__(parent)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

        self.setStyleSheet(
            """
            QFrame {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px;
            }

            QFrame:hover {
                border: 1px solid white;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #cccccc; font-weight: bold; font-size: 13px;")

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #858585; font-size: 12px;")

        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        desc_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


class FastTutorialFrame(QFrame):
    def __init__(self, _parent=None):
        super().__init__(_parent)

        self.background_img = QPixmap("assets/logos/welcome_icon.png").scaled(
            150,
            150,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._parent = _parent

        self.bg_svg = QSvgRenderer("assets/logos/welcome_mountains.svg")

        self.setStyleSheet("background-color: transparent; border: none;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 20)
        main_layout.setSpacing(10)

        title = QLabel("DreamStudio 2026")
        title.setStyleSheet(
            """color: #ffffff; 
            font-size: 42px; 
            font-weight: 300; 
            font-family: montserrat, Arial; 
            padding-left: 120px;"""
        )

        subtitle = QLabel("Get Started with")
        subtitle.setStyleSheet(
            """
            color: #cccccc; 
            font-size: 20px;
            padding-left: 130px;"""
        )

        main_layout.addWidget(subtitle)
        main_layout.addWidget(title)
        main_layout.addSpacing(20)

        start_label = QLabel("Start")
        start_label.setStyleSheet(
            """
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            padding-left: 5px;
            padding-top: 20px;
        """
        )

        main_layout.addWidget(start_label)
        main_layout.addSpacing(6)
        main_layout.addWidget(
            WelcomeAction("New File...", _event=self._parent.ui_build_add_new_editor),
        )
        main_layout.addWidget(
            WelcomeAction("Open File...", _event=self._parent.ui_build_open_file)
        )
        main_layout.addWidget(WelcomeAction("Open Folder..."))
        main_layout.addWidget(WelcomeAction("Clone Git Repository..."))
        main_layout.addSpacing(12)
        main_layout.addStretch()

        main_layout.addStretch()

        footer = QHBoxLayout()
        footer.setSpacing(0)
        footer.setContentsMargins(0, 0, 0, 0)

        startup_check = QCheckBox("Show welcome page on startup")
        startup_check.setChecked(True)
        startup_check.setStyleSheet("color: #cccccc; font-size: 12px;")

        footer.addStretch()
        footer.addWidget(startup_check)
        footer.addStretch()

        main_layout.addLayout(footer)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if not self.background_img.isNull():
            x = 10
            y = 6
            painter.drawPixmap(x, y, self.background_img)
