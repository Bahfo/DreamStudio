"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Developed and Maintained Mainly by DreamStudio Maintainers and Contributors, and
Supervised by EXcellent TechStacks Co.

DreamStudio is an Integrated Development Environment Developed Mainly for C++,
and Python.

The main purpose of DreamStudio is mainly to maintain and develop Excellent
Technologies Applications and Software. It is mainly established as a software
to complete the BlueSea Operating System EcoSystem.

DreamStudio is a software written by its original author Bahaa Nofal. His idea is
to establish a personal EcoSystem for usage separated from tracking and stay in
a comfort zone for daily users.
"""

# Written By Bahaa Nofal - 4/2026

import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPixmap, QColor, QLinearGradient, QBrush, QIcon

# Local Import
from run import DreamStudio


class WelcomeWindow(QWidget):
    initialization_complete = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.background_img = QPixmap("assets/logos/welcome_mountains.png")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.resize(750, 450)

        self.center_on_screen()

        layout = QVBoxLayout(self)

        self.info_label = QLabel(
            "DreamStudio",
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )
        self.info_label.setContentsMargins(17, 20, 0, 0)
        self.info_label.setStyleSheet("""
            QLabel {
            font-family: montserrat, Arial;
            font-size: 44px;
            color: #F5F5F5;
            }""")
        layout.addWidget(self.info_label)
        layout.addSpacing(5)

        top_row_layout = QHBoxLayout()
        top_row_layout.setContentsMargins(20, 0, 0, 0)
        top_row_layout.setSpacing(8)

        self.versionName = QLabel("Quiet Valley")
        self.versionName.setStyleSheet(
            "font-family: montserrat; font-size: 20px; color: #F5F5F5"
        )

        self.version_label = QLabel("v1.0.1")
        self.version_label.setStyleSheet(
            "font-family: montserrat; font-size: 15px; color: #F5F5F5;"
        )

        top_row_layout.addWidget(self.versionName)
        top_row_layout.addWidget(self.version_label)
        top_row_layout.addStretch()

        layout.addLayout(top_row_layout)
        layout.addSpacing(270)

        self.copyright = QLabel(
            "© 2026 EXcellent TechStacks - All Rights Reserved",
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )
        self.copyright.setContentsMargins(17, 20, 17, 0)
        self.copyright.setStyleSheet("""
            QLabel {
            font-family: montserrat, Arial;
            font-size: 12px;
            color: #1E1E1E;
            }""")
        layout.addWidget(self.copyright)

        layout.addStretch()

        self.counter = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.simulate_loading)
        self.timer.start(30)

    def center_on_screen(self):
        """Calculates the screen center and moves the window there."""
        screen_geometry = self.screen().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()

        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def simulate_loading(self):
        """Originally a simulator for loading the software.
        It configures software bootloader so it initializes correctly.
        Once finished, it recieves a signal to start the application,
        otherwise, it fails and shows screen message error."""
        self.counter += 1
        if self.counter >= 400:
            self.timer.stop()
            self.initialization_complete.emit()

    def paintEvent(self, event):
        """Painter event for screen's gradient color. NOTE: This is not something
        that is (write and forget) because software welcome image changes from
        update to update."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        painter.fillRect(self.rect(), QColor("#1E1E1E"))

        gradient = QLinearGradient(0, 0, 0, self.height())

        gradient.setColorAt(0.0, QColor("#382162"))  # Deep Indigo/Purple
        gradient.setColorAt(0.2, QColor("#D8446B"))  # Vibrant Rose/Pink
        gradient.setColorAt(1.0, QColor("#FFB347"))  # Soft Orange/Golden

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())

        if not self.background_img.isNull():
            painter.drawPixmap(-1, 50, self.background_img)


class AppController:
    """
    This class orchestrates the flow of the application.
    It decides which window is shown and when.
    """

    def __init__(self):
        self.welcome_window = WelcomeWindow()
        self.main_window = DreamStudio()
        self.welcome_window.initialization_complete.connect(self.transition_to_main)

    def start_app(self):
        """Welcome Screen Initializer"""
        self.welcome_window.show()

    def transition_to_main(self):
        """Main Screen Transition from Welcome Window."""
        self.main_window.show()
        self.main_window.title_bar.toggle_maximize()
        self.welcome_window.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/logos/dreamStudio_icon.png"))

    controller = AppController()
    controller.start_app()

    sys.exit(app.exec())
