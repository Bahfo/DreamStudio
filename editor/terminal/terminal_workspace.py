"""
(C) COPYRIGHT 2026 EXcellent TechStacks
Terminal Emulator Logic for DreamStudio.
"""

from editor import *
from editor.utils.resource_path import resource_path

from editor.terminal.emulator import ShellEmulator
from editor.terminal.terminal_display import TerminalDisplay

import shlex
import subprocess

logger = logging.getLogger(__name__)

# Grace period (ms) between spawning the interactive shell and submitting
# a programmatic command line, so the prompt is initialized first.
_RUN_COMMAND_DELAY_MS = 250


def format_command_line(argv: list[str]) -> str:
    """Render an argv sequence as a single safely-quoted shell command line.

    Args:
        argv: The argument sequence (interpreter, file path, parameters).

    Returns:
        A string safe to paste into an interactive shell — arguments with
        spaces or shell-sensitive characters remain single arguments.
    """
    if sys.platform == "win32":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


class _SessionItem(QWidget):
    kill_clicked = pyqtSignal(int)

    def __init__(self, session_id: int, display_name: str, parent=None):
        super().__init__(parent)
        self.session_id = session_id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        self._label = QLabel(display_name)
        self._label.setObjectName("terminalSessionLabel")
        layout.addWidget(self._label)

        layout.addStretch()

        btn_kill = QPushButton()
        btn_kill.setObjectName("terminalKillBtn")
        btn_kill.setIcon(QIcon(resource_path("assets/menus/trash.png")))
        btn_kill.setFixedSize(20, 20)
        btn_kill.setToolTip("Kill this terminal session")
        btn_kill.clicked.connect(self._on_kill)
        layout.addWidget(btn_kill)

    def _on_kill(self) -> None:
        self.kill_clicked.emit(self.session_id)


class _TerminalView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.display = TerminalDisplay()
        layout.addWidget(self.display, 1)

        self._scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self._scrollbar.setObjectName("terminalViewScrollbar")
        layout.addWidget(self._scrollbar)

        self.display.history_changed.connect(self._on_display_history)
        self._scrollbar.valueChanged.connect(self._on_scrollbar_changed)

    def _on_display_history(self, offset: int, max_offset: int) -> None:
        self._scrollbar.blockSignals(True)
        self._scrollbar.setRange(0, max_offset)
        self._scrollbar.setPageStep(self.display.rows)
        self._scrollbar.setValue(offset)
        self._scrollbar.blockSignals(False)

    def _on_scrollbar_changed(self, value: int) -> None:
        self.display.set_scroll_offset(value)

    def set_theme(self, bg: str, fg: str, sel: str) -> None:
        self.display.set_theme(bg, fg, sel)


class _EmptyTerminalPlaceholder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self._icon = QLabel()
        self._icon.setObjectName("terminalPlaceholderIcon")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(resource_path("assets/system/sleeping.png"))
        if not pixmap.isNull():
            self._icon.setPixmap(
                pixmap.scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel("No Terminals Open")
        self._title.setObjectName("terminalPlaceholderTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title, 0, Qt.AlignmentFlag.AlignCenter)

        self._subtitle = QLabel(
            "Click the (+) button to add a new system terminal,\n"
            "or click the tools menu (...) to configure a terminal."
        )
        self._subtitle.setObjectName("terminalPlaceholderSubtitle")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)
        layout.addWidget(self._subtitle, 0, Qt.AlignmentFlag.AlignCenter)


class TerminalWorkspace(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions: dict[int, dict] = {}
        self._id_counter = 0
        self._active_id: int | None = None
        self._theme_bg: str | None = None
        self._theme_fg: str | None = None
        self._theme_sel: str | None = None

        self.setObjectName("terminalWorkspace")
        self.setStyleSheet("border:none;")

        self._build_ui()

        # ------------------------------------------------------------------
        # Zero-orphan cleanup (Step 7)
        #
        # Connect to QApplication.aboutToQuit so that every PTY, child
        # process, and reader thread is forcibly terminated when the
        # application exits — even if the workspace widget was hidden (the
        # normal close button merely toggles visibility via closeEvent).
        # ------------------------------------------------------------------
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cleanup)

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 0, 0, 0)
        outer.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setObjectName("terminalWorkspaceSplitter")
        self._splitter.setHandleWidth(1)

        self._stack = QStackedWidget()
        self._empty_placeholder = _EmptyTerminalPlaceholder()
        self._stack.addWidget(self._empty_placeholder)
        self._stack.setCurrentWidget(self._empty_placeholder)
        self._splitter.addWidget(self._stack)

        self._sidebar = self._build_sidebar()
        self._splitter.addWidget(self._sidebar)

        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setSizes([600, 200])

        outer.addWidget(self._splitter)

    def _build_sidebar(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("terminalSidebar")
        widget.setMinimumWidth(160)
        widget.setMaximumWidth(320)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("terminalSidebarHeader")
        header.setFixedHeight(30)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(0)

        self._sidebar_title = QLabel("TERMINALS")
        self._sidebar_title.setObjectName("terminalSidebarTitle")
        header_layout.addWidget(self._sidebar_title)
        header_layout.addStretch()

        self._sidebar_add_btn = QPushButton("+")
        self._sidebar_add_btn.setObjectName("terminalSidebarAddBtn")
        self._sidebar_add_btn.setFixedSize(22, 22)
        self._sidebar_add_btn.setToolTip("Create new terminal session")
        self._sidebar_add_btn.clicked.connect(self._show_terminal_type_menu)
        header_layout.addWidget(self._sidebar_add_btn)

        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list.setObjectName("terminalSessionList")
        self._list.currentRowChanged.connect(self._on_list_row_changed)
        layout.addWidget(self._list)

        return widget

    def _show_terminal_type_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("border: 1px solid;")

        is_windows = sys.platform == "win32"
        primary_label = "PowerShell" if is_windows else "Bash"
        primary_shell = (
            "powershell.exe" if is_windows else os.environ.get("SHELL", "/bin/bash")
        )

        primary_act = QAction(primary_label, menu)
        primary_act.triggered.connect(
            lambda checked, shell=primary_shell: self._on_add_session(shell=shell)
        )
        menu.addAction(primary_act)

        menu.addSeparator()

        placeholder_types = [
            "Zsh",
            "Fish",
            "cmd (Command Prompt)",
            "SSH Session",
            "Docker Container",
            "WSL",
        ]
        for label in placeholder_types:
            act = QAction(label, menu)
            act.setEnabled(False)
            menu.addAction(act)

        menu.exec(QCursor.pos())

    def _on_add_session(self, cwd: str | None = None, shell: str | None = None) -> None:
        self._id_counter += 1
        session_id = self._id_counter

        if shell is None:
            shell = os.environ.get("SHELL", "/bin/bash")
        shell_name = os.path.basename(shell)
        display_name = f"{shell_name}"

        view = _TerminalView()
        display = view.display
        emulator = ShellEmulator()

        emulator.raw_output_received.connect(display.feed)
        display.send_data.connect(
            lambda data, e=emulator: e.write(data.decode("utf-8", errors="replace"))
        )
        display.resized.connect(emulator.resize)
        display.set_emulator(emulator)

        # Query the display widget's current geometry and pass it to the
        # emulator so the PTY is spawned at the correct size from the
        # very first frame (Step 5 — dynamic WinPty spawn dimensions).
        init_cols = display._columns
        init_rows = display._rows
        # If the widget already has a real size, recompute from metrics.
        if display._cw > 0 and display._ch > 0 and display.width() > 0:
            init_cols = max(20, display.width() // max(1, display._cw))
            init_rows = max(5, display.height() // max(1, display._ch))

        emulator.start(cwd=cwd or os.getcwd(), rows=init_rows, cols=init_cols)

        self._stack.addWidget(view)

        if self._stack.currentWidget() is self._empty_placeholder:
            self._stack.setCurrentWidget(view)

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, session_id)
        session_widget = _SessionItem(session_id, display_name)
        session_widget.kill_clicked.connect(self.kill_session)
        item.setSizeHint(session_widget.sizeHint())

        self._list.blockSignals(True)
        self._list.addItem(item)
        self._list.setItemWidget(item, session_widget)
        new_row = self._list.count() - 1
        self._list.blockSignals(False)

        self._sessions[session_id] = {
            "view": view,
            "display": display,
            "emulator": emulator,
            "list_item": item,
            "session_widget": session_widget,
            "name": display_name,
        }

        if self._theme_bg is not None:
            display.set_theme(self._theme_bg, self._theme_fg, self._theme_sel)

        self._list.setCurrentRow(new_row)

    def _on_list_row_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self._list.item(row)
        if item is None:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id not in self._sessions:
            return

        view = self._sessions[session_id]["view"]
        self._stack.setCurrentWidget(view)
        display = view.display

        QTimer.singleShot(0, display.setFocus)

        self._active_id = session_id

    # ------------------------------------------------------------------
    # Session removal (Step 9 — boundary-safe)
    # ------------------------------------------------------------------

    def kill_session(self, session_id: int) -> None:
        """Remove and forcibly terminate a single terminal session.

        Boundary-safety guarantees:
        * When the *last* session is closed (``remaining == 0``), all
          selection highlights are cleared and focus is redirected to the
          ``_empty_placeholder`` widget — the ``-1`` index pitfall is
          completely avoided by bypassing ``setCurrentRow`` entirely.
        * ``setCurrentRow`` is wrapped in ``blockSignals`` so the
          ``currentRowChanged`` signal cannot fire with a stale session
          that was just removed from ``_sessions``.
        * ``max(0, ...)`` clamping prevents negative row indices even if
          the item was already removed from the list.
        """
        session = self._sessions.pop(session_id, None)
        if session is None:
            return

        emulator = session["emulator"]
        view = session["view"]
        item = session["list_item"]

        idx = self._stack.indexOf(view)
        if idx >= 0:
            self._stack.removeWidget(view)
        view.deleteLater()

        row = self._list.row(item)
        self._list.blockSignals(True)
        self._list.takeItem(row)
        self._list.blockSignals(False)

        if self._active_id == session_id:
            self._active_id = None
            remaining = self._list.count()
            if remaining > 0:
                # Clamp to valid range — can never be negative.
                new_row = max(0, min(row, remaining - 1))
                # Block signals to prevent re-entrant row changes while
                # the session dict is in a partially-updated state.
                self._list.blockSignals(True)
                self._list.setCurrentRow(new_row)
                self._list.blockSignals(False)
                # Manually trigger the view switch now that signals are
                # unblocked and the session map is consistent.
                self._on_list_row_changed(new_row)
            else:
                # Zero sessions remain — clear any stale selection
                # highlight in the list widget and reset focus to the
                # empty-state placeholder.
                self._list.clearSelection()
                self._stack.setCurrentWidget(self._empty_placeholder)
                QTimer.singleShot(0, self._empty_placeholder.setFocus)

        emulator.kill()

        if len(self._sessions) == 0:
            self._stack.setCurrentWidget(self._empty_placeholder)

    def active_session_id(self) -> int | None:
        return self._active_id

    def open_command_session(
        self, argv: list[str], cwd: str | None = None, name: str | None = None
    ) -> bool:
        """Create a new interactive terminal session and submit a command
        line to it.

        The session is created through the exact same path as a
        user-initiated terminal (``_on_add_session``) — a real PTY-backed
        interactive shell — and the command is then written to the PTY as
        if typed at the prompt, so stdout/stderr stream directly into the
        integrated terminal.

        Args:
            argv: The argument sequence to execute (must be non-empty).
            cwd: Working directory for the new session.
            name: Optional display name override for the session tab.

        Returns:
            True when the session was created and the command submitted,
            False when no session could be located afterwards.

        Raises:
            RuntimeError: If the PTY backend fails to spawn the shell.
        """
        if not argv:
            return False

        self._on_add_session(cwd=cwd)
        session = self._sessions.get(self._active_id)
        if session is None:
            return False

        if name:
            session["session_widget"]._label.setText(name)
            session["name"] = name

        emulator = session["emulator"]
        command_line = format_command_line(argv)

        def _submit() -> None:
            # Write through the same channel used for user keystrokes
            # (display.send_data -> emulator.write).
            emulator.write(command_line + "\n")

        QTimer.singleShot(_RUN_COMMAND_DELAY_MS, _submit)
        return True

    def active_count(self) -> int:
        return len(self._sessions)

    def set_theme(self, bg: str, fg: str, sel: str) -> None:
        self._theme_bg = bg
        self._theme_fg = fg
        self._theme_sel = sel
        for session in self._sessions.values():
            session["view"].display.set_theme(bg, fg, sel)

    # ------------------------------------------------------------------
    # Zero-orphan cleanup (Step 7)
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Aggressively terminate every session and release all PTY
        resources.

        Iterates over a snapshot of the session keys (via
        ``list(self._sessions.keys())``) so that the dict can be safely
        mutated during iteration by ``kill_session``.  Each session's
        ``emulator.kill()`` closes the PTY master fd (unblocking any
        reader thread), sends SIGKILL to the process group, and joins
        the reader thread with a timeout — no zombie processes or leaked
        file descriptors are left behind.
        """
        for session_id in list(self._sessions.keys()):
            self.kill_session(session_id)

    def closeEvent(self, event) -> None:
        """Intercept close to hide the workspace rather than destroy it.

        The close button in the terminal panel toggles visibility via the
        ``close_requested`` signal, so ``closeEvent`` merely hides the
        widget and rejects the event.  Actual resource cleanup is handled
        by ``cleanup()`` which is connected to
        ``QApplication.aboutToQuit`` — this guarantees teardown runs
        exactly once when the IDE shuts down, regardless of whether the
        workspace was visible at that moment.
        """
        self.hide()
        event.ignore()
