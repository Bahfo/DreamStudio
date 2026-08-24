from editor import *

class Separator(QFrame):
    """
    A separator between objects.

    Parameters:
        - `_width`: sets separator width.
        - `_height`: sets separator height.
    """

    def __init__(self, _width, _height):
        super().__init__()
        self.setFixedWidth(_width)
        self.setFixedHeight(_height)
        self.setObjectName("Separator")
