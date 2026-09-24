"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Create-solution dialog used by the DreamStudio start window.

The dialog collects a solution name, a project location and confirms the
chosen project type read from the manifest scan. It only writes the folder
structure and the ``.ds/solution.yaml`` marker; actual scaffolding is deferred
until the main window is revealed so the IDE can show a blocking progress box
over the running application.
"""

import datetime
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from editor.utils.solution.solution_marker import write_solution
from editor.utils.solution.theme import (
    center_on_screen,
    center_on_screen_show,
    inherit_theme,
)

_DIALOG_MIN_WIDTH = 520


def _message_box(parent, icon, title, text, buttons=QMessageBox.StandardButton.Ok):
    """Build a themed, screen-centered QMessageBox and return it.

    Args:
        parent: Dialog/window owning the box.
        icon: One of the ``QMessageBox.Icon`` values.
        title: Box title.
        text: Box body text.
        buttons: Standard buttons to offer.

    Returns:
        The fully-configured, centered ``QMessageBox`` instance.
    """
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    inherit_theme(box)
    center_on_screen(box)
    return box


class CreateSolutionDialog(QDialog):
    """Modal form collecting the parameters of a brand-new solution.

    Emits nothing on its own; the caller reads :attr:`result_data` after the
    dialog is accepted.

    Attributes:
        result_data (dict): Populated on accept with ``path``, ``name``,
            ``project_type`` and ``manifest_path`` keys.
    """

    def __init__(self, parent=None, project_entry=None) -> None:
        """Build the create dialog.

        Args:
            parent: Optional parent widget (usually the start window).
            project_entry: A manifest entry dict returned by
                ``manifest_scan.scan_project_types()``.
        """
        super().__init__(parent)
        self._project_entry = project_entry or {}
        self.result_data: dict = {}

        self.setWindowTitle("Create a New Solution")
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)
        self.setModal(True)

        self._build_ui()

        styled = inherit_theme(self)
        if not styled:
            self._apply_style()

    def showEvent(self, event) -> None:
        """Center the dialog on the screen each time it is shown."""
        center_on_screen_show(self, event)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(self._heading("New Solution"))

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Solution name, e.g. MyProject")
        layout.addWidget(self._label("Solution name"))
        layout.addWidget(self._name_input)

        location_row = QHBoxLayout()
        self._location_input = QLineEdit()
        self._location_input.setPlaceholderText(
            os.path.expanduser("~/DreamStudioProjects")
        )
        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._choose_location)
        location_row.addWidget(self._location_input, 1)
        location_row.addWidget(browse_btn)
        layout.addWidget(self._label("Location"))
        layout.addLayout(location_row)

        layout.addWidget(self._label("Project type"))
        type_label = QLabel(self._project_entry.get("display_name", "Unknown"))
        type_label.setObjectName("ProjectTypeLabel")
        layout.addWidget(type_label)

        description = QLabel(self._project_entry.get("description", ""))
        description.setWordWrap(True)
        description.setObjectName("DescriptionLabel")
        layout.addWidget(description)

        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self._create_btn = QPushButton("Create and Open")
        self._create_btn.setObjectName("PrimaryButton")
        self._create_btn.setDefault(True)
        self._create_btn.clicked.connect(self._validate_and_accept)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(self._create_btn)
        layout.addLayout(buttons)

    def _heading(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("HeadingLabel")
        return label

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1e1e2e;
            }
            QLabel#HeadingLabel {
                color: #cdd6f4;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#FieldLabel {
                color: #a6adc8;
                font-size: 12px;
            }
            QLabel#ProjectTypeLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel#DescriptionLabel {
                color: #a6adc8;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                padding: 6px 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                padding: 7px 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
            QPushButton#PrimaryButton {
                background-color: #89b4fa;
                color: #11111b;
                font-weight: bold;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #b4befe;
            }
            """
        )

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def _choose_location(self) -> None:
        start_dir = self._location_input.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self, "Select Project Location", start_dir
        )
        if folder:
            self._location_input.setText(folder)

    def _validate_and_accept(self) -> None:
        name = self._name_input.text().strip()
        location = os.path.expanduser(self._location_input.text().strip())
        project_entry = self._project_entry or {}

        if not name:
            _message_box(
                self,
                QMessageBox.Icon.Warning,
                "Missing name",
                "Please enter a solution name.",
            ).exec()
            return
        location = self._resolve_location(location)
        if not location:
            return

        for char in ("/", "\\", ":", "*", "?", '"', "<", ">", "|"):
            if char in name:
                _message_box(
                    self,
                    QMessageBox.Icon.Warning,
                    "Invalid name",
                    "The solution name contains invalid characters.",
                ).exec()
                return

        target = os.path.join(location, name)
        if os.path.exists(target) and any(os.scandir(target)):
            box = _message_box(
                self,
                QMessageBox.Icon.Question,
                "Directory not empty",
                f"'{target}' already exists and is not empty.\n\nOpen it anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            reply = box.exec()
            if reply != QMessageBox.StandardButton.Yes:
                return
        else:
            try:
                os.makedirs(target, exist_ok=True)
            except OSError as exc:
                _message_box(
                    self,
                    QMessageBox.Icon.Critical,
                    "Creation failed",
                    f"Could not create the folder:\n{exc}",
                ).exec()
                return

        project_type = project_entry.get("project_type", "directory")
        try:
            write_solution(
                target,
                name=name,
                project_type=project_type,
                manifest=project_entry.get("manifest_path", ""),
            )
        except OSError as exc:
            _message_box(
                self,
                QMessageBox.Icon.Critical,
                "Creation failed",
                f"Could not write the solution marker:\n{exc}",
            ).exec()
            return

        self.result_data = {
            "path": target,
            "name": name,
            "project_type": project_type,
            "manifest_path": project_entry.get("manifest_path", ""),
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self.accept()

    def _resolve_location(self, location: str) -> str:
        if not location:
            _message_box(
                self,
                QMessageBox.Icon.Warning,
                "Missing location",
                "Please choose a location.",
            ).exec()
            return ""
        os.makedirs(location, exist_ok=True)
        return location
