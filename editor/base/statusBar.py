from editor import *
from editor.utils.resource_path import resource_path

from editor.widgets.QToolButton import ToolbarButton
from editor.widgets.QCircularProgressBar import CircularProgressBar
from editor.utils.git_control.git_control import *


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

    def __init__(self, master, directory):
        super().__init__(master)
        self._saved_btn_fixed = None

        self.currentDirectory = directory

        self.setObjectName("StatusBar")
        self.setFrameShape(QFrame.Shape.Panel)
        self.setFixedHeight(25)
        statusbar_layout = QHBoxLayout(self)
        statusbar_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        statusbar_layout.setContentsMargins(5, 0, 5, 0)

        self.repository = return_repository(self.currentDirectory)

        ############## REPOSITORY ACTIONS ##############
        self.repoActions = ToolbarButton(
            icon_path=resource_path("assets/system/git.png"),
            tooltip="",
            icon_size=(17, 17),
            text=f"   {self.get_repo_name()} | {self.get_branch()}",
        )
        self.repoActions.setFixedHeight(23)
        self.repoActions.adjustSize()
        self.repoActions.setStyleSheet("border-radius: 0px;")
        self.repoActions.clicked.connect(self.show_branches_menu)
        statusbar_layout.addWidget(self.repoActions)

        statusbar_layout.addSpacing(5)

        self.warningBtn = ToolbarButton(
            icon_path=resource_path("assets/system/warning.png"),
            tooltip="Warnings",
            fixed_size=(45, 23),
            icon_size=(17, 17),
        )
        self.warningBtn.setStyleSheet("border-radius: 0px;")
        self.warningBtn.setObjectName("warningButton")
        self.warningBtn.setText("0")
        statusbar_layout.addWidget(self.warningBtn)

        self.errorsBtn = ToolbarButton(
            icon_path=resource_path("assets/system/problem.png"),
            tooltip="Errors",
            fixed_size=(45, 23),
            icon_size=(17, 17),
        )
        self.errorsBtn.setStyleSheet("border-radius: 0px;")
        self.errorsBtn.setObjectName("errorsButton")
        self.errorsBtn.setText("0")
        statusbar_layout.addWidget(self.errorsBtn)

        statusbar_layout.addSpacing(3)

        self.statusBtn = ToolbarButton(
            icon_path=resource_path("assets/system/status.png"),
            tooltip="Status",
            fixed_size=(80, 23),
            icon_size=(17, 17),
        )
        self.statusBtn.setStyleSheet("border-radius: 0px;")
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
            icon_path=resource_path("assets/system/terminal.png"),
            tooltip="Open Terminal",
            fixed_size=(120, 23),
            icon_size=(17, 17),
        )
        self.terminalWindow.setObjectName("terminalButton")
        self.terminalWindow.setText("   Open Terminal")
        statusbar_layout.addWidget(self.terminalWindow)

        self.notificationBtn = ToolbarButton(
            icon_path=resource_path("assets/system/notificaiton.png"),
            tooltip="Notifications",
            fixed_size=(30, 23),
            icon_size=(20, 20),
        )
        self.notificationBtn.setObjectName("notificationButton")
        statusbar_layout.addWidget(self.notificationBtn)

        self._bootstrap_log: list[str] = []

    def set_bootstrap_status(self, step_name: str, message: str) -> None:
        msg = f"[{step_name}] {message}"
        self._bootstrap_log.append(msg)
        if self._saved_btn_fixed is None:
            self._saved_btn_fixed = self.statusBtn.width()
            self._saved_btn_text = self.statusBtn.text()
            self.statusBtn.setMinimumSize(80, 23)
            self.statusBtn.setMaximumSize(16777215, 23)
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
            self.statusBtn.setFixedSize(w, 23)
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

    def get_branch(self):
        """
        Returns the repo branch currently working on.
        """
        if self.repository:
            try:
                branch = self.repository.active_branch.name
                return branch
            except Exception:
                return ""
        return ""

    def get_repo_name(self):
        """
        Returns the repository name.
        """
        if self.repository and getattr(self.repository, "working_tree_dir", None):
            try:
                return os.path.basename(self.repository.working_tree_dir)
            except Exception:
                pass
        # Fallback: use current directory name when not a git repo (e.g. /tmp)
        try:
            return os.path.basename(
                os.path.abspath(self.currentDirectory or os.getcwd())
            )
        except Exception:
            return "No Repo"

    def show_branches_menu(self):
        """Spawns a QMenu with all available branches."""
        menu = QMenu(self)

        all_branches = get_all_branches(self.repository)
        current_branch = self.get_branch()

        for branch_name in all_branches:
            if "HEAD" in branch_name:
                continue

            action = QAction(branch_name, self)

            # Highlight the current branch
            if (
                branch_name == current_branch
                or branch_name == f"heads/{current_branch}"
            ):
                action.setCheckable(True)
                action.setChecked(True)

            action.triggered.connect(
                lambda checked, b=branch_name: self.handle_branch_switch(b)
            )
            menu.addAction(action)

        menu_height = menu.sizeHint().height()
        global_pos = self.repoActions.mapToGlobal(QPoint(0, -menu_height))
        menu.exec(global_pos)

    def handle_branch_switch(self, branch_name: str):
        """Switches the branch safely, handling both local and remote references."""
        try:
            local_branches = [b.name for b in self.repository.branches]

            if branch_name in local_branches:
                switch_branch(self.repository, branch_name)

            elif "/" in branch_name:
                remote, target_local_name = branch_name.split("/", 1)

                if target_local_name in local_branches:
                    switch_branch(self.repository, target_local_name)
                else:
                    self.repository.git.checkout("-b", target_local_name, branch_name)
            else:
                switch_branch(self.repository, branch_name)

            self.repoActions.setText(f"   {self.get_repo_name()} | {self.get_branch()}")
            self.repoActions.adjustSize()

            print(f"Successfully switched to {branch_name}")

        except Exception as e:
            print(f"Failed to switch branch: {e}")
