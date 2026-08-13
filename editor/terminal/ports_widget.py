import psutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMenu,
    QWidget,
    QLineEdit,
    QComboBox,
    QHeaderView,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
)


class PortsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table_count = [
            "PID",
            "Process Name",
            "Port Number",
            "CPU Usage",
            "Memory Usage",
            "Disk Usage",
        ]

        layout.addSpacing(10)

        top_controls_layout = QHBoxLayout()
        top_controls_layout.setContentsMargins(0, 0, 0, 0)

        self.search_bar = QLineEdit(self)
        self.search_bar.setMaximumWidth(300)
        self.search_bar.setPlaceholderText("Search Port Number ...")
        self.search_bar.textChanged.connect(self.refresh_data)

        self.sortByDropDown = QComboBox(self)
        self.sortByDropDown.view().setFixedWidth(150)
        self.sortByDropDown.setPlaceholderText("Filter Processes By ...")
        options = ["Active Processes", "Stopped Process", "All Processes"]
        self.sortByDropDown.addItems(options)
        self.sortByDropDown.setStyleSheet("border: 1px;")

        self.sortByDropDown.currentTextChanged.connect(self.refresh_data)

        top_controls_layout.addWidget(self.search_bar)
        top_controls_layout.addWidget(self.sortByDropDown)
        top_controls_layout.addStretch()

        self.table = QTableWidget(0, len(self.table_count), self)
        self.table.setHorizontalHeaderLabels(self.table_count)
        self.table.setStyleSheet("border: none;")

        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for i in [0, 2, 3, 4, 5]:
            self.table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents
            )

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.verticalHeader().setVisible(False)

        layout.addLayout(top_controls_layout)
        layout.addWidget(self.table)

        self._process_cache = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(4000)

        self.refresh_data()

    def refresh_data(self):
        search_query = self.search_bar.text().strip()
        pid_to_ports = {}

        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.pid:
                    if conn.pid not in pid_to_ports:
                        pid_to_ports[conn.pid] = set()
                    pid_to_ports[conn.pid].add(str(conn.laddr.port))
        except (psutil.AccessDenied, PermissionError):
            pass

        self.table.setRowCount(0)
        current_pids = set()

        for proc in psutil.process_iter(["pid", "name", "status"]):
            try:
                pid = proc.info["pid"]
                ports = pid_to_ports.get(pid, set())
                port_str = ", ".join(ports)

                if search_query and search_query not in port_str:
                    continue

                if pid not in self._process_cache:
                    self._process_cache[pid] = psutil.Process(pid)

                p = self._process_cache[pid]
                name = proc.info["name"]
                status = proc.info["status"]

                cpu = p.cpu_percent()
                mem = p.memory_info().rss / (1024 * 1024)

                try:
                    io = p.io_counters()
                    disk = (io.read_bytes + io.write_bytes) / (1024 * 1024)
                except (psutil.AccessDenied, AttributeError):
                    disk = 0.0

                row = self.table.rowCount()
                self.table.insertRow(row)

                items = [
                    QTableWidgetItem(str(pid)),
                    QTableWidgetItem(name),
                    QTableWidgetItem(port_str),
                    QTableWidgetItem(f"{cpu:.1f}"),
                    QTableWidgetItem(f"{mem:.1f}"),
                    QTableWidgetItem(f"{disk:.1f}"),
                ]

                for col, item in enumerate(items):
                    # Align Process Name (col 1) to the left, center everything else
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

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        for pid in list(self._process_cache.keys()):
            if pid not in current_pids:
                del self._process_cache[pid]

    def show_context_menu(self, pos):
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
