from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt


class ActivityButton(QPushButton):
    def __init__(self, svg_path, title, parent=None):
        super().__init__(parent)

        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(210, 160)
        self.setFlat(True)

        # Force the base widget to be fully transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)
        self.setLayout(main_layout)

        # Container
        self.container = QWidget()
        self.container.setObjectName("activityContainer")
        self.container.setFixedSize(200, 100)

        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.container.setLayout(container_layout)

        self.svg = QSvgWidget(svg_path)
        self.svg.setFixedSize(180, 90)
        container_layout.addWidget(self.svg)

        # Label
        self.label = QLabel(title)
        self.label.setObjectName("activityLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)

        # IMPORTANT: fully detach from palette rendering
        self.label.setAutoFillBackground(False)
        self.label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Assemble
        main_layout.addWidget(self.container, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.label)

        # Styling
        self.setStyleSheet("""
            ActivityButton, ActivityButton:focus, ActivityButton:pressed, ActivityButton:checked {
                background: transparent;
                border: none;
                outline: none; 
            }

            #activityContainer {
                background: transparent;
                border: none;
            }

            #activityLabel {
                background: transparent;
                color: #A9B7C6;
                font-size: 12px;
                padding: 4px 8px;
                border-radius: 6px;
            }

            ActivityButton:hover #activityLabel {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
            }

            ActivityButton:checked #activityLabel {
                background-color: transparent;
                color: white;
            }
        """)
