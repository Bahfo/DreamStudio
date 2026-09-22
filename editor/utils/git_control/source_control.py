from editor import *
from editor.utils.resource_path import resource_path

from editor.utils.panel_shell import PanelShell
from editor.utils.git_control.commit_history import GitGraph, compute_commit_graph
from editor.utils.git_control.status_service import get_status_service
from editor.widgets.QToolBox import ExplorerToolbar, ToolbarButton
from editor.utils.git_control.commit_text import ExpandingTextEdit
import editor.utils.git_control.git_control as git_control


class GitCommitHistory(QFrame):
    """
    Component for viewing Git log details formatted as a structured tree table.
    """

    _PAGE_SIZE = 25
    _MAX_COMMITS = 500
    _ITEM_HEIGHT = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo = None
        self._branch = "main"
        self._head_sha = None
        self._all_commits = []
        self._display_start = 0
        self._display_end = 0
        self._loading = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(2)
        self.tree.setIndentation(4)
        self.tree.setRootIsDecorated(False)
        self.tree.setAnimated(True)
        self.tree.setTextElideMode(Qt.TextElideMode.ElideNone)

        hdr = self.tree.header()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(1, 100)

        self._main_layout.addWidget(self.tree)
        self.tree.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def set_repo(self, repo):
        self._repo = repo
        self.refresh()

    def _load_history(self):
        self.tree.clear()
        self._all_commits = []
        self._display_start = 0
        self._display_end = 0

        if self._repo is None:
            return

        try:
            data = git_control.get_commit_history(self._repo, self._MAX_COMMITS)
        except Exception:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, "Failed to load history")
            return

        commits = data.get("commits", [])
        self._head_sha = data.get("head_sha")
        self._branch = data.get("branch", "main")

        if not commits:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, "No commits found")
            return

        self._all_commits = commits[: self._MAX_COMMITS]
        self._display_start = 0
        self._display_end = min(self._PAGE_SIZE, len(self._all_commits))

        for i in range(self._display_start, self._display_end):
            c = self._all_commits[i]
            item = self._create_item(c, i)
            self.tree.addTopLevelItem(item)

    def _create_item(self, c: object, idx: int) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        short_hash = c.hexsha[:7]
        msg = c.message.split("\n")[0] if c.message else "(no message)"
        is_head = c.hexsha == self._head_sha

        marker = "◉" if is_head else "○"
        display = f"{marker}  {short_hash}  {msg}"
        item.setText(0, display)
        item.setData(0, Qt.ItemDataRole.UserRole, c.hexsha)
        item.setToolTip(0, self._build_rich_tooltip(c))

        if is_head:
            item.setText(1, f"({self._branch})")
            item.setTextAlignment(
                1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

        return item

    def _build_rich_tooltip(self, commit) -> str:
        author = commit.author.name if commit.author else "unknown"
        email = commit.author.email if commit.author else ""
        auth_date = QDateTime.fromSecsSinceEpoch(commit.authored_date).toString(
            "yyyy-MM-dd hh:mm:ss"
        )
        msg = commit.message.strip() if commit.message else "(no message)"
        sha = commit.hexsha

        if commit.parents:
            parents_str = ", ".join(p.hexsha[:7] for p in commit.parents)
        else:
            parents_str = "(none)"

        return (
            f"Commit: {sha}\n"
            f"Author: {author} <{email}>\n"
            f"Date: {auth_date}\n"
            f"Parents: {parents_str}\n\n"
            f"{msg}"
        )

    def _on_scroll(self, value):
        if self._loading:
            return
        self._loading = True

        sb = self.tree.verticalScrollBar()
        near_bottom = sb.maximum() - value < 40
        near_top = value - sb.minimum() < 40

        if near_bottom and self._display_end < len(self._all_commits):
            self._load_next_batch(sb)
        elif near_top and self._display_start > 0:
            self._load_prev_batch(sb)

        self._loading = False

    def _load_next_batch(self, sb):
        count = min(self._PAGE_SIZE, len(self._all_commits) - self._display_end)
        for i in range(self._display_end, self._display_end + count):
            self.tree.addTopLevelItem(self._create_item(self._all_commits[i], i))
        self._display_end += count

    def _load_prev_batch(self, sb):
        count = min(self._PAGE_SIZE, self._display_start)
        for i in range(self._display_start - 1, self._display_start - count - 1, -1):
            self.tree.insertTopLevelItem(0, self._create_item(self._all_commits[i], i))
        self._display_start -= count

        sb.blockSignals(True)
        new_val = max(sb.minimum(), sb.value() - count * self._ITEM_HEIGHT)
        sb.setValue(new_val)
        sb.blockSignals(False)

    def refresh(self):
        self._loading = True
        self._load_history()
        self._loading = False


class GitVersionControl(PanelShell):
    """
    Main source control panel displaying status, commit logs, and branches.
    """

    TITLE_TEXT = "Source Control"

    def __init__(self, parent=None):
        self._repo = None
        self._root_path = ""
        self._all_checked = True
        super().__init__(parent)
        self._setup_focus_tracking()

    def _build_shell(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)

        self._frame = QFrame(self)
        self._frame_layout = QVBoxLayout(self._frame)
        self._main_layout.addWidget(self._frame)

        self._build_header_row()

        self._toolbar_row = QHBoxLayout()
        self._status_label = QLabel("Branch: --")
        self._toolbar_row.addWidget(self._status_label)
        self._toolbar_row.addStretch(1)

        self._explr_toolbox = ExplorerToolbar()
        self._toolbar_row.addLayout(self._explr_toolbox)
        self._frame_layout.addLayout(self._toolbar_row)

        self.view_stack = QStackedWidget(self)
        self._build_init_page()
        self._build_workspace_page()
        self._frame_layout.addWidget(self.view_stack)

    def _header_right_widgets(self) -> list[QWidget]:
        return [
            ToolbarButton(
                resource_path("editor/utils/explorer/assets/icons/dropdown.png"),
                "Options",
                (20, 20),
                (15, 15),
            ),
        ]

    def _build_init_page(self) -> None:
        init_page = QWidget()
        layout = QVBoxLayout(init_page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("No Repository Detected")
        desc = QLabel(
            "Track and monitor workspace history by initializing a Git repository."
        )
        desc.setWordWrap(True)

        init_btn = QPushButton("Initialize Repository")
        init_btn.clicked.connect(self._action_git_init)

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addWidget(init_btn, 0, Qt.AlignmentFlag.AlignCenter)

        self.view_stack.addWidget(init_page)

    def _build_workspace_page(self) -> None:
        workspace_page = QWidget()
        layout = QVBoxLayout(workspace_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        tab_nav_layout = QHBoxLayout()
        tab_nav_layout.setContentsMargins(0, 0, 0, 0)
        tab_nav_layout.setSpacing(4)

        self.btn_status = QPushButton("Status")
        self.btn_history = QPushButton("History")
        self.btn_branches = QPushButton("Branches")

        tab_nav_layout.addWidget(self.btn_status)
        tab_nav_layout.addWidget(self.btn_history)
        tab_nav_layout.addWidget(self.btn_branches)
        tab_nav_layout.addStretch()
        layout.addLayout(tab_nav_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.workspace_stack = QStackedWidget(self)
        splitter.addWidget(self.workspace_stack)

        commit_side_panel = QWidget()
        commit_side_layout = QVBoxLayout(commit_side_panel)
        commit_side_layout.setContentsMargins(0, 4, 0, 0)
        commit_side_layout.setSpacing(6)

        self.commit_input = ExpandingTextEdit()
        self.commit_btn = QPushButton("Commit Changes")
        self.commit_btn.clicked.connect(self._do_commit)

        self.commit_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 7px 14px;
                border-radius: 4px;}
            QPushButton:hover {background-color: #106ebe;}
            QPushButton:pressed {background-color: #005a9e;}
        """)

        commit_side_layout.addWidget(self.commit_input, 1)
        commit_side_layout.addWidget(self.commit_btn, 0)
        commit_side_panel.setMinimumWidth(200)

        splitter.addWidget(commit_side_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.btn_status.clicked.connect(lambda: self.workspace_stack.setCurrentIndex(0))
        self.btn_history.clicked.connect(
            lambda: self.workspace_stack.setCurrentIndex(1)
        )
        self.btn_branches.clicked.connect(
            lambda: self.workspace_stack.setCurrentIndex(2)
        )

        self._build_status_tab()
        self._build_history_tab()
        self._build_branches_tab()

        self.view_stack.addWidget(workspace_page)

    def _build_status_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        toolbar_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh)
        self.check_all_btn = QPushButton("Toggle Check")
        self.check_all_btn.clicked.connect(self._toggle_check_all)
        self.expand_btn = QPushButton("Expand All")
        self.expand_btn.clicked.connect(self._expand_all)
        self.collapse_btn = QPushButton("Collapse All")
        self.collapse_btn.clicked.connect(self._collapse_all)

        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.check_all_btn)
        toolbar_layout.addWidget(self.expand_btn)
        toolbar_layout.addWidget(self.collapse_btn)
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(20)
        layout.addWidget(self.tree, 1)

        self.workspace_stack.addWidget(page)

    def _build_history_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        history_title = QLabel("Commit History Logs")
        self.menu_btn = QPushButton("...")
        self.menu_btn.setFixedWidth(30)
        self.menu_btn.clicked.connect(self._show_history_options_menu)

        header_layout.addWidget(history_title)
        header_layout.addStretch()
        header_layout.addWidget(self.menu_btn)
        layout.addLayout(header_layout)

        self.history_stack = QStackedWidget(self)
        layout.addWidget(self.history_stack)

        self.commit_history = GitCommitHistory(self)
        self.history_stack.addWidget(self.commit_history)

        self.graph_view = GitGraph(self)
        self.history_stack.addWidget(self.graph_view)

        self.workspace_stack.addWidget(page)

    def _build_branches_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        placeholder = QLabel("Branch workspace settings are coming soon.")
        placeholder.setStyleSheet("color: #888888;")
        layout.addWidget(placeholder)

        self.workspace_stack.addWidget(page)

    def _show_history_options_menu(self) -> None:
        menu = QMenu(self)
        action_table = QAction("History Table", self)
        action_graph = QAction("History Graph", self)

        action_table.triggered.connect(lambda: self.history_stack.setCurrentIndex(0))
        action_graph.triggered.connect(lambda: self.history_stack.setCurrentIndex(1))

        menu.addAction(action_table)
        menu.addAction(action_graph)
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def set_workspace(self, root_path: str) -> None:
        self._root_path = os.path.abspath(root_path)
        self._refresh()
        get_status_service().set_root(root_path)

    def _refresh(self) -> None:
        if not self._root_path:
            return

        repo_result = git_control.return_repository(self._root_path)
        if isinstance(repo_result, Exception) or repo_result is None:
            self._repo = None
            self._status_label.setText("Branch: Uninitialized")
            self.view_stack.setCurrentIndex(0)
        else:
            self._repo = repo_result
            self.view_stack.setCurrentIndex(1)
            self._load_changed_files()
            self.commit_history.set_repo(self._repo)

            try:
                history_data = git_control.get_commit_history(self._repo)
                commits = history_data.get("commits", [])
                processed_commits = compute_commit_graph(commits)
                self.graph_view.set_commits(processed_commits)

                self._status_label.setText(
                    f"Branch: {history_data.get('branch', 'main')}"
                )
            except Exception:
                self._status_label.setText("Branch: Unknown")

        get_status_service().request_scan("source-control:refresh")

    def _action_git_init(self) -> None:
        if not self._root_path:
            return
        try:
            from git import Repo

            Repo.init(self._root_path)
            self._refresh()
            get_status_service().set_root(self._root_path)
        except Exception:
            pass

    def _load_changed_files(self):
        self.tree.clear()
        if self._repo is None:
            self.tree.setColumnCount(1)
            return

        try:
            files = git_control.get_changed_files(self._repo)
        except Exception:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, "Error reading git changes")
            return

        if not files:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, "No changes detected")
            return

        self.tree.setColumnCount(2)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        modified = [f for f in files if f["status"] in ("M", "S", "R")]
        deleted = [f for f in files if f["status"] == "D"]
        added = [f for f in files if f["status"] in ("U", "A")]

        if modified:
            self._create_parent_category("Changes", modified)
        if deleted:
            self._create_parent_category("Deleted", deleted)
        if added:
            self._create_parent_category("Added", added)

    def _create_parent_category(self, title: str, files: list):
        parent = QTreeWidgetItem(self.tree)
        parent.setText(0, f"{title} ({len(files)})")
        parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        parent.setExpanded(True)
        for f in files:
            self._add_file_child(parent, f)

    def _add_file_child(self, parent: QTreeWidgetItem, file_info: dict):
        item = QTreeWidgetItem(parent)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)

        path = file_info["path"]
        additions = file_info.get("additions", 0)
        deletions = file_info.get("deletions", 0)

        name = os.path.basename(path)
        dir_part = os.path.dirname(path)

        if dir_part:
            display_text = f"{name}  [{dir_part}]"
        else:
            display_text = name

        item.setText(0, display_text)

        changes_text = ""
        if additions > 0:
            changes_text += f"+{additions}"
        if deletions > 0:
            if changes_text:
                changes_text += f" -{deletions}"
            else:
                changes_text += f"-{deletions}"

        if changes_text:
            item.setText(1, changes_text)
            item.setTextAlignment(
                1,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )

        item.setData(0, Qt.ItemDataRole.UserRole, path)

    def _expand_all(self):
        self.tree.expandAll()

    def _collapse_all(self):
        self.tree.collapseAll()

    def _toggle_check_all(self):
        self._all_checked = not self._all_checked
        state = Qt.CheckState.Checked if self._all_checked else Qt.CheckState.Unchecked
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                child.setCheckState(0, state)

    def _do_commit(self):
        message = self.commit_input.toPlainText().strip()
        if not message:
            return

        checked_files = self._get_checked_files()
        if not checked_files or not self._repo:
            return

        success, msg = git_control.commit_staged(self._repo, message, checked_files)
        get_status_service().request_scan("source-control:commit")
        if success:
            self.commit_input.clear()
            self._refresh()

    def _get_checked_files(self) -> list[str]:
        files = []
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    path = child.data(0, Qt.ItemDataRole.UserRole)
                    if path:
                        files.append(path)
        return files

    def _setup_focus_tracking(self) -> None:
        QApplication.instance().focusChanged.connect(self._on_app_focus_changed)

    def _on_app_focus_changed(self, old, new) -> None:
        focused = False
        if new is not None:
            w = new
            while w is not None:
                if w is self:
                    focused = True
                    break
                try:
                    w = w.parent()
                except (TypeError, RuntimeError):
                    break
        self._set_frame_focused(focused)

    def _set_frame_focused(self, focused: bool) -> None:
        self._frame.setProperty("focused", focused)
        self._frame.style().unpolish(self._frame)
        self._frame.style().polish(self._frame)
