import json
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *

from editor.utils.tools.commands_window import CommandWindow


class DreamStudioTitleBar(QWidget):
    maximize_requested = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self._title_parent = parent
        self.setObjectName("DreamStudioTitleBar")
        self.setFixedHeight(40)
        self.offset = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.window().installEventFilter(self)

        self.icon_btn = QPushButton("DreamStudio")
        self.icon_btn.setObjectName("iconButton")
        self.icon_btn.setFixedSize(120, 30)
        self.icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.icon_btn)

        # Dynamic MenuBar placed on the left side right after the icon button
        self.menubar = QMenuBar(self)
        layout.addWidget(self.menubar)
        layout.addSpacing(30)

        self._ide_search = QLineEdit()
        self._ide_search.setPlaceholderText("Search Anywhere in DreamStudio")
        layout.addWidget(self._ide_search)

        self._commands_window = CommandWindow(self._ide_search)
        self._ide_search.mousePressEvent = self._commands_window._show

        layout.addStretch()

        self.btn_minimize = self._build_control_button(
            "—", 12, self._title_parent.showMinimized, layout
        )
        self.btn_maximize = self._build_control_button(
            "◻", 12, self.toggle_maximize, layout
        )
        self.btn_close = self._build_control_button(
            "✕", 14, self._title_parent.close, layout
        )

        self.load_menus_from_json("editor/base/json/menus.json")

    def _build_control_button(self, text, font_size, callback, layout):
        btn = QPushButton(text)
        btn.setFixedSize(40, 30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        layout.addWidget(btn)
        return btn

    def load_menus_from_json(self, json_filepath):
        """Loads and parses menu configuration dynamically from an external JSON file."""
        try:
            with open(json_filepath, "r", encoding="utf-8") as f:
                menus_config = json.load(f)
            self.setup_menus(menus_config)
        except Exception as e:
            print(f"Error loading menu configuration: {e}")

    def setup_menus(self, menus_config):
        """Builds top-level navigation menus from config mapping."""
        for menu_name, items in menus_config.items():
            menu = self.menubar.addMenu(menu_name)
            menu.setObjectName("TitleBarMenu")
            self._build_menu_items(menu, items)

    def _build_menu_items(self, parent_menu, items):
        """Recursively populates submenus, actions, and separators."""
        for item in items:
            if item is None:
                parent_menu.addSeparator()
                continue

            text = item.get("text")
            icon_path = item.get("icon")
            action_str = item.get("action")
            submenu_items = item.get("submenu")

            if submenu_items:
                if icon_path:
                    sub_menu = parent_menu.addMenu(QIcon(icon_path), text)
                else:
                    sub_menu = parent_menu.addMenu(text)
                self._build_menu_items(sub_menu, submenu_items)
            else:
                if icon_path:
                    action = QAction(QIcon(icon_path), text, self)
                else:
                    action = QAction(text, self)

                if action_str:
                    # Dynamically look up local functions or parent methods
                    target = getattr(
                        self, action_str, getattr(self._title_parent, action_str, None)
                    )
                    if target:
                        action.triggered.connect(target)

                parent_menu.addAction(action)

    def toggle_maximize(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self.btn_maximize.setText("◻")
            return

        self._restore_geometry = win.normalGeometry()
        if not self._restore_geometry.isValid():
            self._restore_geometry = win.geometry()

        win.showMaximized()
        self.btn_maximize.setText("❐")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()

    def sync_titlebar_state(self):
        win = self.window()
        self.btn_maximize.setText("❐" if win.isMaximized() else "◻")

    def mousePressEvent(self, event):
        win = self.window()
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - win.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        win = self.window()
        if self.offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if win.isMaximized():
                cursor_x = event.globalPosition().toPoint().x()
                max_width = win.width()
                width_ratio = cursor_x / max_width

                win.showNormal()
                normal_width = win.width()
                new_x = int(cursor_x - (normal_width * width_ratio))
                new_y = event.globalPosition().toPoint().y() - self.offset.y()

                win.move(new_x, new_y)
                self.offset = event.globalPosition().toPoint() - win.pos()
                return

            win.move(event.globalPosition().toPoint() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.offset = None
        super().mouseReleaseEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.window():
            if event.type() == QEvent.Type.WindowStateChange:
                self.sync_titlebar_state()
        return super().eventFilter(obj, event)
