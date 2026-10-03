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

_WINDOW_WIDTH = 1040
_WINDOW_HEIGHT = 680


class ProjectCard(QFrame):
    """Visual project-template card used by the solution picker."""

    clicked = pyqtSignal(object)
    double_clicked = pyqtSignal(object)

    def __init__(self, project_entry: dict, parent=None) -> None:
        super().__init__(parent)

        self.project_entry = project_entry
        self._selected = False

        self.setObjectName("SolutionProjectCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setMinimumHeight(104)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(14)

        icon_frame = QFrame(self)
        icon_frame.setObjectName("SolutionProjectIconFrame")
        icon_frame.setFixedSize(56, 56)

        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(7, 7, 7, 7)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(icon_frame)
        icon_label.setObjectName("SolutionProjectIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(42, 42)

        icon = self._resolve_icon()

        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(QSize(38, 38)))

        icon_layout.addWidget(icon_label)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        name = self.project_entry.get(
            "display_name",
            "Unnamed Project",
        )

        description = self.project_entry.get(
            "description",
            "No description is available for this project template.",
        )

        name_label = QLabel(str(name), self)
        name_label.setObjectName("SolutionProjectName")
        name_label.setWordWrap(True)

        description_label = QLabel(str(description), self)
        description_label.setObjectName("SolutionProjectDescription")
        description_label.setWordWrap(True)
        description_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        content_layout.addWidget(name_label)
        content_layout.addWidget(description_label, 1)

        layout.addWidget(
            icon_frame,
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        layout.addLayout(content_layout, 1)

    def _resolve_icon(self) -> QIcon:
        """Resolve a manifest-provided icon, falling back to a native icon."""
        icon_value = self.project_entry.get("icon")

        if isinstance(icon_value, QIcon):
            return icon_value

        if isinstance(icon_value, str) and icon_value:
            icon_path = icon_value

            if not os.path.isabs(icon_path):
                manifest_path = self.project_entry.get(
                    "manifest_path",
                    "",
                )

                if manifest_path:
                    icon_path = os.path.join(
                        os.path.dirname(manifest_path),
                        icon_path,
                    )

            icon = QIcon(icon_path)

            if not icon.isNull():
                return icon

        return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def set_selected(self, selected: bool) -> None:
        """Update the card selection state."""
        self._selected = selected

        self.setProperty(
            "selected",
            selected,
        )

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_entry)

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.project_entry)

        super().mouseDoubleClickEvent(event)


class SolutionStartWindow(QMainWindow):
    solution_selected = pyqtSignal(object)
    prompt_cancelled = pyqtSignal()

    def __init__(self, registry=None) -> None:
        super().__init__()

        self._registry = registry
        self._choice_made = False
        self._selection: dict = {}
        self._project_types: list[dict] = []
        self._project_cards: list[ProjectCard] = []
        self._project_items: list[QListWidgetItem] = []
        self._selected_project_entry: dict = {}

        self.setObjectName("SolutionStartWindow")
        self.setWindowTitle(_START_WINDOW_TITLE)
        self.setFixedSize(
            _WINDOW_WIDTH,
            _WINDOW_HEIGHT,
        )

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        self._build_ui()
        self._load_intro_settings()

        if apply_theme(self, self._registry):
            self.style().unpolish(self)
            self.style().polish(self)

        self._force_normal_window_state()
        center_on_screen(self)

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("SolutionStartCentral")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setObjectName("SolutionStartRootLayout")
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(
            self._build_recent_panel(),
            0,
        )
        root.addWidget(
            self._build_project_panel(),
            1,
        )

    def _build_recent_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("SolutionRecentPanel")
        panel.setFrameShape(QFrame.Shape.NoFrame)
        panel.setMinimumWidth(270)
        panel.setMaximumWidth(285)

        layout = QVBoxLayout(panel)
        layout.setObjectName("SolutionRecentLayout")
        layout.setContentsMargins(20, 22, 16, 20)
        layout.setSpacing(9)

        brand = QLabel("DreamStudio", panel)
        brand.setStyleSheet("font-size: 30px;")
        brand.setObjectName("SolutionBrandLabel")
        brand.setAlignment(Qt.AlignmentFlag.AlignLeft)

        recent_title = QLabel("Recent Projects", panel)
        recent_title.setObjectName("SolutionRecentTitle")

        recent_hint = QLabel(
            "Open a recently used solution or browse for an existing folder.", panel
        )
        recent_hint.setWordWrap(True)

        self._recent_list = QListWidget(panel)
        self._recent_list.setStyleSheet("background-color: transparent; border: none;")
        self._recent_list.setFrameShape(QFrame.Shape.NoFrame)
        self._recent_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._recent_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self._recent_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._recent_list.itemDoubleClicked.connect(self._open_recent_item)
        self._recent_list.itemActivated.connect(self._open_recent_item)

        self._browse_btn = QPushButton("Browse for Folder...", panel)
        self._browse_btn.setStyleSheet("border: 1px solid #1B69AD")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.clicked.connect(self._browse_open)

        layout.addWidget(brand)
        layout.addSpacing(8)
        layout.addWidget(recent_title)
        layout.addWidget(recent_hint)
        layout.addSpacing(3)
        layout.addWidget(self._recent_list, 1)
        layout.addWidget(self._browse_btn)

        return panel

    def _build_project_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setFrameShape(QFrame.Shape.NoFrame)
        panel.setStyleSheet("background-color: transparent; border: none;")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 23, 28, 21)
        layout.setSpacing(10)

        title = QLabel("Create a New Solution", panel)
        hint = QLabel("Choose a project template and create a new solution.", panel)

        self._search_box = QLineEdit(panel)
        self._search_box.setPlaceholderText("Search projects...")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setMinimumHeight(38)
        self._search_box.textChanged.connect(self._filter_projects)

        filter_row = QHBoxLayout()
        filter_row.setObjectName("SolutionFilterLayout")
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)

        self._language_filter = QComboBox(panel)
        self._language_filter.setPlaceholderText("Search Programming Languages")
        self._language_filter.setStyleSheet("border: 1px solid #CCCCCC")
        self._language_filter.setCurrentIndex(-1)
        self._language_filter.setMinimumHeight(34)

        self._platform_filter = QComboBox(panel)
        self._platform_filter.setPlaceholderText("Select Development Platform")
        self._platform_filter.setStyleSheet("border: 1px solid #CCCCCC")
        self._platform_filter.addItem("Linux Desktop", "linux")
        self._platform_filter.addItem("Raspberry Pi", "raspberry_pi")
        self._platform_filter.addItem("Development SDK", "development_sdk")
        self._platform_filter.setCurrentIndex(-1)
        self._platform_filter.setMinimumHeight(34)

        filter_row.addWidget(self._language_filter, 1)
        filter_row.addWidget(self._platform_filter, 1)

        self._project_list = QListWidget(panel)
        self._project_list.setFrameShape(QFrame.Shape.NoFrame)
        self._project_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._project_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self._project_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._project_list.setSpacing(7)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 6, 0, 0)
        footer.setSpacing(8)

        self._selection_hint = QLabel("Select a project template to continue.", panel)
        self._selection_hint.setObjectName("SolutionSelectionHint")
        self._selection_hint.setWordWrap(True)

        self._create_button = QPushButton("Create Project", panel)
        self._create_button.setStyleSheet("background-color: #1B69AD; color: white;")
        self._create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._create_button.setMinimumHeight(36)
        self._create_button.setEnabled(False)
        self._create_button.clicked.connect(self._start_create_for_selected)

        footer.addWidget(self._selection_hint, 1)
        footer.addWidget(self._create_button)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(4)
        layout.addWidget(self._search_box)
        layout.addLayout(filter_row)
        layout.addWidget(self._project_list, 1)
        layout.addLayout(footer)

        self._populate_project_types()

        return panel

    def _populate_project_types(self) -> None:
        self._project_types = scan_project_types()

        self._project_list.clear()
        self._project_cards.clear()
        self._project_items.clear()

        for entry in self._project_types:
            item = QListWidgetItem(self._project_list)
            item.setData(
                Qt.ItemDataRole.UserRole,
                entry,
            )
            item.setSizeHint(QSize(0, 112))

            card = ProjectCard(
                entry,
                self._project_list,
            )

            card.clicked.connect(self._select_project_entry)
            card.double_clicked.connect(self._select_and_create)

            self._project_list.addItem(item)
            self._project_list.setItemWidget(item, card)

            self._project_items.append(item)
            self._project_cards.append(card)

        if self._project_types:
            self._select_project_by_index(0)
        else:
            self._selection_hint.setText("No project templates were found.")

    def _select_project_by_index(
        self,
        index: int,
    ) -> None:
        if not (0 <= index < len(self._project_items)):
            self._clear_project_selection()
            return

        item = self._project_items[index]
        entry = self._project_types[index]

        if item.isHidden():
            self._clear_project_selection()
            return

        self._project_list.setCurrentItem(item)
        self._select_project_entry(entry)

    def _select_project_entry(
        self,
        entry: dict,
    ) -> None:
        if not entry:
            self._clear_project_selection()
            return

        self._selected_project_entry = entry

        selected_index = -1

        for index, current_entry in enumerate(self._project_types):
            is_selected = current_entry is entry

            self._project_cards[index].set_selected(is_selected)

            if is_selected:
                selected_index = index

        if selected_index >= 0:
            self._project_list.setCurrentRow(selected_index)

        name = entry.get("display_name", "Project")

        self._selection_hint.setText(f"Selected: {name}")
        self._create_button.setEnabled(True)

    def _clear_project_selection(self) -> None:
        self._selected_project_entry = {}

        for card in self._project_cards:
            card.set_selected(False)

        self._project_list.clearSelection()
        self._create_button.setEnabled(False)
        self._selection_hint.setText("Select a project template to continue.")

    def _select_and_create(
        self,
        entry: dict,
    ) -> None:
        self._select_project_entry(entry)
        self._start_create_for_selected()

    def _filter_projects(
        self,
        text: str,
    ) -> None:
        query = text.strip().casefold()
        first_visible_index = -1

        for index, entry in enumerate(self._project_types):
            name = str(
                entry.get(
                    "display_name",
                    "",
                )
            )

            description = str(
                entry.get(
                    "description",
                    "",
                )
            )

            searchable_text = (f"{name}\n{description}").casefold()

            matches = not query or query in searchable_text

            self._project_items[index].setHidden(not matches)

            if matches and first_visible_index < 0:
                first_visible_index = index

        selected_index = -1

        if self._selected_project_entry:
            for index, entry in enumerate(self._project_types):
                if entry is self._selected_project_entry:
                    selected_index = index
                    break

        if selected_index >= 0 and not self._project_items[selected_index].isHidden():
            self._select_project_entry(self._selected_project_entry)
        elif first_visible_index >= 0:
            self._select_project_by_index(first_visible_index)
        else:
            self._clear_project_selection()

    def _load_intro_settings(self) -> None:
        last = self._last_directory()
        paths_in_recent = []

        for record in list_recent():
            path = record.get(
                "path",
                "",
            )

            paths_in_recent.append(path)

            item = QListWidgetItem(self._recent_list)

            name = record.get("name") or os.path.basename(path.rstrip(os.sep)) or path

            item.setText(f"{name}\n{path}")
            item.setData(
                Qt.ItemDataRole.UserRole,
                path,
            )
            item.setToolTip(path)

        if not paths_in_recent:
            item = QListWidgetItem("No recent solutions yet.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._recent_list.addItem(item)

        if last:
            for index in range(self._recent_list.count()):
                item = self._recent_list.item(index)

                row_path = item.data(Qt.ItemDataRole.UserRole)

                if row_path == last:
                    self._recent_list.setCurrentRow(index)
                    break

    def _last_directory(self) -> str:
        try:
            config = self._registry.get("config") if self._registry else {}

            return (config.get("workspace") or {}).get(
                "last_directory",
                "",
            )
        except Exception:
            return ""

    def set_tab(self, index: int) -> None:
        """
        Preserve the existing public API while using
        the new single-view UI.

        Index 0 focuses project creation.
        Index 1 focuses recent projects.
        """
        if index == 1:
            self._recent_list.setFocus()
        else:
            self._search_box.setFocus()

    def _start_create_for_selected(self) -> None:
        entry = self._selected_project_entry

        if not entry:
            return

        dialog = CreateSolutionDialog(
            self,
            project_entry=entry,
        )

        if dialog.exec() != CreateSolutionDialog.DialogCode.Accepted:
            return

        if not dialog.result_data:
            return

        data = dict(dialog.result_data)

        scaffold = {
            "target": data["path"],
            "name": data["name"],
            "project_type": data["project_type"],
            "manifest_path": data["manifest_path"],
        }

        self._emit_selection(
            data,
            scaffold,
        )

    def _open_recent_item(
        self,
        item,
    ) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)

        if path:
            self._open_solution(path)

    def _browse_open(self) -> None:
        start = self._last_directory() or os.path.expanduser("~")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Solution Folder",
            start,
        )

        if folder:
            self._open_solution(folder)

    def _message_box(
        self,
        icon,
        title,
        text,
        buttons=QMessageBox.StandardButton.Ok,
    ) -> QMessageBox:
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(buttons)

        inherit_theme(box)
        center_on_screen(box)

        return box

    def _open_solution(
        self,
        path: str,
    ) -> None:
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
                    absolute,
                    name=name,
                    project_type=project_type,
                    manifest="",
                )
                try:
                    from editor.utils.properties.project_data_engine import (
                        ProjectDataEngine,
                    )

                    ProjectDataEngine(absolute).commit_solution_properties(
                        {"name": name}
                    )
                except Exception:
                    pass
            except OSError:
                pass

        try:
            add_or_update(
                absolute,
                name=name,
                project_type=project_type,
            )
        except Exception:
            pass

        self._emit_selection(
            {
                "path": absolute,
                "name": name,
                "project_type": project_type,
            },
            None,
        )

    def _emit_selection(
        self,
        data: dict,
        scaffold,
    ) -> None:
        selection = {
            "path": data["path"],
            "name": data.get(
                "name",
                "",
            ),
            "project_type": data.get(
                "project_type",
                "",
            ),
            "_scaffold": scaffold,
        }

        self._choice_made = True
        self._selection = selection
        self.solution_selected.emit(selection)

    def _force_normal_window_state(self) -> None:
        """Ensure the picker always starts as a normal fixed-size window."""
        self.setWindowState(
            self.windowState()
            & ~Qt.WindowState.WindowMaximized
            & ~Qt.WindowState.WindowFullScreen
        )
        self.showNormal()

    def showEvent(self, event) -> None:
        """Reassert normal state whenever the window becomes visible."""
        super().showEvent(event)

        self._force_normal_window_state()
        center_on_screen(self)

    def closeEvent(self, event) -> None:
        """Emit prompt_cancelled when dismissed without a selection."""
        if not self._choice_made:
            self.prompt_cancelled.emit()

        super().closeEvent(event)


def _complete_selection(
    result: dict,
    selection: dict,
    loop,
) -> None:
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
        lambda selection: _complete_selection(
            result,
            selection,
            loop,
        )
    )

    window.prompt_cancelled.connect(loop.quit)

    window._force_normal_window_state()
    window.show()
    window.raise_()
    window.activateWindow()
    center_on_screen(window)

    loop.exec()

    try:
        window.close()
        window.deleteLater()
    except Exception:
        pass

    return (
        result.get("selection"),
        result.get("scaffold"),
    )
