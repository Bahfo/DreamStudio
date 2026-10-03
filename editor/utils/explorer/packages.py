from editor import *
from editor.utils.resource_path import resource_path

from editor.widgets.QToolBox import ExplorerToolbar


class DependenciesView(QWidget):
    """An IDE package manager view that displays, searches, installs,
    and uninstalls Python packages within the active workspace venv.
    """

    def __init__(self, parent=None):
        """
        Initializes the view component hierarchy, core layout configurations,
        and data initialization.
        """
        super().__init__(parent)

        self._directory = ""

        _layout = QVBoxLayout(self)
        _layout.setContentsMargins(5, 5, 5, 5)

        self._label = QLabel("Packages Explorer")
        self._label.setStyleSheet("""
            font-size: 12px;""")
        _layout.addWidget(self._label)

        self._toolbar = ExplorerToolbar()
        self._add_btn = self._toolbar.add_button(
            resource_path("assets/menus/add.png"), "Add new package"
        )
        self._del_btn = self._toolbar.add_button(
            resource_path("assets/menus/trash.png"), "Delete package"
        )
        self._ref_btn = self._toolbar.add_button(
            resource_path("assets/menus/restart.png"), "Refresh"
        )
        self._toolbar.addStretch()
        _layout.addLayout(self._toolbar)

        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText("Search packages...")
        self._search_bar.setClearButtonEnabled(True)
        self._search_bar.textChanged.connect(self._filter_packages)
        _layout.addWidget(self._search_bar)

        # Setup Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Package Name", "Version", "Summary"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)

        self.table.verticalHeader().setVisible(False)

        self.table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { border: none; background-color: transparent; }"
        )

        _layout.addWidget(self.table)

        self._add_btn.clicked.connect(self._add_package)
        self._del_btn.clicked.connect(self._delete_package)
        self._ref_btn.clicked.connect(self._refresh_packages)

        self._process = None
        self._load_packages()

    def _load_packages(self):
        """
        Disables sorting, fetches workspace venv distributions dynamically,
        parses metadata, and updates the table structure.
        """
        self.table.setSortingEnabled(False)
        self.table.clearContents()

        dists = self._workspace_distributions()
        self.table.setRowCount(len(dists))

        for row, dist in enumerate(dists):
            name = dist.metadata.get("Name", "Unknown")
            version = dist.metadata.get("Version", "Unknown")
            summary = dist.metadata.get("Summary", "No description available.")

            name_item = QTableWidgetItem(name)
            version_item = QTableWidgetItem(version)
            summary_item = QTableWidgetItem(summary)

            name_item.setData(Qt.ItemDataRole.UserRole, dist)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, version_item)
            self.table.setItem(row, 2, summary_item)

        self.table.setSortingEnabled(True)
        self._filter_packages(self._search_bar.text())

    def _workspace_python(self) -> str:
        """Return workspace venv python, else global python."""
        try:
            from editor.debugger.run.python_resolver import resolve_project_python

            base = self._directory if self._directory else None
            return resolve_project_python(base)
        except Exception:
            return sys.executable

    def _workspace_distributions(self) -> list:
        """List distributions from workspace venv, fallback to IDE env."""
        try:
            python_exe = self._workspace_python()
            if python_exe and os.path.isfile(python_exe):
                import json as _json
                import subprocess as _sp

                proc = _sp.run(
                    [python_exe, "-m", "pip", "list", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=self._directory if self._directory else None,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    entries = _json.loads(proc.stdout)
                    fake = []
                    for entry in entries:
                        name = entry.get("name", "Unknown")
                        version = entry.get("version", "Unknown")
                        meta = {
                            "Name": name,
                            "Version": version,
                            "Summary": "Installed in workspace env.",
                        }
                        holder = type("D", (), {})()
                        holder.metadata = meta
                        fake.append(holder)
                    fake.sort(key=lambda d: str(d.metadata["Name"]).lower())
                    return fake
        except Exception:
            pass
        dists = sorted(
            importlib.metadata.distributions(), key=lambda d: d.metadata["Name"].lower()
        )
        return list(dists)

    def _filter_packages(self, text):
        """
        Filters table row visibilities dynamically based on the package name entry.
        """
        search_string = text.lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                is_match = search_string in item.text().lower()
                self.table.setRowHidden(row, not is_match)

    def _refresh_packages(self):
        """
        Clears search selections and requests a clean re-scan of metadata files.
        """
        self._load_packages()

    def set_workspace(self, path: str) -> None:
        """Update the directory used for pip operations.

        Args:
            path: Absolute path of the active solution/folder.
        """
        if path and os.path.isdir(path):
            self._directory = os.path.abspath(path)
            try:
                self._load_packages()
            except Exception:
                pass

    def _add_package(self):
        """
        Prompts the user for a valid package identity string to supply to pip.
        """
        package_name, ok = QInputDialog.getText(
            self, "Install Package", "Enter package name (e.g., requests, numpy):"
        )
        if ok and package_name.strip():
            self._run_pip_command(["install", package_name.strip()])

    def _delete_package(self):
        """
        Processes row extraction metrics and executes asynchronous package removal
        routines.
        """
        current_row = self.table.currentRow()
        if current_row == -1:
            QMessageBox.warning(
                self, "No Selection", "Please select a package to delete."
            )
            return

        package_item = self.table.item(current_row, 0)
        package_name = package_item.text()

        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to uninstall '{package_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self._run_pip_command(["uninstall", package_name, "-y"])

    def _run_pip_command(self, arguments):
        """
        Spawns an out-of-process system thread to safely execute a pip command
        without freezing the parent application thread loop.
        """
        if self._process and self._process.state() == QProcess.ProcessState.Running:
            QMessageBox.warning(
                self, "Busy", "Another package management process is already running."
            )
            return

        if not self._directory or not os.path.isdir(self._directory):
            QMessageBox.warning(
                self, "No Workspace", "Open a solution folder before managing packages."
            )
            return

        old = self._process
        self._process = QProcess(self)
        if old is not None:
            try:
                old.deleteLater()
            except Exception:
                pass
        python_exe = self._workspace_python()
        full_args = ["-m", "pip"] + arguments

        self.setEnabled(False)
        self._process.finished.connect(self._on_pip_finished)
        self._process.setWorkingDirectory(self._directory)
        self._process.start(python_exe, full_args)

    def _on_pip_finished(self, exit_code, exit_status):
        """
        Handles background process conclusion events, restores input visibility
        patterns, and surfaces diagnostics upon shell failures.
        """
        self.setEnabled(True)
        proc = self._process

        if exit_code == 0:
            self._load_packages()
        else:
            error_msg = ""
            try:
                error_msg = proc.readAllStandardError().data().decode().strip()
            except Exception:
                pass
            QMessageBox.critical(
                self,
                "Process Failed",
                f"Package operation failed.\n\nError details:\n"
                f"{error_msg if error_msg else 'Unknown error.'}",
            )

        self._process = None
        if proc is not None:
            try:
                proc.deleteLater()
            except Exception:
                pass
