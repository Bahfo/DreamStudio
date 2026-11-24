from editor import *
from assets.fonts.font_strapper import Fonts
from editor.base.user.gradient import GradientBanner


class IDEStartPage(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(1024, 750)

        self.setContentsMargins(0, 0, 0, 0)
        self._layout = QVBoxLayout(self)
