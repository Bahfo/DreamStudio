"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.
Standalone preview for the Nodes Designer canvas.
"""

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication, QMainWindow

from editor.utils.node_editor.ui_build import NodeBuilder


def main() -> None:
    os.chdir(_PROJECT_ROOT)

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
