import time
import psutil

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont,QLinearGradient
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QProgressBar, QPushButton
)

# Local Imports
from editor.widgets.QSystemGraphWidget import SystemGraphUtil

_CORE_COLORS = [
    "#E06C75", "#61AFEF", "#98C379", "#E5C07B",
    "#C678DD", "#56B6C2", "#D19A66", "#ABB2BF",
    "#BE5046", "#3E7BCC", "#7EC87E", "#D4A05A",
    "#F78C6C", "#89DDFF", "#C3E88D", "#FF9CAC",
]

_WINDOW_WIDTH = 780
_WINDOW_HEIGHT = 760


class _SysMonitorTitleBar(QWidget):
    """Custom title bar for System Monitor, matching main IDE title bar structure."""

    def __init__(self, parent, title="System Monitor"):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.setStyleSheet("font: 'inter';")
        self.offset = None

        self._gradient_colors = [
            "#004073", "#11324E", "#1E2E3B", "#24292D", "#25272B",
        ]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_btn = QPushButton(title)
        self.title_btn.setStyleSheet("""
            QPushButton{
                color: white;
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-family: 'Inter';
            }
        """)
        layout.addWidget(self.title_btn)

        layout.addStretch()

        self.btn_minimize = QPushButton("\u2014")
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_minimize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minimize.setStyleSheet("""
            QPushButton{
                color: white;
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover{
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        layout.addWidget(self.btn_minimize)

        self.btn_close = QPushButton("\u2715")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton{
                color: white;
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover{
                background-color: #E81123;
                color: white;
            }
        """)
        layout.addWidget(self.btn_close)

        self.btn_minimize.clicked.connect(self.parent.showMinimized)
        self.btn_close.clicked.connect(self.parent.close)

    def mousePressEvent(self, event):
        win = self.window()
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - win.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        win = self.window()
        if self.offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            win.move(event.globalPosition().toPoint() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.offset = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        stops = [0.85, 0.7, 0.5, 0.3, 0.1]
        gradient = QLinearGradient(0, 0, self.width(), 0)
        for stop, color in zip(stops, self._gradient_colors):
            gradient.setColorAt(stop, QColor(color))
        painter.fillRect(self.rect(), gradient)
        super().paintEvent(event)


class SystemMonitorPanel(QWidget):

    def __init__(self, parent=None, theme_manager=None):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("System Monitor")
        self.setFixedSize(_WINDOW_WIDTH, _WINDOW_HEIGHT)

        self._theme_manager = theme_manager

        self._prev_net = None
        self._prev_disk = None
        self._prev_net_time = 0.0
        self._prev_disk_time = 0.0
        self._first_net = True
        self._first_disk = True

        if theme_manager:
            self._bg_color = theme_manager.color("editor.background", "#1E1E1E")
            self._grid_color = theme_manager.color("widget.border", "#2A2D30")
            self._text_color = theme_manager.color("editor.text", "#999999")
            self._window_bg = theme_manager.color("window.background", "#1E1E1E")
        else:
            self._bg_color = "#1E1E1E"
            self._grid_color = "#2A2D30"
            self._text_color = "#999999"
            self._window_bg = "#1E1E1E"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = _SysMonitorTitleBar(self, "System Monitor")
        main_layout.addWidget(self.title_bar)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {self._window_bg};")
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)

        self.tabs = QTabWidget()
        self._apply_tab_styling()
        content_layout.addWidget(self.tabs)

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
            lbl.setStyleSheet(f"color: {self._text_color}; background-color: transparent;")

            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(6)

            bar_color = _CORE_COLORS[i % len(_CORE_COLORS)]
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color: {self._grid_color}; border-radius: 3px; border: none; }}
                QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 3px; }}
            """)

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

        self.proc_tab = QWidget()
        self.proc_tab.setStyleSheet(f"background-color: {self._window_bg};")
        proc_layout = QVBoxLayout(self.proc_tab)
        proc_layout.setContentsMargins(5, 5, 5, 5)

        self.process_table = QTableWidget(0, 6)
        self.process_table.setHorizontalHeaderLabels(["PID", "Name", "CPU %", "RAM (MB)", "Disk R/W", "Internet"])
        self.process_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.process_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.process_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.process_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.process_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.process_table.setShowGrid(False)
        self.process_table.setFont(QFont("Inter", 9))
        self._apply_table_styling()
        proc_layout.addWidget(self.process_table)

        self._process_items = {}

        self.tabs.addTab(self.perf_tab, "Performance")
        self.tabs.addTab(self.proc_tab, "Processes")

        main_layout.addWidget(self.content_widget)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._collect)
        self._timer.start(1000)

        QTimer.singleShot(100, self._collect)

    def _apply_tab_styling(self):
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background-color: {self._window_bg}; }}
            QTabBar::tab {{ background: {self._bg_color}; color: {self._text_color};
            padding: 8px 20px; border-bottom: 2px solid transparent; }}
            QTabBar::tab:selected {{ color: #FFFFFF; border-bottom: 2px solid #61AFEF; }}
        """)

    def _apply_table_styling(self):
        self.process_table.setStyleSheet(f"""
            QTableWidget {{ background-color: {self._window_bg}; 
            color: {self._text_color}; border: 1px solid {self._grid_color}; }}
            QHeaderView::section {{ background-color: {self._grid_color}; 
            color: {self._text_color}; padding: 4px; border: none; 
            border-right: 1px solid {self._bg_color}; 
            border-bottom: 1px solid {self._bg_color};
            font-family: 'Inter'; }}
        """)

    def retheme(self, t):
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

        self.content_widget.setStyleSheet(f"background-color: {self._window_bg};")
        self._apply_tab_styling()
        self.perf_tab.setStyleSheet(f"background-color: {self._window_bg};")
        self.proc_tab.setStyleSheet(f"background-color: {self._window_bg};")
        self._apply_table_styling()

        for i in range(self._num_cores):
            self._core_labels[i].setStyleSheet(
                f"color: {self._text_color}; background-color: transparent;"
            )
            bar_color = _CORE_COLORS[i % len(_CORE_COLORS)]
            self._core_bars[i].setStyleSheet(f"""
                QProgressBar {{ background-color: {self._grid_color}; border-radius: 3px; border: none; }}
                QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 3px; }}
            """)

        tb_text = t.color("titlebar.text", "#FFFFFF")
        btn_hover = t.color("titlebar.btn_hover", "rgba(255, 255, 255, 0.1)")
        self.title_bar.title_btn.setStyleSheet(f"""
            QPushButton{{
                color: {tb_text};
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-family: 'Inter';
            }}
        """)
        win_btn_style = f"""
            QPushButton{{color: {tb_text}; background-color: transparent; 
            border: none; border-radius: 4px; font-size: 12px;}}
            QPushButton:hover{{background-color: {btn_hover};}}
        """
        self.title_bar.btn_minimize.setStyleSheet(win_btn_style)
        self.title_bar.btn_close.setStyleSheet(win_btn_style + """
            QPushButton:hover{background-color: #E81123; color: white;}
        """)

        self.title_bar._gradient_colors = [
            t.color("titlebar.gradient_0", "#004073"),
            t.color("titlebar.gradient_1", "#11324E"),
            t.color("titlebar.gradient_2", "#1E2E3B"),
            t.color("titlebar.gradient_3", "#24292D"),
            t.color("titlebar.gradient_4", "#25272B"),
        ]

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

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 
            'memory_info', 'io_counters']):
            try:
                pid = proc.info['pid']
                current_pids.add(pid)

                name = proc.info['name'] or ""
                cpu = f"{proc.info['cpu_percent']:.1f}" if proc.info['cpu_percent'] is not None else "0.0"

                ram = "0.0"
                if proc.info['memory_info']:
                    ram = f"{(proc.info['memory_info'].rss / (1024**2)):.1f}"

                disk = "N/A"
                if proc.info['io_counters']:
                    reads = proc.info['io_counters'].read_bytes / (1024**2)
                    writes = proc.info['io_counters'].write_bytes / (1024**2)
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
