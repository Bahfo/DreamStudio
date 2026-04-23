from PyQt6.QtWidgets import QApplication, QSplitter, QTextEdit, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt


class SmoothSplitterDemo(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 1. Initialize Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 2. Add widgets
        splitter.addWidget(QTextEdit("Left Pane"))
        splitter.addWidget(QTextEdit("Right Pane"))

        # 3. Ensure smooth (opaque) resizing is on
        splitter.setOpaqueResize(True)

        # 4. Set stretch factors so they resize proportionally (1:1)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # 5. Optional: Set initial distribution
        splitter.setSizes([300, 300])

        layout.addWidget(splitter)
        self.resize(700, 400)


app = QApplication([])
demo = SmoothSplitterDemo()
demo.show()
app.exec()
