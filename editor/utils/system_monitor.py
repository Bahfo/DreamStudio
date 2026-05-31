import time
import psutil

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QPainterPath, 
    QLinearGradient, QBrush
)
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QWidget, QGridLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QProgressBar
)

_CORE_COLORS = [
    "#E06C75", "#61AFEF", "#98C379", "#E5C07B",
    "#C678DD", "#56B6C2", "#D19A66", "#ABB2BF",
    "#BE5046", "#3E7BCC", "#7EC87E", "#D4A05A",
    "#F78C6C", "#89DDFF", "#C3E88D", "#FF9CAC",
]

_PLOT_HEIGHT = 140


class _GraphWidget(QWidget):
    """Upgraded GraphWidget with Antialiasing, Smooth Paths, and Gradients."""
    def __init__(self, parent=None, title="", unit="%", min_y=0, max_y=100):
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._min_y = min_y
        self._max_y = max_y
        self._series = {}
        self._colors = {}
        self._max_points = 60
        self._show_legend = True

        self.bg = QColor("#1E1E1E")
        self.grid_color = QColor("#2A2D30")
        self.text_color = QColor("#999999")
        self.border_color = QColor("#3F4145")

        self.setMinimumHeight(_PLOT_HEIGHT)
        self.setMaximumHeight(_PLOT_HEIGHT * 2)

    def add_series(self, name, color=None):
        self._series[name] = []
        if color is not None:
            self._colors[name] = QColor(color)
        else:
            idx = len(self._series)
            self._colors[name] = QColor(_CORE_COLORS[idx % len(_CORE_COLORS)])

    def append(self, name, value):
        if name not in self._series:
            self.add_series(name)
        self._series[name].append(value)
        if len(self._series[name]) > self._max_points:
            self._series[name].pop(0)

    def set_range(self, min_y, max_y):
        self._min_y = min_y
        self._max_y = max_y

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.fillRect(self.rect(), self.bg)

        ml, mr, mt, mb = 50, 15, 25, 25
        px = ml
        py = mt
        pw = w - ml - mr
        ph = h - mt - mb

        if pw <= 0 or ph <= 0:
            painter.end()
            return

        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(px, py, pw, ph)

        painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
        for i in range(1, 4):
            y = py + int(ph * i / 4)
            painter.drawLine(px, y, px + pw, y)

        painter.setPen(self.text_color)
        f = QFont("JetBrains Mono", 8)
        painter.setFont(f)
        for i in range(5):
            y = py + ph - int(ph * i / 4)
            val = self._min_y + (self._max_y - self._min_y) * i / 4
            painter.drawText(2, y - 6, ml - 6, 12,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"{val:.0f}")

        tf = QFont("Inter", 10, QFont.Weight.Bold)
        painter.setFont(tf)
        painter.setPen(self.text_color)
        painter.drawText(px, 2, pw, 18,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"{self._title} ({self._unit})")

        if not self._series:
            painter.end()
            return

        max_len = max((len(v) for v in self._series.values()), default=0)
        if max_len < 2:
            painter.end()
            return

        painter.save()
        painter.setClipRect(px, py, pw, ph)

        for name, values in self._series.items():
            if len(values) < 2:
                continue
            
            color = self._colors.get(name, QColor("#FFFFFF"))
            path = QPainterPath()
            
            rng = max(self._max_y - self._min_y, 1)
            
            # Build continuous smooth path
            for i, val in enumerate(values):
                x = px + (i * pw / max(self._max_points - 1, 1))
                ratio = (val - self._min_y) / rng
                y = py + ph - int(ratio * ph)
                
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            # Draw Gradient Fill
            fill_path = QPainterPath(path)
            fill_path.lineTo(px + pw, py + ph)
            fill_path.lineTo(px, py + ph)
            fill_path.closeSubpath()

            gradient = QLinearGradient(0, py, 0, py + ph)
            gradient.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 100))
            gradient.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            
            painter.fillPath(fill_path, QBrush(gradient))

            # Draw Line Segment
            painter.setPen(QPen(color, 2))
            painter.drawPath(path)

        painter.restore()

        # Legend
        if self._show_legend and len(self._series) <= 8:
            lx = px + 6
            ly = py + 4
            for name, color in self._colors.items():
                if name not in self._series or not self._series[name]:
                    continue
                painter.setPen(QPen(color, 2.5))
                painter.drawLine(lx, ly + 5, lx + 14, ly + 5)
                painter.setPen(self.text_color)
                lf = QFont("JetBrains Mono", 7)
                painter.setFont(lf)
                painter.drawText(lx + 18, ly + 8, name)
                ly += 14

        painter.end()


class SystemMonitorPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("System Monitor")
        self.resize(780, 720) # Slightly larger to fit table and progress bars

        self._prev_net = None
        self._prev_disk = None
        self._prev_net_time = 0.0
        self._prev_disk_time = 0.0
        self._first_net = True
        self._first_disk = True

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Base Styling for Tabs
        self._bg_color = "#1E1E1E"
        self._grid_color = "#2A2D30"
        self._text_color = "#999999"

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{ background: {self._bg_color}; color: {self._text_color}; padding: 8px 20px; border-bottom: 2px solid transparent; }}
            QTabBar::tab:selected {{ color: #FFFFFF; border-bottom: 2px solid #61AFEF; }}
        """)
        main_layout.addWidget(self.tabs)

        # --- TAB 1: PERFORMANCE ---
        self.perf_tab = QWidget()
        perf_layout = QVBoxLayout(self.perf_tab)
        perf_layout.setContentsMargins(5, 5, 5, 5)

        # CPU Section (Graph + Progress Bars)
        self._cpu_graph = _GraphWidget(title="Total CPU Usage", unit="%", max_y=100)
        self._cpu_graph.add_series("Total", "#61AFEF")
        perf_layout.addWidget(self._cpu_graph)

        self._core_layout = QGridLayout()
        self._core_bars = []
        self._num_cores = psutil.cpu_count(logical=True) or 1
        cols = 4 if self._num_cores >= 8 else 2

        for i in range(self._num_cores):
            lbl = QLabel(f"Core {i}")
            lbl.setFont(QFont("JetBrains Mono", 8))
            lbl.setStyleSheet(f"color: {self._text_color};")
            
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            
            # Dynamic Core colors from your original palette
            bar_color = _CORE_COLORS[i % len(_CORE_COLORS)]
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color: {self._grid_color}; border-radius: 3px; }}
                QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 3px; }}
            """)
            
            row = i // cols
            col = (i % cols) * 2
            self._core_layout.addWidget(lbl, row, col)
            self._core_layout.addWidget(bar, row, col + 1)
            self._core_bars.append(bar)

        perf_layout.addLayout(self._core_layout)

        # RAM, NET, DISK
        self._ram_graph = _GraphWidget(title="Memory Usage", unit="%", max_y=100)
        self._net_graph = _GraphWidget(title="Network", unit="KB/s", max_y=100)
        self._disk_graph = _GraphWidget(title="Disk", unit="MB/s", max_y=50)

        perf_layout.addWidget(self._ram_graph)
        perf_layout.addWidget(self._net_graph)
        perf_layout.addWidget(self._disk_graph)

        self._ram_graph.add_series("RAM", "#98C379")
        self._net_graph.add_series("Upload", "#E06C75")
        self._net_graph.add_series("Download", "#98C379")
        self._disk_graph.add_series("Read", "#C678DD")
        self._disk_graph.add_series("Write", "#E5C07B")

        # --- TAB 2: PROCESSES ---
        self.proc_tab = QWidget()
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
        self.process_table.setFont(QFont("JetBrains Mono", 9))
        proc_layout.addWidget(self.process_table)

        self._process_items = {}

        self.tabs.addTab(self.perf_tab, "Performance")
        self.tabs.addTab(self.proc_tab, "Processes")

        # Timer setup
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._collect)
        self._timer.start(1000)

        QTimer.singleShot(100, self._collect)

    def retheme(self, t):
        """Preserves your original theming mechanism for the parent system."""
        self._bg_color = t.color("editor.background", "#1E1E1E")
        self._grid_color = t.color("widget.border", "#2A2D30")
        self._text_color = t.color("editor.text", "#999999")
        border = t.color("widget.border", "#3F4145")

        bg_qcol = QColor(self._bg_color)
        grid_qcol = QColor(self._grid_color)
        text_qcol = QColor(self._text_color)
        border_qcol = QColor(border)

        for g in (self._cpu_graph, self._ram_graph, self._net_graph, self._disk_graph):
            g.bg = bg_qcol
            g.grid_color = grid_qcol
            g.text_color = text_qcol
            g.border_color = border_qcol

        # Update Table Theme
        self.process_table.setStyleSheet(f"""
            QTableWidget {{ background-color: {self._bg_color}; color: {self._text_color}; border: 1px solid {self._grid_color}; }}
            QHeaderView::section {{ background-color: {self._grid_color}; color: {self._text_color}; padding: 4px; border: none; border-right: 1px solid {self._bg_color}; border-bottom: 1px solid {self._bg_color}; }}
        """)
        
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
        # Line Graph updates with Total CPU
        total_cpu = psutil.cpu_percent()
        self._cpu_graph.append("Total", total_cpu)
        
        # Progress Bars update with per-core CPU
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
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'io_counters']):
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
                    self.process_table.setItem(row, 5, QTableWidgetItem("N/A")) # Per-process net requires root
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