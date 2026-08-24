from editor import *

class MenuBar(QMenu):
    def __init__(self, _parent=None):
        super().__init__(parent=_parent)
        self._parent = _parent
        self.setObjectName("MenuBar")

        
