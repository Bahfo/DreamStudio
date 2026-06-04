from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
)
from PyQt6.QtCore import Qt

from editor.widgets.QDreamTabEditor import QDreamTabEditor


class DevContainers(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._parent = parent
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(5)

        layout.addSpacing(10)
        self.label = QLabel("DEV CONTAINERS")
        self.label.setStyleSheet(
            """color: #969696; 
            font-size: 11px; 
            font-weight: bold; 
            letter-spacing: 1px; 
            padding: 4px 8px;"""
        )
        layout.addWidget(self.label)
        layout.addSpacing(10)

        self.tab_editor = QDreamTabEditor(self)

        self.processes_tab = QWidget()
        self._setup_processes_tab()
        self.tab_editor.addTab(self.processes_tab, "Processes")
        self.tab_editor.addTab(QWidget(), "Images")

        self.tab_editor.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
        """)

        layout.addWidget(self.tab_editor)

    def _setup_processes_tab(self):
        layout = QVBoxLayout(self.processes_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Name", "PID", "Status", "CPU Usage", "Memory Usage", "Actions"]
        )

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 80)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                color: #CCCCCC;
                gridline-color: #2D2D2D;
                border: 1px solid #2D2D2D;
                border-radius: 4px;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QTableWidget::item:selected {
                background-color: #25324D;
                color: white;
            }
            QHeaderView::section {
                background-color: #252526;
                color: #969696;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid #2D2D2D;
                font-weight: bold;
                font-size: 11px;
            }
        """)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)

        layout.addWidget(self.table, stretch=1)

        self.detail_card = QFrame()
        self._setup_detail_card()
        self.detail_card.setVisible(False)
        layout.addWidget(self.detail_card)

    def _setup_detail_card(self):
        card = self.detail_card
        card.setObjectName("ContainerDetailCard")
        card.setStyleSheet("""
            #ContainerDetailCard {
                background-color: #1E1E1E;
                border: 1px solid #35538F;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        title = QLabel("Container Details")
        title.setStyleSheet(
            "color: #CCCCCC; font-size: 13px; font-weight: bold; background: transparent;"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = QPushButton("X")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3C3C3C;
                color: #969696;
                border: none;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
                color: white;
            }
        """)
        close_btn.clicked.connect(lambda: card.setVisible(False))
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

        info_layout = QHBoxLayout()
        info_layout.setSpacing(20)

        self.detail_name = QLabel("Name: --")
        self.detail_id = QLabel("ID: --")
        self.detail_image = QLabel("Image: --")
        self.detail_status = QLabel("Status: --")

        for lbl in [
            self.detail_name,
            self.detail_id,
            self.detail_image,
            self.detail_status,
        ]:
            lbl.setStyleSheet(
                "color: #969696; font-size: 11px; background: transparent;"
            )

        info_layout.addWidget(self.detail_name)
        info_layout.addWidget(self.detail_id)
        info_layout.addWidget(self.detail_image)
        info_layout.addWidget(self.detail_status)
        info_layout.addStretch()

        layout.addLayout(info_layout)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        start_btn = QPushButton("Start")
        stop_btn = QPushButton("Stop")
        restart_btn = QPushButton("Restart")
        remove_btn = QPushButton("Remove")

        btn_style = """
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """
        remove_btn_style = """
            QPushButton {
                background-color: #5a1d1d;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #7a2d2d;
            }
        """

        for btn in [start_btn, stop_btn, restart_btn]:
            btn.setStyleSheet(btn_style)
        remove_btn.setStyleSheet(remove_btn_style)

        actions_layout.addWidget(start_btn)
        actions_layout.addWidget(stop_btn)
        actions_layout.addWidget(restart_btn)
        actions_layout.addWidget(remove_btn)
        actions_layout.addStretch()

        layout.addLayout(actions_layout)

    def add_container_row(
        self, name, pid, status, cpu, memory, row_data=None
    ):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(name))
        self.table.setItem(row, 1, QTableWidgetItem(str(pid)))
        self.table.setItem(row, 2, QTableWidgetItem(status))
        self.table.setItem(row, 3, QTableWidgetItem(f"{cpu}%"))
        self.table.setItem(row, 4, QTableWidgetItem(memory))

        check_btn = QPushButton("Check")
        check_btn.setFixedSize(60, 22)
        check_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        check_btn.clicked.connect(
            lambda checked, r=row: self.show_container_detail(r, row_data)
        )
        self.table.setCellWidget(row, 5, check_btn)

    def show_container_detail(self, row, row_data=None):
        self.detail_card.setVisible(True)
