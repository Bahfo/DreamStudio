import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PyQt6.QtWidgets import QApplication, QMainWindow
from editor.utils.node_editor.ui_build import NodeBuilder


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QMainWindow()
    window.setWindowTitle("Node Panel Preview")
    window.resize(900, 650)

    panel = NodeBuilder(parent=window)
    window.setCentralWidget(panel)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
