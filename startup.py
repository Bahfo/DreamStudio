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
# Frozen (PyInstaller) compatibility: sys._MEIPASS is the bundle dir when frozen.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _PROJECT_ROOT = sys._MEIPASS  # type: ignore[attr-defined]
else:
    _PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main() -> None:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtWidgets import QApplication

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName("DreamStudio")
    app.setStyle("Fusion")

    from editor.utils.resource_path import resource_path
    from PyQt6.QtGui import QIcon

    app.setWindowIcon(QIcon(resource_path("assets/dreamStudio_icon.png")))

    from bootstrap.splash import SplashController
    from bootstrap.manager import BootstrapManager

    splash = SplashController()
    splash.show()

    bootstrap = BootstrapManager(base_dir=_PROJECT_ROOT)
    result = bootstrap.run(splash=splash)

    if result.success and result.window is not None:
        window = result.window

        def _reveal():
            try:
                if splash.is_visible:
                    splash.close()
            except Exception:
                try:
                    splash.close()
                except Exception:
                    pass
            window.setEnabled(True)
            window.showMaximized()
            try:
                window.ui_ready.emit()
            except Exception:
                pass

        QTimer.singleShot(0, _reveal)
    else:
        try:
            if splash.is_visible:
                splash.close()
        except Exception:
            try:
                splash.close()
            except Exception:
                pass
        if result.success and result.window is None:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(
                None,
                "Startup Error",
                "Main window failed to initialize (registry missing).",
            )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
