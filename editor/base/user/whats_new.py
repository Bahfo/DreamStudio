from editor import *

from fonts.font_strapper import Fonts

# Local Imports
from editor.base.user.gradient import GradientBanner


class IDEStartPage(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(1024, 750)
