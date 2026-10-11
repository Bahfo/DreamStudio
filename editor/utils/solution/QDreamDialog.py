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

from editor import *

from editor.utils.solution.dialogs import ask_yes_no, themed_box
from editor.utils.solution.solution_marker import ensure_solution_marker
from editor.utils.solution.theme import (
    center_on_screen_show,
    inherit_theme,
    load_dialog_qss,
)

_DIALOG_MIN_WIDTH = 520


class CreateSolutionDialog(QDialog):
    """Collect a solution name and location for the chosen template.

    Attributes:
        result_data: Creation result dict after an accepted dialog.
    """

    def __init__(self, parent=None, project_entry=None) -> None:
        """Build the dialog for *project_entry*.

        Args:
            parent: Parent widget to inherit the theme from.
            project_entry: Manifest entry the solution is created from.
        """
        super().__init__(parent)
        self._project_entry = project_entry or {}
        self.result_data: dict = {}

        self.setWindowTitle("Create a New Solution")
        self.setMinimumWidth(_DIALOG_MIN_WIDTH)
        self.setModal(True)

        self._build_ui()

        if not inherit_theme(self):
            self.setStyleSheet(load_dialog_qss())

    def showEvent(self, event) -> None:
        """Center the dialog on the screen each time it is shown."""
        center_on_screen_show(self, event)

    def _build_ui(self) -> None:
        """Create the name, location and confirmation widgets."""
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
        """Build a heading label for *text*.

        Args:
            text: Heading content.

        Returns:
            Configured label.
        """
        label = QLabel(text)
        label.setObjectName("HeadingLabel")
        return label

    def _label(self, text: str) -> QLabel:
        """Build a field label for *text*.

        Args:
            text: Label content.

        Returns:
            Configured label.
        """
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    def _choose_location(self) -> None:
        """Let the user pick the parent folder for the new solution."""
        start_dir = self._location_input.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self, "Select Project Location", start_dir
        )
        if folder:
            self._location_input.setText(folder)

    def _validate_and_accept(self) -> None:
        """Validate inputs, write the marker and accept the dialog."""
        name = self._name_input.text().strip()
        location = os.path.expanduser(self._location_input.text().strip())
        project_entry = self._project_entry or {}

        if not name:
            themed_box(
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
                themed_box(
                    self,
                    QMessageBox.Icon.Warning,
                    "Invalid name",
                    "The solution name contains invalid characters.",
                ).exec()
                return

        target = os.path.join(location, name)
        if os.path.exists(target) and any(os.scandir(target)):
            if not ask_yes_no(
                self,
                "Directory not empty",
                f"'{target}' already exists and is not empty.\n\nOpen it anyway?",
            ):
                return
        else:
            try:
                os.makedirs(target, exist_ok=True)
            except OSError as exc:
                themed_box(
                    self,
                    QMessageBox.Icon.Critical,
                    "Creation failed",
                    f"Could not create the folder:\n{exc}",
                ).exec()
                return

        project_type = project_entry.get("project_type", "directory")
        try:
            ensure_solution_marker(
                target,
                name=name,
                project_type=project_type,
                manifest=project_entry.get("manifest_path", ""),
            )
        except OSError as exc:
            themed_box(
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
        """Ensure *location* exists and return it, warning when empty.

        Args:
            location: Raw location text from the input field.

        Returns:
            The ensured directory, or ``""`` when no location was given.
        """
        if not location:
            themed_box(
                self,
                QMessageBox.Icon.Warning,
                "Missing location",
                "Please choose a location.",
            ).exec()
            return ""
        os.makedirs(location, exist_ok=True)
        return location
