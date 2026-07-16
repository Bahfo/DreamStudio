from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *


class MenuBar(QMenu):
    def __init__(self, _parent=None):
        super().__init__(parent=_parent)
        self._parent = _parent
        self.setObjectName("MenuBar")

        