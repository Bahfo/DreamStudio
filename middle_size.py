import sys
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QPushButton,
    QStackedWidget,
)


class MobileUIStructure(QWidget):
    def __init__(self):
        super().__init__()
        self._drag_position = QPoint()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 750)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.setStyleSheet(
            """
            #PhoneChassis {
                background-color: #0B0B0C;
                border: 3px solid #2E3033;
                border-radius: 38px;
            }
            #ScreenMatrix {
                background-color: #121212;
                border-radius: 26px;
            }
            #OptionsDock {
                background-color: #1E1E1F;
                border: 1px solid #2D2D30;
                border-radius: 20px;
            }
            QPushButton {
                background-color: transparent;
                color: #A0A0A0;
                border: none;
                border-radius: 15px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #2D2D30;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #007ACC;
                color: #FFFFFF;
            }
            QToolTip {
                background-color: #2D2D30;
                color: #F1F1F1;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 5px 8px;
                font-family: 'inter', sans-serif;
                font-size: 11px;
            }
        """
        )

        self.phone_chassis = QFrame()
        self.phone_chassis.setObjectName("PhoneChassis")
        self.phone_chassis.setFixedSize(320, 700)

        chassis_layout = QVBoxLayout(self.phone_chassis)
        chassis_layout.setContentsMargins(8, 12, 8, 12)
        chassis_layout.setSpacing(0)

        self.camera_lens = QFrame()
        self.camera_lens.setFixedSize(10, 10)
        self.camera_lens.setStyleSheet(
            """
            background-color: #1C1C1E;
            border: 2px solid #0B0B0C;
            border-radius: 5px;
        """
        )
        chassis_layout.addWidget(
            self.camera_lens, alignment=Qt.AlignmentFlag.AlignCenter
        )
        chassis_layout.addSpacing(10)

        self.screen_matrix = QStackedWidget()
        self.screen_matrix.setObjectName("ScreenMatrix")
        chassis_layout.addWidget(self.screen_matrix, stretch=1)

        main_layout.addWidget(self.phone_chassis)

        self.options_dock = QFrame()
        self.options_dock.setObjectName("OptionsDock")
        self.options_dock.setFixedWidth(40)

        dock_layout = QVBoxLayout(self.options_dock)
        dock_layout.setContentsMargins(4, 8, 4, 8)
        dock_layout.setSpacing(8)
        dock_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        menu_items = [
            ("⏻", "Power on/off"),
            ("🔊", "Volume Up"),
            ("🔉", "Volume Down"),
            ("◁", "Return"),
            ("○", "Home"),
            ("▢", "Activities"),
        ]

        for icon, tooltip in menu_items:
            btn = QPushButton(icon)
            btn.setFixedSize(30, 30)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            btn.clicked.connect(
                lambda checked, t=tooltip: print(f"[{t}] button clicked.")
            )
            dock_layout.addWidget(btn)

        main_layout.addWidget(self.options_dock)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui_preview = MobileUIStructure()
    ui_preview.show()
    sys.exit(app.exec())
