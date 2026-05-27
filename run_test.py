# Script to run applicaion directly without startup welcome and configs

import sys

from PyQt6.QtWidgets import QApplication
from editor.ui_build import DreamStudio

# Running here if to fast-test application widgets,
# Otherwise running from welcome.py
TOOLTIP_STYLE = """
QToolTip {
    background-color: #252526;
    color: #CCCCCC;
    border: 1px solid #3C3C3C;
    padding: 4px 8px;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DreamStudio")
    app.setStyleSheet(TOOLTIP_STYLE)
    window = DreamStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
