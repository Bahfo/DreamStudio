from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QThread, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QStackedWidget,
)
import os
import logging

try:
    import docker
except ImportError:
    docker = None

from editor.widgets.QDreamTabEditor import QDreamTabEditor

logger = logging.getLogger(__name__)


class DockerWorker(QObject):
    connected = pyqtSignal(bool, str)
    containers_loaded = pyqtSignal(list)
    images_loaded = pyqtSignal(list)
    docker_files_found = pyqtSignal(list)
    operation_finished = pyqtSignal(bool, str)

    def __init__(self, workspace_dir, project_prefix):
        super().__init__()
        self.workspace_dir = workspace_dir
        self.project_prefix = project_prefix
        self.docker_client = None

    @pyqtSlot()
    def connect_docker(self):
        if docker is None:
            self.connected.emit(False, "Docker SDK not installed")
            return
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            self.connected.emit(True, "Docker connected")
        except Exception as e:
            self.docker_client = None
            self.connected.emit(False, str(e))

    @pyqtSlot()
    def list_containers(self):
        if not self.docker_client:
            self.containers_loaded.emit([])
            return
        try:
            containers = []
            for c in self.docker_client.containers.list(all=True):
                tag = self.project_prefix
                if any(tag in name for name in (c.name or "")) or any(
                    tag in (img or "") for img in c.image.tags
                ):
                    containers.append(
                        {
                            "name": c.name,
                            "id": c.short_id,
                            "status": c.status,
                            "image": c.image.tags[0] if c.image.tags else "unknown",
                        }
                    )
            self.containers_loaded.emit(containers)
        except Exception as e:
            logger.error("Failed to list containers: %s", e)
            self.containers_loaded.emit([])

    @pyqtSlot()
    def list_images(self):
        if not self.docker_client:
            self.images_loaded.emit([])
            return
        try:
            images = []
            for img in self.docker_client.images.list():
                for tag in img.tags:
                    if tag.startswith(self.project_prefix):
                        images.append(
                            {
                                "id": img.short_id,
                                "tag": tag,
                                "size_mb": round(img.attrs["Size"] / (1024 * 1024), 2),
                                "created": img.attrs.get("Created", ""),
                            }
                        )
            self.images_loaded.emit(images)
        except Exception as e:
            logger.error("Failed to list images: %s", e)
            self.images_loaded.emit([])

    @pyqtSlot()
    def locate_docker_files(self):
        found = []
        for root, dirs, files in os.walk(self.workspace_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
            for file in files:
                if file.lower() == "dockerfile" or file.endswith(".dockerfile"):
                    rel = os.path.relpath(os.path.join(root, file), self.workspace_dir)
                    found.append(rel)
        self.docker_files_found.emit(found)

    @pyqtSlot(str, str)
    def build_image(self, dockerfile_rel_path, tag_name):
        if not self.docker_client:
            self.operation_finished.emit(False, "Docker not connected")
            return
        dockerfile_path = os.path.join(self.workspace_dir, dockerfile_rel_path)
        build_context = os.path.dirname(dockerfile_path)
        try:
            self.docker_client.images.build(
                path=build_context,
                dockerfile=os.path.basename(dockerfile_path),
                tag=tag_name,
                rm=True,
            )
            self.operation_finished.emit(True, f"Image {tag_name} built")
        except Exception as e:
            self.operation_finished.emit(False, str(e))

    @pyqtSlot(str)
    def start_container(self, container_id):
        if not self.docker_client:
            return
        try:
            c = self.docker_client.containers.get(container_id)
            c.start()
            self.operation_finished.emit(True, f"Container {container_id} started")
        except Exception as e:
            self.operation_finished.emit(False, str(e))

    @pyqtSlot(str)
    def stop_container(self, container_id):
        if not self.docker_client:
            return
        try:
            c = self.docker_client.containers.get(container_id)
            c.stop()
            self.operation_finished.emit(True, f"Container {container_id} stopped")
        except Exception as e:
            self.operation_finished.emit(False, str(e))

    @pyqtSlot(str)
    def remove_container(self, container_id):
        if not self.docker_client:
            return
        try:
            c = self.docker_client.containers.get(container_id)
            c.remove(force=True)
            self.operation_finished.emit(True, f"Container {container_id} removed")
        except Exception as e:
            self.operation_finished.emit(False, str(e))


class DevContainers(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self._theme = None

        main_window = self.window()
        self._workspace_dir = getattr(main_window, "currentDirectory", os.getcwd())
        self._project_prefix = os.path.basename(self._workspace_dir)

        self._worker = None
        self._thread = None
        self._connected = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(5)

        layout.addSpacing(10)
        top_row = QHBoxLayout()
        self.label = QLabel("DEV CONTAINERS")
        self.label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; "
            "letter-spacing: 1px; padding: 4px 8px;"
        )
        top_row.addWidget(self.label)
        top_row.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFixedSize(70, 24)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_all)
        self.refresh_btn.setEnabled(False)
        top_row.addWidget(self.refresh_btn)

        self.status_label = QLabel("Connecting to Docker...")
        self.status_label.setStyleSheet(
            "color: #969696; font-size: 10px; padding: 4px 8px;"
        )
        top_row.addWidget(self.status_label)

        layout.addLayout(top_row)
        layout.addSpacing(10)

        self.content_stack = QStackedWidget()

        self.no_sdk_widget = self._build_no_sdk_widget()
        self.content_stack.addWidget(self.no_sdk_widget)

        self.tab_editor = QDreamTabEditor(self)

        self.processes_tab = QWidget()
        self._setup_processes_tab()
        self.tab_editor.addTab(self.processes_tab, "Processes")

        self.images_tab = QWidget()
        self._setup_images_tab()
        self.tab_editor.addTab(self.images_tab, "Images")

        self.tab_editor.setStyleSheet(
            "QTabWidget::pane { border: none; background-color: transparent; }"
        )

        self.content_stack.addWidget(self.tab_editor)
        layout.addWidget(self.content_stack)

        if docker is None:
            self.content_stack.setCurrentWidget(self.no_sdk_widget)
            self.refresh_btn.setVisible(False)
            self.status_label.setText("Docker SDK not installed")
        else:
            self.content_stack.setCurrentWidget(self.tab_editor)
            self._start_worker()

    def _build_no_sdk_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap("assets/system/sleeping.png")
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                60,
                60,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_label)

        layout.addSpacing(20)

        self._no_sdk_title = QLabel("Docker SDK is not installed")
        self._no_sdk_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_sdk_title.setStyleSheet(
            "color: #CCCCCC; font-size: 15px; font-weight: bold;"
        )
        layout.addWidget(self._no_sdk_title)

        self._no_sdk_subtitle = QLabel(
            "Please install Docker SDK to start the connection"
        )
        self._no_sdk_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_sdk_subtitle.setStyleSheet("color: #969696; font-size: 12px;")
        self._no_sdk_subtitle.setWordWrap(True)
        layout.addWidget(self._no_sdk_subtitle)

        return widget

    def _start_worker(self):
        self._thread = QThread(self)
        self._worker = DockerWorker(self._workspace_dir, self._project_prefix)
        self._worker.moveToThread(self._thread)

        self._worker.connected.connect(self._on_docker_connected)
        self._worker.containers_loaded.connect(self._on_containers_loaded)
        self._worker.images_loaded.connect(self._on_images_loaded)
        self._worker.docker_files_found.connect(self._on_docker_files_found)
        self._worker.operation_finished.connect(self._on_operation_finished)

        self._thread.started.connect(self._worker.connect_docker)
        self._thread.finished.connect(self._cleanup_worker)
        self._thread.start()

    def _cleanup_worker(self):
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

    def _on_docker_connected(self, success, message):
        if success:
            self._connected = True
            self.status_label.setText("Connected")
            self.refresh_btn.setEnabled(True)
            self.refresh_all()
        else:
            self._connected = False
            self.status_label.setText("Docker unavailable")
            self.refresh_btn.setEnabled(False)
            logger.warning("Docker connection failed: %s", message)

    def _on_containers_loaded(self, containers):
        self.process_table.setRowCount(0)
        for c in containers:
            self._add_container_row(c)

    def _add_container_row(self, c):
        row = self.process_table.rowCount()
        self.process_table.insertRow(row)

        self.process_table.setItem(row, 0, QTableWidgetItem(c["name"]))
        self.process_table.setItem(row, 1, QTableWidgetItem(c["id"]))
        self.process_table.setItem(row, 2, QTableWidgetItem(c["status"]))
        self.process_table.setItem(row, 3, QTableWidgetItem(c["image"]))
        self.process_table.setItem(row, 4, QTableWidgetItem("--"))
        self.process_table.setItem(row, 5, QTableWidgetItem("--"))

        inspect_btn = QPushButton("Inspect")
        inspect_btn.setFixedSize(60, 22)
        inspect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        inspect_btn.clicked.connect(
            lambda checked, cid=c["id"]: self._inspect_container(cid)
        )
        self.process_table.setCellWidget(row, 6, inspect_btn)

    def _inspect_container(self, container_id):
        self.status_label.setText(f"Inspecting {container_id}...")
        QMessageBox.information(self, "Container", f"Container {container_id} selected")

    def _on_images_loaded(self, images):
        self.image_table.setRowCount(0)
        for img in images:
            row = self.image_table.rowCount()
            self.image_table.insertRow(row)
            self.image_table.setItem(row, 0, QTableWidgetItem(img["tag"]))
            self.image_table.setItem(row, 1, QTableWidgetItem(img["id"]))
            self.image_table.setItem(row, 2, QTableWidgetItem(f"{img['size_mb']} MB"))
            self.image_table.setItem(
                row, 3, QTableWidgetItem(str(img.get("created", "")))
            )

    def _on_docker_files_found(self, files):
        pass

    def _on_operation_finished(self, success, message):
        self.status_label.setText(message)
        if success:
            self.refresh_all()

    def refresh_all(self):
        if not self._worker or not self._connected:
            return
        self.status_label.setText("Refreshing...")
        QTimer.singleShot(50, self._worker.list_containers)
        QTimer.singleShot(100, self._worker.list_images)
        QTimer.singleShot(150, self._worker.locate_docker_files)

    def _setup_processes_tab(self):
        layout = QVBoxLayout(self.processes_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.process_table = QTableWidget()
        self.process_table.setColumnCount(7)
        self.process_table.setHorizontalHeaderLabels(
            ["Name", "Container ID", "Status", "Image", "Ports", "Uptime", "Actions"]
        )

        header = self.process_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 70)

        self.process_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.process_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.process_table.verticalHeader().setVisible(False)
        self.process_table.setShowGrid(True)

        layout.addWidget(self.process_table, stretch=1)

    def _setup_images_tab(self):
        layout = QVBoxLayout(self.images_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.image_table = QTableWidget()
        self.image_table.setColumnCount(4)
        self.image_table.setHorizontalHeaderLabels(
            ["Tag", "Image ID", "Size", "Created"]
        )

        header = self.image_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(3):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        self.image_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.image_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.image_table.verticalHeader().setVisible(False)
        self.image_table.setShowGrid(True)

        layout.addWidget(self.image_table, stretch=1)

    def retheme(self, t) -> None:
        self._theme = t
        bg = t.color("widget.background", "#252526")
        text = t.color("widget.text", "#CCCCCC")
        border = t.color("widget.border", "#3C3C3C")
        table_bg = t.color("treeview.background", "#252526")
        table_text = t.color("treeview.text", "#CCCCCC")
        table_highlight = t.color("treeview.highlight", "#2D476D")
        header_bg = t.color("treeview.header_bg", "#2D2D2D")
        header_text = t.color("treeview.header_text", "#CCCCCC")
        accent = t.color("widget.accent", "#007ACC")

        self.setObjectName("DevContainers")
        self.setStyleSheet(
            f"""
            #DevContainers {{
                background-color: {bg};
                color: {text};
            }}
        """
        )

        self.label.setStyleSheet(
            f"""
            color: {text};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
            padding: 4px 8px;
        """
        )

        self.status_label.setStyleSheet(
            f"""
            color: {header_text};
            font-size: 10px;
            padding: 4px 8px;
        """
        )
        self._style_table(
            self.process_table,
            table_bg,
            table_text,
            table_highlight,
            header_bg,
            header_text,
            border,
        )
        self._style_table(
            self.image_table,
            table_bg,
            table_text,
            table_highlight,
            header_bg,
            header_text,
            border,
        )

        self._no_sdk_title.setStyleSheet(
            f"""
            color: {text};
            font-size: 15px;
            font-weight: bold;
        """
        )
        self._no_sdk_subtitle.setStyleSheet(
            f"""
            color: {header_text};
            font-size: 12px;
        """
        )

        self.refresh_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #1177bb;
            }}
            QPushButton:disabled {{
                background-color: {border};
                color: {text};
            }}
        """
        )

    def _style_table(
        self,
        table,
        table_bg,
        table_text,
        table_highlight,
        header_bg,
        header_text,
        border,
    ):
        table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: {table_bg};
                color: {table_text};
                gridline-color: {border};
                border: 1px solid {border};
                border-radius: 4px;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {table_highlight};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_text};
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid {border};
                font-weight: bold;
                font-size: 11px;
            }}
        """
        )

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        super().closeEvent(event)

    def __del__(self):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(1000)
