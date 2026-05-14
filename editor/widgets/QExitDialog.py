from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt


class ExitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedWidth(300)

        # 1. Update the StyleSheet with the #exitButton selector
        self.setStyleSheet("""
            QDialog {
                background-color: #2B2B2B;
                border: 1px solid #444444; /* Added a subtle border for frameless look */
            }
            QLabel {
                color: #BBBBBB;
                font-size: 14px;
                background-color: transparent;
                padding: 10px 5px;
            }
            QPushButton {
                color: #BBBBBB;
                background-color: transparent;
                border: none;
                border-radius: 2px;
                padding: 8px 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
                color: white;
            }
            
            QPushButton#exitButton {
                color: #FF5555; /* Red Text */
            }
            QPushButton#exitButton:hover {
                background-color: #CC0000; /* Solid Red background on hover */
                color: white;
            }
            QPushButton#exitButton:pressed {
                background-color: #990000;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)

        self.label = QLabel("Confirm Exiting?")
        layout.addWidget(self.label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.yes_button = QPushButton("EXIT DREAMSTUDIO")
        # 3. Assign the object name to match the CSS selector
        self.yes_button.setObjectName("exitButton")

        self.no_button = QPushButton("CANCEL")

        self.yes_button.clicked.connect(self.accept)
        self.no_button.clicked.connect(self.reject)

        button_layout.addWidget(self.yes_button)
        button_layout.addWidget(self.no_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)
