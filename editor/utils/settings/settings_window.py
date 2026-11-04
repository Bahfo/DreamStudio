"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Main Settings Window for DreamStudio - Converts Settings to JSON.
"""

from editor import *


class SettingsWindow(QWidget):
    """
    Main Settings Window
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setContentsMargins(0, 0, 0, 0)
        self._layout = QVBoxLayout(self)
