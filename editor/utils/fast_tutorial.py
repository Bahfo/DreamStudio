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
    def __init__(self, text, parent=None):
        super().__init__(text, parent)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

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
                padding: 8px;
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
    def __init__(self, parent=None):
        super().__init__(parent)

        self.background_img = QPixmap("assets/logos/welcome_icon.png").scaled(
            150,
            150,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

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

        columns = QHBoxLayout()
        columns.setSpacing(40)
        columns.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        left.setSpacing(4)
        left.setContentsMargins(0, 0, 0, 0)

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

        left.addWidget(start_label)
        left.addSpacing(6)
        left.addWidget(WelcomeAction("New File..."))
        left.addWidget(WelcomeAction("Open File..."))
        left.addWidget(WelcomeAction("Open Folder..."))
        left.addWidget(WelcomeAction("Clone Git Repository..."))
        left.addSpacing(12)
        left.addStretch()

        columns.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(8)
        right.setContentsMargins(0, 0, 0, 0)

        walk_label = QLabel("Learn The Fundamentals")
        walk_label.setStyleSheet(
            """
            color: #ffffff;
            font-size: 18px; 
            font-weight: bold;"""
        )

        right.addWidget(walk_label)
        right.addSpacing(6)

        right.addWidget(
            WalkthroughCard(
                "Start with a Simple Tutorial",
                "Learn the basics, how to set up projects, and start coding.",
            )
        )
        right.addWidget(
            WalkthroughCard(
                "Explore the Full Capabilities of DreamStudio",
                "See how professionals utilize DreamStudio up to the maximum point.",
            )
        )
        right.addWidget(
            WalkthroughCard(
                "Contact Us",
                "See next updates cycle, chat with the devs, contribute to the project, and more.",
            )
        )
        right.addStretch()

        columns.addLayout(right)
        main_layout.addLayout(columns)

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

        gradient = QLinearGradient(
            0, self.height() / 2, self.width() / 3, self.height() / 3
        )

        gradient.setColorAt(0.0, QColor(81, 43, 214, 180))
        gradient.setColorAt(1.0, QColor(30, 30, 30, 100))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())

        rect = self.rect()
        target_rect = QRectF(
            -5, self.height() * 0.3, rect.width() + 5, rect.height() * 0.7
        )

        if self.bg_svg.isValid():
            self.bg_svg.render(painter, target_rect)

        if not self.background_img.isNull():
            x = 10
            y = 6
            painter.drawPixmap(x, y, self.background_img)
