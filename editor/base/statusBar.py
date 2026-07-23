from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QComboBox,
    QLabel,
    QProgressBar,
    QListWidget,
)

from editor.widgets.QToolButton import ToolbarButton


class BootstrapDetailMenu(QFrame):
    def __init__(self, messages, parent=None):
        super().__init__(
            parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.setObjectName("BootstrapDetailMenu")
        self.setFixedSize(500, 350)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title_bar = QFrame()
        self.title_bar.setObjectName("BootstrapDetailTitleBar")
        self.title_bar.setFixedHeight(36)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(12, 0, 12, 0)
        self.title_label = QLabel("Bootstrap Progress")
        self.title_label.setObjectName("BootstrapDetailTitle")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        layout.addWidget(self.title_bar)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("bootstrapList")
        for msg in messages:
            self.list_widget.addItem(msg)
        self.list_widget.scrollToBottom()
        layout.addWidget(self.list_widget)

    def add_message(self, msg):
        self.list_widget.addItem(msg)
        self.list_widget.scrollToBottom()


class StatusBar(QFrame):
    bootstrap_done = pyqtSignal(bool)

    def __init__(self, master):
        super().__init__(master)
        self._saved_btn_fixed = None

        self.setObjectName("StatusBar")
        self.setFrameShape(QFrame.Shape.Panel)
        self.setFixedHeight(30)
        statusbar_layout = QHBoxLayout(self)
        statusbar_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        statusbar_layout.setContentsMargins(5, 0, 5, 0)

        self.zoomBtn = QComboBox()
        self.zoomBtn.setObjectName("zoomComboBox")
        self.zoomBtn.setFixedSize(40, 28)
        self.zoomBtn.addItems(["75%", "100%", "110%", "125%"])
        self.zoomBtn.view().setMinimumWidth(80)
        self.zoomBtn.setCurrentIndex(1)
        self.zoomBtn.view().setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.zoomBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.zoomBtn.currentTextChanged.connect(self.on_zoom_toggle)
        statusbar_layout.addWidget(self.zoomBtn)

        statusbar_layout.addSpacing(3)

        self.warningBtn = ToolbarButton(
            icon_path="assets/system/warning.png",
            tooltip="Warnings",
            fixed_size=(45, 28),
            icon_size=(17, 17),
        )
        self.warningBtn.setObjectName("warningButton")
        self.warningBtn.setText("0")
        statusbar_layout.addWidget(self.warningBtn)

        statusbar_layout.addSpacing(3)

        self.errorsBtn = ToolbarButton(
            icon_path="assets/system/problem.png",
            tooltip="Errors",
            fixed_size=(45, 28),
            icon_size=(17, 17),
        )
        self.errorsBtn.setObjectName("errorsButton")
        self.errorsBtn.setText("0")
        statusbar_layout.addWidget(self.errorsBtn)

        statusbar_layout.addSpacing(3)

        self.statusBtn = ToolbarButton(
            icon_path="assets/system/status.png",
            tooltip="Status",
            fixed_size=(80, 28),
            icon_size=(17, 17),
        )
        self.statusBtn.setObjectName("statusButton")
        self.statusBtn.setText("   Ready")
        statusbar_layout.addWidget(self.statusBtn)

        self.bootstrap_progress_container = QFrame()
        self.bootstrap_progress_container.setObjectName("bootstrapProgressContainer")
        self.bootstrap_progress_container.setFixedSize(100, 20)
        progress_container_layout = QHBoxLayout(self.bootstrap_progress_container)
        progress_container_layout.setContentsMargins(0, 0, 0, 0)
        self.bootstrap_progress = QProgressBar()
        self.bootstrap_progress.setObjectName("bootstrapProgress")
        self.bootstrap_progress.setTextVisible(False)
        self.bootstrap_progress.setFixedHeight(6)
        self.bootstrap_progress.setRange(0, 0)
        self.bootstrap_progress.hide()
        progress_container_layout.addWidget(self.bootstrap_progress)
        statusbar_layout.addWidget(self.bootstrap_progress_container)

        statusbar_layout.addStretch()

        self.lines_and_cols = QLabel()
        self.lines_and_cols.setObjectName("lineColLabel")
        self.lines_and_cols.setText("Ln 1 : Col 1")
        statusbar_layout.addWidget(self.lines_and_cols)

        self.spacing_options = QLabel()
        self.spacing_options.setObjectName("indentLabel")
        self.spacing_options.setText("Indent: 4 Spaces")
        statusbar_layout.addWidget(self.spacing_options)

        self.EOL = QLabel()
        self.EOL.setObjectName("eolLabel")
        self.EOL.setText("LF")
        statusbar_layout.addWidget(self.EOL)

        self.terminalWindow = ToolbarButton(
            icon_path="assets/system/terminal.png",
            tooltip="Open Terminal",
            fixed_size=(120, 28),
            icon_size=(17, 17),
        )
        self.terminalWindow.setObjectName("terminalButton")
        self.terminalWindow.setText("   Open Terminal")
        statusbar_layout.addWidget(self.terminalWindow)

        self.notificationBtn = ToolbarButton(
            icon_path="assets/system/notificaiton.png",
            tooltip="Notifications",
            fixed_size=(30, 28),
            icon_size=(20, 20),
        )
        self.notificationBtn.setObjectName("notificationButton")
        statusbar_layout.addWidget(self.notificationBtn)

        self._bootstrap_log: list[str] = []

    def on_zoom_toggle(self, zoomText: str):
        if not zoomText:
            return
        try:
            percent = int(zoomText.replace("%", "").strip())
            zoom_map = {"75": -2, "100": 0, "110": 1, "125": 3, "150": 5}
            zoom_level = zoom_map.get(str(percent), 0)
            self.text_zoom_toggle(zoom_level)
        except Exception as e:
            print(f"Zoom error: {e}")

    def set_bootstrap_status(self, step_name: str, message: str) -> None:
        msg = f"[{step_name}] {message}"
        self._bootstrap_log.append(msg)
        if self._saved_btn_fixed is None:
            self._saved_btn_fixed = self.statusBtn.width()
            self._saved_btn_text = self.statusBtn.text()
            self.statusBtn.setMinimumSize(80, 28)
            self.statusBtn.setMaximumSize(16777215, 28)
        self.statusBtn.setText(f"  {message}")
        self.statusBtn.setToolTip(f"Step: {step_name}")
        self.bootstrap_progress.show()
        popup = getattr(self, "_bootstrap_popup", None)
        if popup is not None and popup.isVisible():
            popup.add_message(msg)

    def set_bootstrap_finished(self, success: bool) -> None:
        self.bootstrap_progress.hide()
        if self._saved_btn_fixed is not None:
            w = self._saved_btn_fixed
            self._saved_btn_fixed = None
            self._saved_btn_text = None
            self.statusBtn.setFixedSize(w, 28)
        if success:
            self.statusBtn.setText("  Ready")
            self.statusBtn.setToolTip("Project initialized successfully")
        else:
            self.statusBtn.setText("  Failed")
            self.statusBtn.setToolTip("Project initialization failed")
        self.bootstrap_done.emit(True)
        popup = getattr(self, "_bootstrap_popup", None)
        if popup is not None and popup.isVisible():
            popup.add_message(
                "Bootstrap completed successfully." if success else "Bootstrap failed."
            )

    def show_bootstrap_details(self) -> None:
        if not self._bootstrap_log:
            return
        popup = getattr(self, "_bootstrap_popup", None)
        if popup is not None and popup.isVisible():
            popup.close()
            return
        popup = BootstrapDetailMenu(self._bootstrap_log, self.window())
        btn_pos = self.statusBtn.mapToGlobal(self.statusBtn.rect().topLeft())
        screen = self.screen().geometry()
        popup_x = max(screen.left(), min(btn_pos.x(), screen.right() - popup.width()))
        popup_y = btn_pos.y() - popup.height() - 4
        if popup_y < screen.top():
            popup_y = btn_pos.y() + self.statusBtn.height() + 4
        popup.move(popup_x, popup_y)
        popup.show()
        self._bootstrap_popup = popup

    def clear_bootstrap_log(self) -> None:
        self._bootstrap_log.clear()

    def text_zoom_toggle(self, zoom_level: int):
        main_win = self.window()
        tabs = getattr(main_win, "tab_editors", None)
        if not tabs:
            return
        for i in range(tabs.count()):
            editor = tabs.widget(i)
            if editor and hasattr(editor, "zoomTo"):
                editor.zoomTo(zoom_level)

    def set_debug_background(self) -> None:
        """Paint the entire status bar orange to indicate an active debug session."""
        self.setStyleSheet(
            "StatusBar { background-color: #FF9800; }"
            "StatusBar QLabel { color: white; }"
        )

    def reset_background(self) -> None:
        """Restore the status bar to its theme-default appearance."""
        self.setStyleSheet("")
