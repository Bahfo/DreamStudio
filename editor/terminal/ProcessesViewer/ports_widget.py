"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.
Process and listening-port table for the system monitor.
"""

import psutil

from editor import *

from editor.utils.tools.port_info import fetch_pid_to_ports, service_name

_ACTIVE_STATUSES = {
    psutil.STATUS_RUNNING,
    psutil.STATUS_SLEEPING,
    psutil.STATUS_DISK_SLEEP,
}
_STOPPED_STATUSES = {
    psutil.STATUS_STOPPED,
    psutil.STATUS_TRACING_STOP,
    psutil.STATUS_ZOMBIE,
}


class PortsWidget(QWidget):
    """Process and listening-port table with filtering and process controls."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._bg_color = "#1E1E1E"
        self._fg_color = "#D4D4D4"
        self._grid_color = "#2A2D30"
        self._accent_color = "#61AFEF"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.table_headers = [
            "PID",
            "Process Name",
            "Port(s)",
            "Service",
            "CPU (%)",
            "RAM (MB)",
            "I/O (MB)",
        ]

        top_controls_layout = QHBoxLayout()
        top_controls_layout.setContentsMargins(0, 0, 0, 0)
        top_controls_layout.setSpacing(15)

        self.search_bar = QLineEdit(self)
        self.search_bar.setMaximumWidth(350)
        self.search_bar.setPlaceholderText("Search PID, Name, Port, or Service...")
        self.search_bar.textChanged.connect(self.refresh_data)

        self.sortByDropDown = QComboBox(self)
        self.sortByDropDown.setEditable(True)
        self.sortByDropDown.lineEdit().setReadOnly(True)
        self.sortByDropDown.setMinimumWidth(160)
        options = ["All Processes", "Active Processes", "Stopped Processes"]
        self.sortByDropDown.addItems(options)
        self.sortByDropDown.currentTextChanged.connect(self.refresh_data)
        self.sortByDropDown.lineEdit().textChanged.connect(self.refresh_data)

        self.listen_only_check = QCheckBox("Listening Sockets Only", self)
        self.listen_only_check.setChecked(True)
        self.listen_only_check.toggled.connect(self.refresh_data)

        top_controls_layout.addWidget(self.search_bar)
        top_controls_layout.addWidget(self.sortByDropDown)
        top_controls_layout.addWidget(self.listen_only_check)
        top_controls_layout.addStretch()

        self.table = QTableWidget(0, len(self.table_headers), self)
        self.table.setHorizontalHeaderLabels(self.table_headers)

        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)

        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for i in (0, 2, 3, 4, 5, 6):
            self.table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents
            )

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.verticalHeader().setVisible(False)

        layout.addLayout(top_controls_layout)
        layout.addWidget(self.table)

        self._apply_styles()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(4000)

        self.refresh_data()

    @staticmethod
    def _blend(base: str, other: str, ratio: float) -> str:
        """Blend two hex colours, returning the result as ``#RRGGBB``."""
        first = QColor(base)
        second = QColor(other)
        if not first.isValid():
            first = QColor("#1E1E1E")
        if not second.isValid():
            second = QColor("#D4D4D4")

        ratio = max(0.0, min(1.0, ratio))
        red = round(first.red() + (second.red() - first.red()) * ratio)
        green = round(first.green() + (second.green() - first.green()) * ratio)
        blue = round(first.blue() + (second.blue() - first.blue()) * ratio)
        return QColor(red, green, blue).name()

    def apply_theme(self, bg: str, fg: str, sel: str = "") -> None:
        """Re-colour the process table for the active IDE theme."""
        if QColor(bg).isValid():
            self._bg_color = bg
        if QColor(fg).isValid():
            self._fg_color = fg
        if QColor(sel).isValid() and sel.lower() != self._bg_color.lower():
            self._accent_color = sel
        self._grid_color = self._blend(self._bg_color, self._fg_color, 0.14)
        self._apply_styles()

    def _apply_styles(self) -> None:
        """Apply the current theme palette to the table and controls."""
        alt = self._blend(self._bg_color, self._fg_color, 0.08)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {self._grid_color};
                border-radius: 4px;
                background-color: {self._bg_color};
                alternate-background-color: {alt};
                color: {self._fg_color};
            }}
            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {self._grid_color};
            }}
            QTableWidget::item:selected {{
                background-color: {self._accent_color};
                color: {self._bg_color};
            }}
            QHeaderView::section {{
                background-color: {alt};
                color: {self._fg_color};
                padding: 6px;
                border: none;
                border-bottom: 2px solid {self._grid_color};
                font-weight: bold;
            }}
        """)

        control_style = (
            f"background-color: {alt}; color: {self._fg_color}; "
            f"border: 1px solid {self._grid_color}; padding: 5px; "
            "border-radius: 4px;"
        )
        self.search_bar.setStyleSheet(control_style)
        self.sortByDropDown.setStyleSheet(control_style)
        self.listen_only_check.setStyleSheet(
            f"color: {self._fg_color}; background-color: transparent;"
        )

    @staticmethod
    def _passes_filters(
        pid: int,
        name: str,
        status: str,
        port_str: str,
        service_str: str,
        search_query: str,
        status_filter: str,
    ) -> bool:
        """Check whether one process matches the current UI filters."""
        haystack = f"{port_str} {service_str} {name} {pid}".lower()
        if search_query and search_query.lower() not in haystack:
            return False

        if "Active" in status_filter:
            return status in _ACTIVE_STATUSES
        if "Stopped" in status_filter:
            return status in _STOPPED_STATUSES
        return True

    def refresh_data(self):
        """Rebuild the table from live socket and process information."""
        search_query = self.search_bar.text().strip()
        status_filter = self.sortByDropDown.currentText()
        listen_only = self.listen_only_check.isChecked()
        pid_to_ports = fetch_pid_to_ports(listen_only=listen_only)

        self.table.setRowCount(0)
        current_pids = set()

        for proc in psutil.process_iter(
            ["pid", "name", "status", "cpu_percent", "memory_info", "io_counters"]
        ):
            try:
                pid = proc.info["pid"]
                port_entries = pid_to_ports.get(pid)

                if port_entries:
                    ordered_ports = sorted(port_entries, key=lambda e: int(e[0]))
                    port_str = ", ".join(port for port, _ in ordered_ports)

                    services: list = []
                    seen_services = set()
                    for port, proto in ordered_ports:
                        resolved = service_name(port, proto)
                        if resolved != "-" and resolved not in seen_services:
                            seen_services.add(resolved)
                            services.append(resolved)
                    service_str = ", ".join(services) if services else "-"
                else:
                    port_str = "-"
                    service_str = "-"

                name = proc.info["name"] or "unknown"
                status = proc.info["status"]

                if not self._passes_filters(
                    pid,
                    name,
                    status,
                    port_str,
                    service_str,
                    search_query,
                    status_filter,
                ):
                    continue

                cpu = proc.info["cpu_percent"] or 0.0
                mem_info = proc.info["memory_info"]
                mem = mem_info.rss / (1024 * 1024) if mem_info else 0.0

                io = proc.info["io_counters"]
                disk = (io.read_bytes + io.write_bytes) / (1024 * 1024) if io else 0.0

                row = self.table.rowCount()
                self.table.insertRow(row)

                items = [
                    QTableWidgetItem(str(pid)),
                    QTableWidgetItem(name),
                    QTableWidgetItem(port_str),
                    QTableWidgetItem(service_str),
                    QTableWidgetItem(f"{cpu:.1f}"),
                    QTableWidgetItem(f"{mem:.1f}"),
                    QTableWidgetItem(f"{disk:.1f}"),
                ]

                for col, item in enumerate(items):
                    if col == 1:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                        )
                    else:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    self.table.setItem(row, col, item)

                self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, pid)
                self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole + 1, status)

                current_pids.add(pid)

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
                TypeError,
                ValueError,
                RuntimeError,
                OverflowError,
            ):
                continue

    def show_context_menu(self, pos):
        """Open the process control menu for the row under *pos*."""
        item = self.table.itemAt(pos)
        if not item:
            return

        row = item.row()
        port_item = self.table.item(row, 0)
        pid = port_item.data(Qt.ItemDataRole.UserRole)
        status = port_item.data(Qt.ItemDataRole.UserRole + 1)

        menu = QMenu(self)
        menu.setMinimumWidth(200)
        stop_action = menu.addAction("Stop")
        continue_action = menu.addAction("Continue")
        kill_action = menu.addAction("Kill")

        if status == psutil.STATUS_STOPPED:
            stop_action.setEnabled(False)
            continue_action.setEnabled(True)
        else:
            stop_action.setEnabled(True)
            continue_action.setEnabled(False)

        action = menu.exec(self.table.viewport().mapToGlobal(pos))

        if action:
            try:
                proc = psutil.Process(pid)
                if action == stop_action:
                    proc.suspend()
                elif action == continue_action:
                    proc.resume()
                elif action == kill_action:
                    proc.kill()
                self.refresh_data()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
