from editor import *
import psutil


from editor.widgets.QSystemGraphWidget import SystemGraphUtil
from editor.terminal.ProcessesViewer.ports_widget import PortsWidget

from assets.fonts.font_strapper import Fonts


class SystemMonitor(QWidget):
    """Live performance graphs plus the process/port table."""

    def __init__(self, _parent=None):
        super().__init__(_parent)
        self._theme = None

        self._prev_net = None
        self._prev_disk = None
        self._prev_net_time = 0.0
        self._prev_disk_time = 0.0
        self._first_net = True
        self._first_disk = True

        bg, fg, sel = self._palette_from_window(_parent)
        self._bg_color = bg
        self._fg_color = fg
        self._grid_color = self._blend(bg, fg, 0.14)
        self._text_color = self._blend(bg, fg, 0.68)
        self._window_bg = bg
        self._accent_color = sel

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(5)

        main_layout.addSpacing(10)
        self.label = QLabel("SYSTEM MONITOR")
        main_layout.addWidget(self.label)
        main_layout.addSpacing(10)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.perf_tab = QWidget()
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
            lbl.setFont(Fonts.inter(8))

            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(6)

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

        self.ports_view = PortsWidget(self)

        self.tabs.addTab(perf_scroll, "Performance")
        self.tabs.addTab(self.ports_view, "Processes & Ports")

        self.apply_theme(self._bg_color, self._fg_color, self._accent_color)

        try:
            psutil.cpu_percent(interval=None)
            psutil.cpu_percent(interval=None, percpu=True)
        except Exception:
            pass

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._collect)
        self._timer.start(1000)

        QTimer.singleShot(100, self._collect)

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------
    @staticmethod
    def _palette_from_window(parent) -> tuple[str, str, str]:
        """Read the active IDE theme colours from the owning main window."""
        window = None
        try:
            window = parent.window() if parent is not None else None
        except RuntimeError:
            window = None

        bg = getattr(window, "_qss_bg", None) or "#1E1E1E"
        fg = getattr(window, "_qss_fg", None) or "#D4D4D4"
        sel = getattr(window, "_qss_sel", None) or "#61AFEF"

        if not QColor(bg).isValid():
            bg = "#1E1E1E"
        if not QColor(fg).isValid():
            fg = "#D4D4D4"
        if not QColor(sel).isValid() or sel.lower() == bg.lower():
            sel = "#61AFEF"
        return bg, fg, sel

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
        """Re-colour every monitor surface for the active IDE theme."""
        if QColor(bg).isValid():
            self._bg_color = bg
            self._window_bg = bg
        if QColor(fg).isValid():
            self._fg_color = fg
        if QColor(sel).isValid() and sel.lower() != self._bg_color.lower():
            self._accent_color = sel

        self._text_color = self._blend(self._bg_color, self._fg_color, 0.68)
        self._grid_color = self._blend(self._bg_color, self._fg_color, 0.14)

        self.label.setStyleSheet(
            f"color: {self._text_color}; font-size: 11px; font-weight: bold; "
            "letter-spacing: 1px; padding: 4px 8px; background-color: transparent;"
        )

        self.perf_tab.setStyleSheet(
            f"""
            QWidget {{
                background-color: {self._bg_color};
                color: {self._text_color};
            }}
            QProgressBar {{
                background-color: {self._grid_color};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {self._accent_color};
                border-radius: 3px;
            }}
            """
        )

        for lbl in self._core_labels:
            lbl.setStyleSheet(
                f"color: {self._text_color}; background-color: transparent;"
            )

        for graph in (
            self._cpu_graph,
            self._ram_graph,
            self._net_graph,
            self._disk_graph,
        ):
            graph.bg = QColor(self._bg_color)
            graph.grid_color = QColor(self._grid_color)
            graph.text_color = QColor(self._text_color)
            graph.border_color = QColor(
                self._blend(self._bg_color, self._fg_color, 0.25)
            )
            graph.update()

        self._apply_tab_styling()

        if hasattr(self.ports_view, "apply_theme"):
            self.ports_view.apply_theme(
                self._bg_color, self._fg_color, self._accent_color
            )

    def _apply_tab_styling(self) -> None:
        """Style the inner QTabWidget to match the active theme."""
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {self._grid_color};
                background-color: {self._bg_color};
            }}
            QTabBar::tab {{
                background-color: {self._bg_color};
                color: {self._text_color};
                padding: 5px 14px;
                border: 1px solid {self._grid_color};
                border-bottom: none;
            }}
            QTabBar::tab:selected {{
                color: {self._text_color};
                border-bottom: 2px solid {self._accent_color};
            }}
            """)

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------
    def _collect(self):
        self._collect_cpu()
        self._collect_ram()
        self._collect_net()
        self._collect_disk()
        self.update()

    def _collect_cpu(self):
        total_cpu = psutil.cpu_percent(interval=None)
        self._cpu_graph.append("Total", total_cpu)

        per_core = psutil.cpu_percent(interval=None, percpu=True)
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
