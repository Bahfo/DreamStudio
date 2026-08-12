import psutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMenu,
    QWidget,
    QLineEdit,
    QHeaderView,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
)


class PortsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search Port Number...")
        self.search_bar.textChanged.connect(self.refresh_data)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            ["Port(s)", "Name", "CPU (%)", "Memory (MB)", "Disk IO (MB)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.search_bar)
        layout.addWidget(self.table)

        self._process_cache = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(2000)

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

                self.table.setItem(row, 0, QTableWidgetItem(port_str))
                self.table.setItem(row, 1, QTableWidgetItem(name))
                self.table.setItem(row, 2, QTableWidgetItem(f"{cpu:.1f}"))
                self.table.setItem(row, 3, QTableWidgetItem(f"{mem:.1f}"))
                self.table.setItem(row, 4, QTableWidgetItem(f"{disk:.1f}"))

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
