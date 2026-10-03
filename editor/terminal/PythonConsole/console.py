from editor import *
from editor.utils.notifications.notification_manager import get_notification_manager
from editor.utils.resource_path import resource_path
from editor.widgets.QToolButton import ToolbarButton

try:
    from qtconsole.manager import QtKernelManager
    from qtconsole.rich_ipython_widget import RichJupyterWidget

    _JUPYTER_AVAILABLE = True
except ImportError:
    QtKernelManager = None  # type: ignore
    RichJupyterWidget = None  # type: ignore
    _JUPYTER_AVAILABLE = False


class PythonShell(QWidget):
    """
    Python commands shell GUI interfacing a Jupyter kernel in background.
    """

    COMPLETION_STYLE = "droplist"
    COMPLETION_HEIGHT = 12
    BUFFER_SIZE = 10000
    CONSOLE_WIDTH = 120

    def __init__(self, parent=None, cwd=None):
        super().__init__(parent)
        self.setObjectName("PythonShell")
        self._workspace_dir = ""
        self._restart_attempts = 0
        self._unavailable = not _JUPYTER_AVAILABLE

        if self._unavailable:
            layout = QVBoxLayout(self)
            msg = QLabel(
                "Python console unavailable: install qtconsole + jupyter to enable."
            )
            msg.setWordWrap(True)
            layout.addWidget(msg)
            self.kernel_manager = None
            self.kernel_client = None
            self.console = None
            return

        resolved_cwd = cwd if isinstance(cwd, str) and cwd else self._detect_workspace()
        if resolved_cwd and os.path.isdir(resolved_cwd):
            self._workspace_dir = os.path.abspath(resolved_cwd)

        self.kernel_manager = QtKernelManager(kernel_name="python3")
        try:
            self.kernel_manager.start_kernel(cwd=self._workspace_dir or None)
        except Exception:
            self.kernel_manager.start_kernel()
        try:
            app = QApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self._shutdown_kernel)
        except Exception:
            pass

        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        self.console = RichJupyterWidget(parent=self)
        self.console.setObjectName("JupyterConsole")
        self.console.kernel_manager = self.kernel_manager
        self.console.kernel_client = self.kernel_client

        self.console.gui_completion = self.COMPLETION_STYLE
        self.console.gui_completion_height = self.COMPLETION_HEIGHT
        self.console.buffer_size = self.BUFFER_SIZE

        self.console.banner = (
            "(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.\n"
            "Python Interpreter Shell for DreamStudio - Jupyter Backend.\n"
            "Type commands or code below.\n\n"
        )

        self.console.in_prompt = ">>> "
        self.console.out_prompt = ""
        self.console.font_size = 10

        self.console.custom_edit = True
        self.console.custom_restart = True

        self._build_toolbar()
        self._connect_signals()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar_container)
        layout.addWidget(self.console)

    def _detect_workspace(self) -> str:
        """Return window workspace without using process CWD."""
        try:
            top = self.window()
            candidate = getattr(top, "currentDirectory", "") if top else ""
            if candidate and os.path.isdir(str(candidate)):
                return os.path.abspath(str(candidate))
        except Exception:
            pass
        return ""

    def set_workspace(self, path: str) -> None:
        """Track workspace switches; restart kernel cwd when possible."""
        if getattr(self, "_unavailable", False):
            return
        if not path or not os.path.isdir(path):
            return
        self._workspace_dir = os.path.abspath(path)
        try:
            self.console.execute(f"%cd -q {shlex.quote(self._workspace_dir)}")
        except Exception:
            pass

    def _shutdown_kernel(self) -> None:
        """Best-effort kernel shutdown for app quit."""
        if getattr(self, "_unavailable", False):
            return
        try:
            self.kernel_client.stop_channels()
        except Exception:
            pass
        try:
            self.kernel_manager.shutdown_kernel(now=True)
        except Exception:
            pass

    def _build_toolbar(self):
        self._toolbar_container = QWidget()
        self._toolbar_container.setObjectName("PythonShellToolbar")
        self._toolbar_container.setStyleSheet("background-color: transparent;")
        toolbar_layout = QHBoxLayout(self._toolbar_container)
        toolbar_layout.setContentsMargins(4, 2, 4, 2)
        toolbar_layout.setSpacing(2)

        self._btn_run = ToolbarButton(
            icon_path="assets/menus/run.png",
            tooltip="",
            fixed_size=(140, 24),
            icon_size=(18, 18),
            callback=self._on_run_file,
            text="Run Python File",
        )
        toolbar_layout.addWidget(self._btn_run)

        self._btn_restart = ToolbarButton(
            icon_path="assets/menus/restart.png",
            tooltip="",
            text="Restart Kernel",
            fixed_size=(140, 24),
            icon_size=(18, 18),
            callback=self.restart_kernel,
        )
        toolbar_layout.addWidget(self._btn_restart)

        self._btn_interrupt = ToolbarButton(
            icon_path="assets/menus/stop.png",
            tooltip="",
            fixed_size=(140, 24),
            icon_size=(18, 18),
            callback=self.interrupt_kernel,
            text="Interrupt Kernel",
        )
        toolbar_layout.addWidget(self._btn_interrupt)

        sep = QFrame()
        sep.setObjectName("ToolbarSeparator")
        sep.setFixedWidth(1)
        sep.setFixedHeight(18)
        toolbar_layout.addWidget(sep, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._btn_clear = ToolbarButton(
            icon_path="assets/menus/trash.png",
            text="Clear Console",
            fixed_size=(140, 24),
            icon_size=(18, 18),
            callback=self.clear_console,
            tooltip="",
        )
        toolbar_layout.addWidget(self._btn_clear)

        toolbar_layout.addStretch()

        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("PythonShellStatus")
        self._status_label.setStyleSheet("font-size: 13px;")
        toolbar_layout.addWidget(self._status_label)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.console.executing.connect(self._on_executing)
        self.console.executed.connect(self._on_executed)
        self.console.custom_edit_requested.connect(self._on_custom_edit)
        self.console.custom_restart_kernel_died.connect(self._on_kernel_died)

    def _on_executing(self):
        self._status_label.setText("Busy")
        self._status_label.setProperty("status", "busy")

    def _on_executed(self):
        self._status_label.setText("Ready")
        self._status_label.setProperty("status", "ready")

    def _on_custom_edit(self, filename, line):
        try:
            tabs = self.window().hero_window._text_editor_center._tabs
            tabs.open_file_at_line(str(filename), int(line) if line else 0)
        except Exception:
            pass

    def _on_kernel_died(self, since_last_heartbeat):
        self._status_label.setText("Kernel died")
        self._status_label.setProperty("status", "busy")
        self._restart_attempts += 1
        if self._restart_attempts > 3:
            get_notification_manager().add_error(
                "Python Kernel",
                "Kernel died repeatedly; automatic restart stopped. "
                "Use Restart Kernel manually.",
                source="PythonConsole",
            )
            return
        get_notification_manager().add_error(
            "Python Kernel",
            f"Kernel died (no heartbeat for {since_last_heartbeat:.1f}s). "
            "Restarting...",
            source="PythonConsole",
        )
        try:
            self.restart_kernel()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Kernel lifecycle
    # ------------------------------------------------------------------

    def _quote(self, path: str) -> str:
        """Platform-aware shell quoting for Jupyter magics."""
        import sys as _sys

        if _sys.platform == "win32":
            escaped = str(path).replace('"', '""')
            return f'"{escaped}"'
        return shlex.quote(str(path))

    def restart_kernel(self, force: bool = False):
        if getattr(self, "_unavailable", False):
            return
        try:
            if not force:
                try:
                    if not self.kernel_manager.is_alive():
                        force = True
                except Exception:
                    force = True
            if force:
                try:
                    self.kernel_manager.restart_kernel(now=True)
                except Exception:
                    pass
            self.console.restart_kernel("Restarting ...")
            self._restart_attempts = 0
        except Exception:
            pass

    def force_restart_kernel(self):
        """Manual restart that works even when kernel is dead."""
        self._restart_attempts = 0
        self.restart_kernel(force=True)

    def interrupt_kernel(self):
        if getattr(self, "_unavailable", False):
            return
        self.console.interrupt_kernel()

    def clear_console(self):
        if getattr(self, "_unavailable", False):
            return
        self.console.clear()

    def run_file(self, path: str):
        if getattr(self, "_unavailable", False):
            return
        if not path or not os.path.isfile(path):
            try:
                from editor.utils.notifications.notification_manager import (
                    get_notification_manager as _nm2,
                )

                _nm2().add_error(
                    "Python Console",
                    f"File does not exist: {path}",
                    source="PythonConsole",
                )
            except Exception:
                pass
            return
        try:
            if not self.kernel_manager.is_alive():
                self.restart_kernel(force=True)
        except Exception:
            pass
        if path:
            try:
                parent = os.path.dirname(os.path.abspath(path))
                if os.path.isdir(parent):
                    self.console.execute(f"%cd -q {self._quote(parent)}")
            except Exception:
                pass
            self.console.execute(f"%run -i {self._quote(path)}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_run_file(self):
        start = self._workspace_dir if self._workspace_dir else os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Run Python File",
            start,
            "Python Files (*.py *.pyw);;All Files (*)",
        )
        if path:
            self.run_file(path)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self):
        if getattr(self, "_unavailable", False) or self.console is None:
            return
        palette = self.palette()
        bg = palette.color(QPalette.ColorRole.Window).name()
        fg = palette.color(QPalette.ColorRole.WindowText).name()
        mid = palette.color(QPalette.ColorRole.Mid).name()
        highlight = palette.color(QPalette.ColorRole.Highlight).name()

        self.console.style_sheet = (
            "QTextEdit, QPlainTextEdit {"
            "  background-color: %s;"
            "  color: %s;"
            "  selection-background-color: %s;"
            "}"
            ".in-prompt { color: %s; font-weight: bold; }"
            ".out-prompt { color: %s; font-weight: bold; }"
            ".in-prompt-number { font-weight: bold; }"
            ".out-prompt-number { font-weight: bold; }"
        ) % (bg, fg, highlight, highlight, mid)

        bg_color = QColor(bg)
        self.console.syntax_style = (
            "monokai" if bg_color.lightness() < 128 else "default"
        )

        if hasattr(self.console, "_call_tip_widget"):
            tip_palette = QToolTip.palette()
            self.console._call_tip_widget.setPalette(tip_palette)
            self.console._call_tip_widget.setFont(self.console.font)

    def changeEvent(self, event):
        if event.type() in (
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
        ):
            self._apply_theme()
        super().changeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_theme()

    def closeEvent(self, a0):
        self._shutdown_kernel()
        super().closeEvent(a0)
