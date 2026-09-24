"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Solution start window shown before the DreamStudio main window boots.
"""

import os

from editor import *

from editor.utils.solution.QDreamDialog import CreateSolutionDialog
from editor.utils.solution.manifests_scanner import scan_project_types
from editor.utils.solution.recent_projects_scanner import add_or_update, list_recent
from editor.utils.solution.solution_marker import (
    is_solution_dir,
    read_solution,
    write_solution,
)
from editor.utils.solution.theme import apply_theme, center_on_screen, inherit_theme

_START_WINDOW_TITLE = "Welcome to DreamStudio"


class SolutionStartWindow(QMainWindow):
    solution_selected = pyqtSignal(object)
    prompt_cancelled = pyqtSignal()

    def __init__(self, registry=None) -> None:
        super().__init__()
        self._registry = registry
        self._choice_made = False
        self._selection: dict = {}

        self.setWindowTitle(_START_WINDOW_TITLE)
        self.setMinimumSize(760, 480)

        self._build_ui()
        self._load_intro_settings()
        if not apply_theme(self, self._registry):
            self._apply_style()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._pages = QStackedWidget(central)
        self._pages.addWidget(self._build_create_page())
        self._pages.addWidget(self._build_open_page())

        root.addWidget(self._build_sidebar(), 0)
        root.addWidget(self._pages, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        brand = QLabel("DreamStudio")
        brand.setObjectName("BrandLabel")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setContentsMargins(0, 18, 0, 12)

        self._nav_list = QListWidget(sidebar)
        self._nav_list.setObjectName("NavList")
        self._nav_list.addItem("Create a New Solution")
        self._nav_list.addItem("Open an Existing Solution")
        self._nav_list.setCurrentRow(0)
        self._nav_list.setFrameShape(QFrame.Shape.NoFrame)
        self._nav_list.currentRowChanged.connect(self._pages.setCurrentIndex)

        layout.addWidget(brand)
        layout.addWidget(self._nav_list)
        layout.addStretch(1)
        return sidebar

    def _build_create_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(10)
        self._create_pages = QStackedWidget(page)
        self._create_pages.addWidget(self._build_project_type_list())
        self._create_pages.addWidget(self._build_empty_state())
        layout.addWidget(self._create_pages, 1)
        return page

    def _build_project_type_list(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel("Start a new project")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        hint = QLabel("Pick a project type to create a new solution from a template.")
        hint.setObjectName("PageHint")
        layout.addWidget(hint)

        self._project_types_list = QListWidget(widget)
        self._project_types_list.setObjectName("ProjectTypesList")
        layout.addWidget(self._project_types_list, 1)

        self._project_types = scan_project_types()
        for entry in self._project_types:
            item = QListWidgetItem(entry["display_name"])
            item.setData(Qt.ItemDataRole.UserRole, self._project_types_list.count())
            item.setToolTip(entry["description"])
            self._project_types_list.addItem(item)

        meta_row = QHBoxLayout()
        self._type_description = QLabel("Select a project type to see its description.")
        self._type_description.setObjectName("DescriptionLabel")
        self._type_description.setWordWrap(True)
        meta_row.addWidget(self._type_description, 1)

        self._next_btn = QPushButton("Next")
        self._next_btn.setObjectName("PrimaryButton")
        self._next_btn.clicked.connect(self._start_create_for_selected)
        meta_row.addWidget(self._next_btn)

        layout.addLayout(meta_row)

        if self._project_types:
            self._project_types_list.setCurrentRow(0)
            self._create_pages.setCurrentIndex(0)
        else:
            self._create_pages.setCurrentIndex(1)

        self._project_types_list.currentRowChanged.connect(
            self._refresh_type_description
        )
        self._project_types_list.itemDoubleClicked.connect(
            lambda _item: self._start_create_for_selected()
        )
        return widget

    def _build_empty_state(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.addStretch(1)
        label = QLabel(
            "No project templates were found.\nManifests may have been deleted."
        )
        label.setObjectName("DescriptionLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addStretch(1)
        return widget

    def _build_open_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(6)

        title = QLabel("Open an existing solution")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        hint = QLabel("Reopen a recently used solution or browse for a folder.")
        hint.setObjectName("PageHint")
        layout.addWidget(hint)

        self._recent_list = QListWidget(page)
        self._recent_list.setObjectName("RecentList")
        self._recent_list.itemDoubleClicked.connect(self._open_recent_item)
        layout.addWidget(self._recent_list, 1)

        self._recent_list.itemActivated.connect(self._open_recent_item)

        self._browse_btn = QPushButton("Browse for folder...")
        self._browse_btn.setObjectName("PrimaryButton")
        self._browse_btn.clicked.connect(self._browse_open)
        layout.addWidget(self._browse_btn, 0, Qt.AlignmentFlag.AlignRight)
        return page

    def _load_intro_settings(self) -> None:
        last = self._last_directory()
        paths_in_recent = []

        for record in list_recent():
            path = record.get("path", "")
            paths_in_recent.append(path)
            item = QListWidgetItem(os.path.basename(path.rstrip(os.sep)) or path)
            item.setText(
                f"{record.get('name') or os.path.basename(path.rstrip(os.sep))}\n{path}"
            )
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self._recent_list.addItem(item)

        if not paths_in_recent:
            self._recent_list.addItem("No recent solutions yet.")
            self._recent_list.item(0).setFlags(Qt.ItemFlag.NoItemFlags)

        if last:
            for index in range(self._recent_list.count()):
                row_path = self._recent_list.item(index).data(Qt.ItemDataRole.UserRole)
                if row_path == last:
                    self._recent_list.setCurrentRow(index)
                    self._nav_list.setCurrentRow(1)
                    break

    def _last_directory(self) -> str:
        try:
            config = self._registry.get("config") if self._registry else {}
            return (config.get("workspace") or {}).get("last_directory", "")
        except Exception:
            return ""

    def set_tab(self, index: int) -> None:
        """Select the given landing tab without changing the main window.

        Args:
            index: 0 for *Create*, 1 for *Open*.
        """
        self._nav_list.setCurrentRow(index)
        self._pages.setCurrentIndex(index)

    def _refresh_type_description(self, row: int) -> None:
        if 0 <= row < len(self._project_types):
            self._type_description.setText(self._project_types[row]["description"])

    def _selected_project_entry(self) -> dict:
        row = self._project_types_list.currentRow()
        if not (0 <= row < len(self._project_types)):
            return {}
        return self._project_types[row]

    def _start_create_for_selected(self) -> None:
        entry = self._selected_project_entry()
        if not entry:
            return
        dialog = CreateSolutionDialog(self, project_entry=entry)
        if dialog.exec() == CreateSolutionDialog.DialogCode.Accepted:
            if not dialog.result_data:
                return
            data = dict(dialog.result_data)
            scaffold = {
                "target": data["path"],
                "name": data["name"],
                "project_type": data["project_type"],
                "manifest_path": data["manifest_path"],
            }
            self._emit_selection(data, scaffold)

    def _open_recent_item(self, item) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self._open_solution(path)

    def _browse_open(self) -> None:
        start = self._last_directory() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Solution Folder", start)
        if folder:
            self._open_solution(folder)

    def _message_box(
        self, icon, title, text, buttons=QMessageBox.StandardButton.Ok
    ) -> QMessageBox:

        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(buttons)
        inherit_theme(box)
        center_on_screen(box)
        return box

    def _open_solution(self, path: str) -> None:
        absolute = os.path.abspath(path)
        if not os.path.isdir(absolute):
            self._message_box(
                QMessageBox.Icon.Warning,
                "Folder unavailable",
                f"The folder no longer exists:\n{absolute}",
            ).exec()
            return

        project_type = "directory"
        name = os.path.basename(absolute.rstrip(os.sep)) or absolute
        if is_solution_dir(absolute):
            try:
                marker = read_solution(absolute)
                project_type = marker.get("project_type") or project_type
                name = marker.get("name") or name
            except Exception:
                pass
        else:
            try:
                write_solution(
                    absolute, name=name, project_type=project_type, manifest=""
                )
            except OSError:
                pass

        try:
            add_or_update(absolute, name=name, project_type=project_type)
        except Exception:
            pass

        self._emit_selection(
            {"path": absolute, "name": name, "project_type": project_type}, None
        )

    def _emit_selection(self, data: dict, scaffold) -> None:
        selection = {
            "path": data["path"],
            "name": data.get("name", ""),
            "project_type": data.get("project_type", ""),
            "_scaffold": scaffold,
        }
        self._choice_made = True
        self._selection = selection
        self.solution_selected.emit(selection)

    def closeEvent(self, event) -> None:
        """Emit ``prompt_cancelled`` when dismissed without a selection."""
        if not self._choice_made:
            self.prompt_cancelled.emit()
        super().closeEvent(event)


def _complete_selection(result: dict, selection: dict, loop) -> None:
    result["selection"] = selection
    result["scaffold"] = (
        selection.get("_scaffold") if isinstance(selection, dict) else None
    )
    loop.quit()


def run_start_window_selection(window) -> tuple:
    from PyQt6.QtCore import QEventLoop

    result: dict = {}
    loop = QEventLoop()
    window.solution_selected.connect(
        lambda selection: _complete_selection(result, selection, loop)
    )
    window.prompt_cancelled.connect(loop.quit)
    window.showMaximized()
    window.setEnabled(True)
    loop.exec()
    try:
        window.close()
        window.deleteLater()
    except Exception:
        pass
    return result.get("selection"), result.get("scaffold")
