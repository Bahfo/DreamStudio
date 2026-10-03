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


def _parse_project_arg(argv: list) -> str | None:
    """Extract a project/solution path from command-line arguments.

    Supports ``--project <path>``, ``--solution <path>`` and ``-p <path>``.
    Returns ``None`` when no path was supplied.
    """
    for index, arg in enumerate(argv):
        if arg in ("--project", "--solution", "-p") and index + 1 < len(argv):
            candidate = argv[index + 1]
            if candidate and not candidate.startswith("-"):
                return candidate
    return None


def _run_post_reveal_scaffold(window, scaffold: dict) -> None:
    """Scaffold a just-created solution over the revealed main window.

    The scaffolding runs with a blocking modal progress dialog so the user
    cannot interact with the IDE until it finishes or is cancelled.

    Args:
        window: The revealed DreamStudio main window.
        scaffold: Pending-scaffold dict emitted by the solution prompt.
    """
    try:
        from editor.utils.solution.QScafoldController import ScaffoldController

        controller = ScaffoldController(window, scaffold)
        controller.run_blocking()
    except Exception:
        import logging
        import traceback

        logging.getLogger(__name__).error(
            "Scaffolding failed:\n%s", traceback.format_exc()
        )
        try:
            from editor.utils.notifications.notification_manager import (
                get_notification_manager,
            )

            get_notification_manager().add_error(
                "Scaffold", "Project scaffolding failed; see logs.", source="Startup"
            )
        except Exception:
            pass


def _reveal_result(result, splash) -> None:
    """Reveal a successful bootstrap result (shared by initial and retry)."""
    from PyQt6.QtCore import QTimer

    if getattr(result, "cancelled", False):
        try:
            if splash is not None and splash.is_visible:
                splash.close()
        except Exception:
            pass
        return
    if result.success and result.window is not None:
        window = result.window

        def _reveal():
            try:
                if splash is not None and splash.is_visible:
                    splash.close()
            except Exception:
                try:
                    if splash is not None:
                        splash.close()
                except Exception:
                    pass
            try:
                window.setEnabled(True)
                window.showMaximized()
            except Exception:
                pass
            try:
                window.ui_ready.emit()
            except Exception:
                import logging

                logging.getLogger(__name__).warning("ui_ready emit failed")

        QTimer.singleShot(0, _reveal)

        if result.scaffold:
            QTimer.singleShot(
                0, lambda: _run_post_reveal_scaffold(window, result.scaffold)
            )


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

    project_dir = _parse_project_arg(sys.argv[1:])
    bootstrap = BootstrapManager(base_dir=_PROJECT_ROOT, project_dir=project_dir)
    result = bootstrap.run(splash=splash)

    if result.cancelled:
        try:
            if splash.is_visible:
                splash.close()
        except Exception:
            pass
        app.quit()
        sys.exit(0)

    if result.success and result.window is not None:
        _reveal_result(result, splash)
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
