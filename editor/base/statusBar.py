from editor import *
from editor.utils.resource_path import resource_path

from editor.widgets.QToolButton import ToolbarButton
from editor.widgets.QIndexingProgress import IndexingProgress
from editor.utils.git_control.git_control import *

#: Severity groups that own a diagnostic status-bar button, in display order.
#: The label is what the right-click menu shows; the group name is what the
#: Problems panel understands.
DIAGNOSTIC_GROUPS = (
    ("errors", "Problems"),
    ("warnings", "Warnings"),
    ("checks", "Checks"),
)

#: Labels for the groups the panel knows but that own no button. They are
#: listed in the same menu, after the button-backed groups, so a diagnostic of
#: such a group can still be switched off.
UNBUTTONED_GROUP_LABELS = {
    "typos": "Typos & Notes",
}


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
        self._branch_menu_no_repo_notified = False
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

        self.checksBtn = ToolbarButton(
            icon_path=resource_path("assets/system/bug.png"),
            tooltip="Checks",
            fixed_size=(45, 23),
            icon_size=(17, 17),
        )
        self.checksBtn.setStyleSheet("border-radius: 0px;")
        self.checksBtn.setObjectName("checksButton")
        self.checksBtn.setText("0")
        statusbar_layout.addWidget(self.checksBtn)

        # Right-clicking any diagnostic button opens the display options for
        # the three groups (list them in the tree / underline them).
        self._problems_panel = None
        self._group_buttons = {
            "errors": self.errorsBtn,
            "warnings": self.warningBtn,
            "checks": self.checksBtn,
        }
        for button in self._group_buttons.values():
            button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            button.customContextMenuRequested.connect(
                lambda pos, btn=button: self._show_diagnostics_menu(btn, pos)
            )

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

        self.indexing_bar = IndexingProgress(self)
        self.indexing_bar.setObjectName("indexingProgress")
        statusbar_layout.addWidget(self.indexing_bar)

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

    def set_debug_background(self) -> None:
        """Paint the entire status bar orange to indicate an active debug session."""
        self.setStyleSheet(
            "StatusBar { background-color: #FF9800; }"
            "StatusBar QLabel { color: white; }"
        )

    def reset_background(self) -> None:
        """Restore the status bar to its theme-default appearance."""
        self.setStyleSheet("")

    def attach_problems_panel(self, panel) -> None:
        """Bind the Problems panel whose display options these buttons drive.

        Also wires the panel's indexing signals to the status-bar progress
        indicator, so a repository scan shows a loader bar until it ends.

        Args:
            panel: The ``ProblemsWidget`` the menu reads and updates. When it
                is ``None`` the menu reports that the panel is unavailable.
        """
        self._problems_panel = panel
        try:
            if panel is None:
                return
            panel.indexing_started.connect(self.indexing_bar.start_indexing)
            panel.indexing_progress.connect(self.indexing_bar.advance_indexing)
            panel.indexing_finished.connect(self.indexing_bar.finish_indexing)
        except Exception:
            pass

    def problems_panel(self):
        """Return the attached Problems panel, or ``None``."""
        return self._problems_panel

    def _group_of_button(self, button) -> str:
        """Return the severity group *button* stands for (``""`` if unknown)."""
        for group, candidate in self._group_buttons.items():
            if candidate is button:
                return group
        return ""

    def _show_diagnostics_menu(self, button, position) -> None:
        """Open the diagnostic display options for the right-clicked *button*."""
        menu = self.build_diagnostics_menu(button)
        menu.exec(button.mapToGlobal(position))

    def _menu_groups(self, clicked_group: str) -> list:
        """Return the ``(group, label)`` pairs the display menu lists.

        The button-backed groups come first — the right-clicked one ahead of
        the others — followed by every remaining group the Problems panel
        knows. A group owning no button must still be listed: otherwise its
        diagnostics would stay underlined in the editor with no switch able to
        turn them off.

        Args:
            clicked_group: Group of the right-clicked button, if any.

        Returns:
            Ordered ``(group, label)`` tuples, one per severity group.
        """
        ordered = sorted(DIAGNOSTIC_GROUPS, key=lambda item: item[0] != clicked_group)
        known = {group for group, _label in ordered}
        panel = self._problems_panel
        groups = getattr(panel, "severity_groups", None)
        if callable(groups):
            groups = groups()
        for group in groups or ():
            if group in known:
                continue
            known.add(group)
            ordered.append((group, UNBUTTONED_GROUP_LABELS.get(group, group.title())))
        return ordered

    def build_diagnostics_menu(self, button=None) -> QMenu:
        """Build the display-options menu of the diagnostic buttons.

        Each group owns two independent switches: whether its rows are listed
        in the Problems panel, and whether it is underlined in the code
        editor. The group of the right-clicked *button* comes first, and every
        group the Problems panel knows is listed — not only the button-backed
        ones — so each diagnostic type can be switched off.

        Args:
            button: The button that was clicked, used to order the groups.

        Returns:
            A ready-to-exec :class:`QMenu`; the caller owns it.
        """
        panel = self._problems_panel
        menu = QMenu(self)
        clicked_group = self._group_of_button(button)
        ordered = self._menu_groups(clicked_group)

        for group, label in ordered:
            submenu = menu.addMenu(label)
            shown = None if panel is None else panel.is_group_enabled(group)
            underlined = None if panel is None else panel.is_group_underlined(group)
            panel_action = submenu.addAction("Show in Problems panel")
            panel_action.setCheckable(True)
            panel_action.setChecked(bool(shown))
            panel_action.setEnabled(panel is not None)
            panel_action.toggled.connect(
                lambda enabled, g=group: self._set_group_shown(g, enabled)
            )
            underline_action = submenu.addAction("Underline in editor")
            underline_action.setCheckable(True)
            underline_action.setChecked(bool(underlined))
            underline_action.setEnabled(panel is not None)
            underline_action.toggled.connect(
                lambda enabled, g=group: self._set_group_underlined(g, enabled)
            )

        menu.addSeparator()
        show_all = menu.addAction("Show all groups in panel")
        show_all.setEnabled(panel is not None)
        show_all.triggered.connect(lambda: self._set_all_groups(True))
        underline_all = menu.addAction("Underline all groups in editor")
        underline_all.setEnabled(panel is not None)
        underline_all.triggered.connect(lambda: self._set_all_underlined(True))
        reset = menu.addAction("Reset display options")
        reset.setEnabled(panel is not None)
        reset.triggered.connect(self._reset_display_options)

        if panel is None:
            placeholder = menu.addAction("Problems panel unavailable")
            placeholder.setEnabled(False)
        return menu

    def _set_group_shown(self, group: str, enabled: bool) -> None:
        """Show or hide *group* rows in the Problems panel."""
        if self._problems_panel is not None:
            self._problems_panel.set_group_enabled(group, enabled)

    def _set_group_underlined(self, group: str, enabled: bool) -> None:
        """Turn editor underlining on or off for *group*."""
        if self._problems_panel is not None:
            self._problems_panel.set_group_underlined(group, enabled)

    def _set_all_groups(self, enabled: bool) -> None:
        """Show or hide every severity group in the Problems panel.

        "All" covers every group the panel knows, including the ones without a
        status-bar button, so the panel decides what that means.
        """
        panel = self._problems_panel
        if panel is None:
            return
        if enabled:
            panel.show_all_groups()
        else:
            panel.set_enabled_groups(())

    def _set_all_underlined(self, enabled: bool) -> None:
        """Turn editor underlining on or off for every severity group."""
        panel = self._problems_panel
        if panel is None:
            return
        if enabled:
            panel.underline_all_groups()
        else:
            panel.set_underlined_groups(())

    def _reset_display_options(self) -> None:
        """Restore the default display options of the Problems panel."""
        if self._problems_panel is not None:
            self._problems_panel.reset_display_options()

    def set_problem_counts(self, errors: int, warnings: int, checks: int = 0) -> None:
        """Publish the Problems-panel counts on the diagnostic buttons.

        Args:
            errors: Number of error-severity diagnostics.
            warnings: Number of warning-severity diagnostics.
            checks: Number of failed non-fatal checks (bare ``except``, …).
        """
        try:
            error_count = max(0, int(errors))
            warning_count = max(0, int(warnings))
            check_count = max(0, int(checks))
        except (TypeError, ValueError):
            return
        self.errorsBtn.setText(str(error_count))
        self.errorsBtn.setToolTip(f"{error_count} error(s) — open the Problems panel")
        self.warningBtn.setText(str(warning_count))
        self.warningBtn.setToolTip(
            f"{warning_count} warning(s) — open the Problems panel"
        )
        self.checksBtn.setText(str(check_count))
        self.checksBtn.setToolTip(
            f"{check_count} check(s) — open the Problems panel on checks only"
        )

    def set_workspace(self, directory: str) -> None:
        """Re-bind the status bar to a new workspace directory.

        Resolves the Git repository for the new directory, refreshes the
        repository/branch label and toggles the branch-switch button so it
        never dereferences a stale or missing repository handle.

        Args:
            directory: Absolute path of the active solution/workspace.
        """
        self.currentDirectory = directory
        self.repository = return_repository(directory) if directory else None
        self._branch_menu_no_repo_notified = False
        self.repoActions.setText(f"   {self.get_repo_name()} | {self.get_branch()}")
        self.repoActions.adjustSize()
        self.repoActions.setEnabled(True)

    def get_branch(self):
        """
        Returns the repo branch currently working on.
        """
        if self.repository:
            try:
                return self.repository.active_branch.name
            except Exception as exc:
                try:
                    head = getattr(self.repository, "head", None)
                    if head is not None and getattr(head, "is_detached", False):
                        return "DETACHED"
                except Exception:
                    pass
                logger.debug("Branch lookup failed: %s", exc)
                return "UNKNOWN"
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
        if not self.currentDirectory:
            return "No Repo"
        try:
            return os.path.basename(os.path.abspath(self.currentDirectory))
        except Exception:
            return "No Repo"

    def show_branches_menu(self):
        """Spawns a QMenu with all available branches.

        Guards against a missing repository: when the workspace is not a
        Git repository the menu is replaced by a single informational
        action instead of dereferencing ``None``.
        """
        menu = QMenu(self)

        if self.repository is None:
            if not self._branch_menu_no_repo_notified:
                self._branch_menu_no_repo_notified = True
                from editor.utils.notifications.notification_manager import (
                    get_notification_manager,
                )

                try:
                    get_notification_manager().add_warning(
                        "Not a Git Repository",
                        "The current solution is not a Git repository, "
                        "so branch switching is unavailable.",
                        "Git",
                    )
                except Exception:
                    pass
            no_repo_action = QAction("Not a Git Repository", self)
            no_repo_action.setEnabled(False)
            menu.addAction(no_repo_action)
            menu_height = menu.sizeHint().height()
            global_pos = self.repoActions.mapToGlobal(QPoint(0, -menu_height))
            menu.exec(global_pos)
            return

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
            from editor.utils.notifications.notification_manager import (
                get_notification_manager,
            )
        except Exception:
            get_notification_manager = None  # type: ignore
        if self.repository is None:
            if get_notification_manager is not None:
                get_notification_manager().add_error(
                    "Branch Switch",
                    "Cannot switch branch: no repository is open.",
                    source="StatusBar",
                )
            return
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

            if get_notification_manager is not None:
                get_notification_manager().add_success(
                    "Branch Switch",
                    f"Successfully switched to {branch_name}.",
                    source="StatusBar",
                )

        except Exception as e:
            if get_notification_manager is not None:
                get_notification_manager().add_error(
                    "Branch Switch",
                    f"Failed to switch branch: {e}",
                    source="StatusBar",
                )
