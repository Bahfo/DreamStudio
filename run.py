import sys

from PyQt6.QtWidgets import QApplication
from editor.ui_build import DreamStudio


# Running here if to fast-test application widgets,
# Otherwise running from welcome.py
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DreamStudio")
    window = DreamStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
