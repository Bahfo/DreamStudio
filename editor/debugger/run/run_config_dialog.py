"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Dialog for creating and editing DreamStudio run configurations
(File Path, First Argument, Parameters) consumed by `ConfigRun`.
"""

import os
import shlex
import sys

from editor import *


def parse_parameters(text: str) -> list[str]:
    """Split a raw parameters string into separate command-line arguments.

    Args:
        text: Raw parameters input, e.g. ``--verbose --port 8080``.

    Returns:
        A list of individual parameter strings (empty when blank).

    Raises:
        ValueError: If the text uses unbalanced quoting that cannot be
          tokenized into arguments.
    """
    text = (text or "").strip()
    if not text:
        return []
    try:
        return shlex.split(text, posix=(sys.platform != "win32"))
    except ValueError as exc:
        raise ValueError(f"Invalid parameter quoting: {exc}") from exc


class RunConfigDialog(QDialog):
    """Modal editor for a single run configuration.

    Produces a plain dict compatible with the `ConfigRun` JSON format:
    ``config_name``, ``file_path``, ``Arg``, ``Parameters``.
    """

    def __init__(self, parent=None, initial: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Configure Run Options")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setFixedWidth(460)

        initial = initial or {}
        self._build_ui(initial)
        self._apply_styles()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, initial: dict) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Configure Run Options")
        title.setObjectName("runConfigTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_edit = QLineEdit(str(initial.get("config_name", "") or ""))
        self.name_edit.setPlaceholderText("My Python Script")
        form.addRow("Config Name", self.name_edit)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self.path_edit = QLineEdit(str(initial.get("file_path", "") or ""))
        self.path_edit.setPlaceholderText("/full/path/to/target_file")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_btn)
        form.addRow("File Path (Full)", path_row)

        self.arg_edit = QLineEdit(str(initial.get("Arg", "") or sys.executable))
        self.arg_edit.setPlaceholderText("python3, node, gcc, custom-executable")
        form.addRow("First Argument", self.arg_edit)

        self.params_edit = QLineEdit(" ".join(initial.get("Parameters", []) or []))
        self.params_edit.setPlaceholderText("--verbose --port 8080")
        form.addRow("Parameters", self.params_edit)

        layout.addLayout(form)

        self.error_label = QLabel()
        self.error_label.setObjectName("runConfigError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch()

        cancel_btn = QPushButton("CANCEL")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("SAVE")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        buttons_row.addWidget(cancel_btn)
        buttons_row.addWidget(save_btn)

        layout.addLayout(buttons_row)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QDialog { background-color: #2B2B2B; border: 1px solid #444444; }
            QLabel { color: #BBBBBB; }
            #runConfigTitle { font-weight: bold; font-size: 15px; }
            #runConfigError { color: #E06C75; }
            QLineEdit { background-color: #1E1E1E; color: #DDDDDD;
                        border: 1px solid #444444; border-radius: 4px;
                        padding: 5px; }
            QPushButton { background-color: #3A3A3A; color: #DDDDDD;
                          border: 1px solid #555555; border-radius: 4px;
                          padding: 6px 14px; }
            QPushButton:hover { background-color: #555555; }
            """
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_file(self) -> None:
        """Open a native file picker and fill the File Path (Full) field."""
        start_dir = os.path.dirname(self.path_edit.text()) or os.getcwd()
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Select Target File", start_dir
        )
        if chosen:
            self.path_edit.setText(chosen)

    def _on_save(self) -> None:
        """Validate the fields and accept the dialog when valid."""
        try:
            self.get_config()
        except ValueError as exc:
            self.error_label.setText(str(exc))
            self.error_label.show()
            return
        self.accept()

    def get_config(self) -> dict:
        """Collect and validate the dialog fields.

        Returns:
            A dict in the `ConfigRun` format: ``config_name``,
            ``file_path``, ``Arg``, ``Parameters`` (argv list).

        Raises:
            ValueError: When required fields are missing or the
              parameters string cannot be tokenized.
        """
        name = self.name_edit.text().strip() or "dsconfig"
        file_path = self.path_edit.text().strip()
        first_arg = self.arg_edit.text().strip()

        if not file_path:
            raise ValueError("File Path (Full) is required.")
        if not first_arg:
            raise ValueError("First Argument is required.")

        return {
            "config_name": name,
            "file_path": file_path,
            "Arg": first_arg,
            "Parameters": parse_parameters(self.params_edit.text()),
        }
