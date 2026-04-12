import sys

from PyQt6.QtWidgets import QApplication
from editor.ui_build import DreamStudio


def main():
    app = QApplication(sys.argv)
    window = DreamStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
