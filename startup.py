"""
DreamStudio application entry point.

This is the only file that should be executed to start the IDE.
It delegates all startup orchestration to BootstrapManager.

Usage:
    python startup.py
"""

import os
import sys

# Ensure the project root is on sys.path so bootstrap/ and editor/ are importable.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main() -> None:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("DreamStudio")
    app.setStyle("Fusion")

    from bootstrap.splash import SplashController
    from bootstrap.manager import BootstrapManager

    splash = SplashController()
    splash.show()

    bootstrap = BootstrapManager(base_dir=_PROJECT_ROOT)
    result = bootstrap.run(splash=splash)

    if result.success:
        window = result.window

        def _reveal():
            splash.close()
            window.setEnabled(True)
            window.showMaximized()
            window.show()

        QTimer.singleShot(5000, _reveal)
    else:
        splash.close()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
