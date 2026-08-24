from editor import *

from editor.utils.tools.commands_window import CommandWindow


class DreamStudioTitleBar(QWidget):
    maximize_requested = pyqtSignal()

    # Blue gradient endpoints for the built-in dark and light themes.
    _TITLE_BAR_BLUE_ENDS = {
        "dark": QColor("#004E98"),
        "light": QColor("#0081F2"),
    }

    def __init__(self, parent, directory):
        super().__init__(parent)
        self._title_parent = parent
        self.setObjectName("DreamStudioTitleBar")
        self.setFixedHeight(40)
        self.offset = None
        self.directory = directory
        self._menu_actions: dict[str, QAction] = {}

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
        self._ide_search.setObjectName("DreamStudioTitleBarSearch")
        self._ide_search.setPlaceholderText("Search Anywhere in DreamStudio")
        layout.addWidget(self._ide_search)

        # The hanging widgets that will show under the QLineEdit if any is triggered.
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
        self._update_menu_state(False)

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

    _EDITOR_MENU_ACTIONS = frozenset({
        "set_save_current_file",
        "set_save_file_as",
        "set_save_all_files",
        "set_save_all_and_close",
        "set_close_editor",
    })

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
                        self, action_str,
                        getattr(self._title_parent, action_str, None),
                    )
                    if target:
                        action.triggered.connect(target)

                if action_str in self._EDITOR_MENU_ACTIONS:
                    self._menu_actions[action_str] = action

                parent_menu.addAction(action)

    def _update_menu_state(self, has_tabs: bool) -> None:
        """Enable or disable editor-dependent menu actions."""
        for action in self._menu_actions.values():
            action.setEnabled(has_tabs)

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

    def paintEvent(self, event):
        """Draw the title bar with a horizontal gradient derived from the stylesheet.

        For the built-in dark/light themes the left colour is anchored to the
        vertical sidebar colour and the right-hand end blends toward the theme's
        blue.  Every other theme reads its base colour from the active
        ``QWidget#DreamStudioTitleBar`` rule and blends toward white.
        """
        base = self._title_bar_base_color()
        end = self._title_bar_gradient_end(base)

        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0.0, base)
        gradient.setColorAt(1.0, end)
        painter.fillRect(self.rect(), gradient)

        painter.setPen(base.darker(112))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        painter.end()
        super().paintEvent(event)

    def _title_bar_base_color(self) -> QColor:
        """Return the title bar background colour from the applied stylesheet."""
        qss = self.styleSheet()
        if not qss:
            qss = self.window().styleSheet()

        theme_name = getattr(self._title_parent, "_current_theme_name", None)
        if theme_name in self._TITLE_BAR_BLUE_ENDS:
            selector = r"VerticalSidebar|QFrame#VerticalSidebar"
        else:
            selector = r"DreamStudioTitleBar|QWidget#DreamStudioTitleBar"

        pattern = re.compile(
            rf"(?:{selector})\s*{{[^}}]*background-color\s*:\s*([^;}}\s]+)",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(qss)
        if match:
            color = QColor(match.group(1).strip())
            if color.isValid():
                return color

        parent_bg = getattr(self._title_parent, "_qss_bg", None)
        if parent_bg:
            color = QColor(parent_bg)
            if color.isValid():
                return color
        return self.palette().window().color()

    def _title_bar_gradient_end(self, base: QColor) -> QColor:
        """Return the gradient end colour for the currently active theme."""
        theme_name = getattr(self._title_parent, "_current_theme_name", None)
        blue_end = self._TITLE_BAR_BLUE_ENDS.get(theme_name)
        if blue_end is not None:
            return blue_end

        amount = 0.18 if base.lightness() < 128 else 0.10
        red = base.red() + int((255 - base.red()) * amount)
        green = base.green() + int((255 - base.green()) * amount)
        blue = base.blue() + int((255 - base.blue()) * amount)
        return QColor(red, green, blue)

    # ------------------------------------------------------------------
    # Help menu actions
    # ------------------------------------------------------------------

    def show_welcome(self) -> None:
        """Open the IDE welcome / start page window."""
        from editor.base.user.whats_new import IDEStartPage

        self._welcome_window = IDEStartPage()
        self._welcome_window.show()
