import time
import psutil

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QProgressBar,
    QScrollArea,
)

from editor.widgets.QSystemGraphWidget import SystemGraphUtil

_CORE_COLORS = [
    "#E06C75",
    "#61AFEF",
    "#98C379",
    "#E5C07B",
    "#C678DD",
    "#56B6C2",
    "#D19A66",
    "#ABB2BF",
    "#BE5046",
    "#3E7BCC",
    "#7EC87E",
    "#D4A05A",
    "#F78C6C",
    "#89DDFF",
    "#C3E88D",
    "#FF9CAC",
]


class SystemMonitor(QWidget):

    def __init__(self, _parent=None):
        super().__init__(_parent)
        self._theme = None

        self._prev_net = None
        self._prev_disk = None
        self._prev_net_time = 0.0
        self._prev_disk_time = 0.0
        self._first_net = True
        self._first_disk = True

        self._bg_color = "#1E1E1E"
        self._grid_color = "#2A2D30"
        self._text_color = "#999999"
        self._window_bg = "#1E1E1E"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(5)

        main_layout.addSpacing(10)
        self.label = QLabel("SYSTEM MONITOR")
        self.label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; "
            "letter-spacing: 1px; padding: 4px 8px;"
        )
        main_layout.addWidget(self.label)
        main_layout.addSpacing(10)

        self.tabs = QTabWidget()
        self._apply_tab_styling()
        main_layout.addWidget(self.tabs)

        self.perf_tab = QWidget()
        self.perf_tab.setStyleSheet(f"background-color: {self._window_bg};")
        perf_layout = QVBoxLayout(self.perf_tab)
        perf_layout.setContentsMargins(5, 5, 5, 5)

        self._cpu_graph = SystemGraphUtil(title="Total CPU Usage", unit="%", max_y=100)
        self._cpu_graph.add_series("Total", "#61AFEF")
        perf_layout.addWidget(self._cpu_graph)

        self._core_layout = QGridLayout()
        self._core_bars = []
        self._core_labels = []
        self._num_cores = psutil.cpu_count(logical=True) or 1
        cols = 4 if self._num_cores >= 8 else 2

        for i in range(self._num_cores):
            lbl = QLabel(f"Core {i}")
            lbl.setFont(QFont("Inter", 8))
            lbl.setStyleSheet(
                f"color: {self._text_color}; background-color: transparent;"
            )

            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(6)

            bar_color = _CORE_COLORS[i % len(_CORE_COLORS)]
            bar.setStyleSheet(
                f"""
                QProgressBar {{ background-color: {self._grid_color}; border-radius: 3px; border: none; }}
                QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 3px; }}
            """
            )

            row = i // cols
            col = (i % cols) * 2
            self._core_layout.addWidget(lbl, row, col)
            self._core_layout.addWidget(bar, row, col + 1)
            self._core_bars.append(bar)
            self._core_labels.append(lbl)

        self._core_layout.setContentsMargins(50, 0, 15, 0)
        for i in range(cols):
            self._core_layout.setColumnStretch(i * 2, 0)
            self._core_layout.setColumnStretch(i * 2 + 1, 1)
        perf_layout.addLayout(self._core_layout)

        self._ram_graph = SystemGraphUtil(title="Memory Usage", unit="%", max_y=100)
        self._net_graph = SystemGraphUtil(title="Network", unit="KB/s", max_y=100)
        self._disk_graph = SystemGraphUtil(title="Disk", unit="MB/s", max_y=50)

        perf_layout.addWidget(self._ram_graph)
        perf_layout.addWidget(self._net_graph)
        perf_layout.addWidget(self._disk_graph)

        self._ram_graph.add_series("RAM", "#98C379")
        self._net_graph.add_series("Upload", "#E06C75")
        self._net_graph.add_series("Download", "#98C379")
        self._disk_graph.add_series("Read", "#C678DD")
        self._disk_graph.add_series("Write", "#E5C07B")

        perf_scroll = QScrollArea()
        perf_scroll.setWidgetResizable(True)
        perf_scroll.setWidget(self.perf_tab)
        perf_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; border: none; }"
            "QScrollBar::handle:vertical { background: #424242; min-height: 24px; border-radius: 4px; }"
            "QScrollBar::handle:vertical:hover { background: #555555; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
        )

        self.proc_tab = QWidget()
        self.proc_tab.setStyleSheet(f"background-color: {self._window_bg};")
        proc_layout = QVBoxLayout(self.proc_tab)
        proc_layout.setContentsMargins(5, 5, 5, 5)

        self.process_table = QTableWidget(0, 6)
        self.process_table.setHorizontalHeaderLabels(
            ["PID", "Name", "CPU %", "RAM (MB)", "Disk R/W", "Internet"]
        )
        self.process_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.process_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.process_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Interactive
        )
        self.process_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.process_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.process_table.setShowGrid(False)
        self.process_table.setFont(QFont("Inter", 9))
        self._apply_table_styling()
        proc_layout.addWidget(self.process_table)

        self._process_items = {}

        self.tabs.addTab(perf_scroll, "Performance")
        self.tabs.addTab(self.proc_tab, "Processes")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._collect)
        self._timer.start(1000)

        QTimer.singleShot(100, self._collect)

    def _apply_tab_styling(self):
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{ border: none; background-color: {self._window_bg}; }}
            QTabBar::tab {{ background: {self._bg_color}; color: {self._text_color};
            padding: 8px 20px; border-bottom: 2px solid transparent; }}
            QTabBar::tab:selected {{ color: #FFFFFF; border-bottom: 2px solid #61AFEF; }}
        """
        )

    def _apply_table_styling(self):
        self.process_table.setStyleSheet(
            f"""
            QTableWidget {{ background-color: {self._window_bg};
            color: {self._text_color}; border: 1px solid {self._grid_color}; }}
            QHeaderView::section {{ background-color: {self._grid_color};
            color: {self._text_color}; padding: 4px; border: none;
            border-right: 1px solid {self._bg_color};
            border-bottom: 1px solid {self._bg_color};
            font-family: 'inter'; }}
        """
        )

    def retheme(self, t):
        self._theme = t
        self._bg_color = t.color("editor.background", "#1E1E1E")
        self._grid_color = t.color("widget.border", "#2A2D30")
        self._text_color = t.color("editor.text", "#999999")
        border = t.color("widget.border", "#3F4145")
        self._window_bg = t.color("window.background", "#1E1E1E")

        bg_qcol = QColor(self._bg_color)
        grid_qcol = QColor(self._grid_color)
        text_qcol = QColor(self._text_color)
        border_qcol = QColor(border)

        for g in (self._cpu_graph, self._ram_graph, self._net_graph, self._disk_graph):
            g.bg = bg_qcol
            g.grid_color = grid_qcol
            g.text_color = text_qcol
            g.border_color = border_qcol

        self._apply_tab_styling()
        self.perf_tab.setStyleSheet(f"background-color: {self._window_bg};")
        self.proc_tab.setStyleSheet(f"background-color: {self._window_bg};")
        self._apply_table_styling()

        for i in range(self._num_cores):
            self._core_labels[i].setStyleSheet(
                f"color: {self._text_color}; background-color: transparent;"
            )
            bar_color = _CORE_COLORS[i % len(_CORE_COLORS)]
            self._core_bars[i].setStyleSheet(
                f"""
                QProgressBar {{ background-color: {self._grid_color}; border-radius: 3px; border: none; }}
                QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 3px; }}
            """
            )

        section_fg = t.color("widget.text", "#969696")
        self.label.setStyleSheet(
            f"color: {section_fg}; font-size: 11px; font-weight: bold; "
            f"letter-spacing: 1px; padding: 4px 8px;"
        )

        self.update()

    def _collect(self):
        self._collect_cpu()
        self._collect_ram()
        self._collect_net()
        self._collect_disk()

        if self.tabs.currentIndex() == 1:
            self._collect_processes()

        self.update()

    def _collect_cpu(self):
        total_cpu = psutil.cpu_percent()
        self._cpu_graph.append("Total", total_cpu)

        per_core = psutil.cpu_percent(percpu=True)
        for i in range(min(len(per_core), self._num_cores)):
            self._core_bars[i].setValue(int(per_core[i]))

    def _collect_ram(self):
        mem = psutil.virtual_memory()
        self._ram_graph.append("RAM", mem.percent)

    def _collect_net(self):
        now = time.time()
        net = psutil.net_io_counters()
        if self._prev_net is not None and not self._first_net:
            dt = now - self._prev_net_time
            if dt > 0:
                up_kbps = (net.bytes_sent - self._prev_net[0]) / dt / 1024
                down_kbps = (net.bytes_recv - self._prev_net[1]) / dt / 1024
                self._net_graph.append("Upload", up_kbps)
                self._net_graph.append("Download", down_kbps)
                peak = max(up_kbps, down_kbps, 10)
                self._net_graph.set_range(0, max(peak * 1.2, 10))
        self._prev_net = (net.bytes_sent, net.bytes_recv)
        self._prev_net_time = now
        self._first_net = False

    def _collect_disk(self):
        now = time.time()
        disk = psutil.disk_io_counters()
        if disk is None:
            return
        if self._prev_disk is not None and not self._first_disk:
            dt = now - self._prev_disk_time
            if dt > 0:
                read_mbs = (disk.read_bytes - self._prev_disk[0]) / dt / 1024 / 1024
                write_mbs = (disk.write_bytes - self._prev_disk[1]) / dt / 1024 / 1024
                self._disk_graph.append("Read", read_mbs)
                self._disk_graph.append("Write", write_mbs)
                peak = max(read_mbs, write_mbs, 1)
                self._disk_graph.set_range(0, max(peak * 1.2, 5))
        self._prev_disk = (disk.read_bytes, disk.write_bytes)
        self._prev_disk_time = now
        self._first_disk = False

    def _collect_processes(self):
        self.process_table.setSortingEnabled(False)
        current_pids = set()

        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_info", "io_counters"]
        ):
            try:
                pid = proc.info["pid"]
                current_pids.add(pid)

                name = proc.info["name"] or ""
                cpu = (
                    f"{proc.info['cpu_percent']:.1f}"
                    if proc.info["cpu_percent"] is not None
                    else "0.0"
                )

                ram = "0.0"
                if proc.info["memory_info"]:
                    ram = f"{(proc.info['memory_info'].rss / (1024**2)):.1f}"

                disk = "N/A"
                if proc.info["io_counters"]:
                    reads = proc.info["io_counters"].read_bytes / (1024**2)
                    writes = proc.info["io_counters"].write_bytes / (1024**2)
                    disk = f"{reads:.1f} / {writes:.1f} MB"

                if pid in self._process_items:
                    row = self._process_items[pid]
                    self.process_table.item(row, 2).setText(cpu)
                    self.process_table.item(row, 3).setText(ram)
                    self.process_table.item(row, 4).setText(disk)
                else:
                    row = self.process_table.rowCount()
                    self.process_table.insertRow(row)
                    self.process_table.setItem(row, 0, QTableWidgetItem(str(pid)))
                    self.process_table.setItem(row, 1, QTableWidgetItem(name))
                    self.process_table.setItem(row, 2, QTableWidgetItem(cpu))
                    self.process_table.setItem(row, 3, QTableWidgetItem(ram))
                    self.process_table.setItem(row, 4, QTableWidgetItem(disk))
                    self.process_table.setItem(row, 5, QTableWidgetItem("N/A"))
                    self._process_items[pid] = row
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        dead_pids = set(self._process_items.keys()) - current_pids
        for pid in dead_pids:
            row = self._process_items[pid]
            self.process_table.removeRow(row)
            del self._process_items[pid]
            self._process_items = {
                int(self.process_table.item(r, 0).text()): r
                for r in range(self.process_table.rowCount())
            }

        self.process_table.setSortingEnabled(True)
