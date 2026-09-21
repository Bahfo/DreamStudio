from editor import *
from editor.utils.resource_path import resource_path

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
        self._refresh_menus: list[QMenu] = []
        self._selection_source = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._filter_window = self.window()
        try:
            self._filter_window.installEventFilter(self)
        except Exception:
            pass
        try:
            self.destroyed.connect(self._cleanup_filter)
        except Exception:
            pass

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

        self.free_trial_btn = QPushButton("Start Free Trial")
        self.free_trial_btn.setObjectName("FreeTrial")
        self.free_trial_btn.setStyleSheet("""
        QPushButton#FreeTrial {
            background-color: transparent;
            border: 1px solid white;
            border-radius: 12px;
            color: white;
        }
        QPushButton#FreeTrial:hover {
            border: 1px solid #C9C9C9;
            color: #C9C9C9;
        }
        """)
        self.free_trial_btn.setFixedSize(115, 25)
        layout.addWidget(self.free_trial_btn)
        self.free_trial_btn.clicked.connect(self._title_parent._on_free_trial_click)

        self.btn_minimize = self._build_control_button(
            "—", self._title_parent.showMinimized, layout
        )
        self.btn_maximize = self._build_control_button(
            "◻", self.toggle_maximize, layout
        )
        self.btn_close = self._build_control_button(
            "✕", self._title_parent.close, layout
        )

        self.load_menus_from_json(resource_path("editor/base/json/menus.json"))
        self._update_menu_state(False)

        # The clipboard availability decides whether Paste can run.
        try:
            QApplication.clipboard().dataChanged.connect(self.refresh_action_states)
        except (TypeError, RuntimeError):
            pass

    def _build_control_button(self, text, callback, layout):
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

        # Safety net: an editor-dependent menu carries the freshest possible
        # state the moment it opens, even if no other signal fired meanwhile.
        for menu in self._refresh_menus:
            try:
                menu.aboutToShow.connect(self.refresh_action_states)
            except (TypeError, RuntimeError):
                pass

    _EDITOR_MENU_ACTIONS = frozenset(
        {
            "set_save_current_file",
            "set_save_file_as",
            "set_save_all_files",
            "set_save_all_and_close",
            "set_close_editor",
        }
    )

    # Single title-bar action responsible for the options bar; its label
    # flips between the two texts below while staying the same QAction.
    _OPTIONS_BAR_ACTION = "set_toggle_options_bar"
    _OPTIONS_BAR_HIDE_TEXT = "Hide Options Bar"
    _OPTIONS_BAR_SHOW_TEXT = "Show Options Bar"

    # Editor-dependent actions declared in ``menus.json`` mapped to the
    # capability they require from the active editor.  Every entry is
    # resolved by :meth:`refresh_action_states`.
    _ACTION_REQUIREMENTS = {
        # Edit
        "set_undo": "undo",
        "set_redo": "redo",
        "set_cut": "selection",
        "set_copy": "copy",
        "set_copy_as_plain_text": "copy",
        "set_paste": "paste",
        "set_delete_selection": "selection",
        "set_select_all": "editor",
        "set_unselect_all": "editor",
        "set_indent_selection": "selection",
        "set_unindent_selection": "selection",
        # View
        _OPTIONS_BAR_ACTION: "always",
        # Code
        "set_format_code": "editable",
        "set_comment_current_line": "editable",
        "set_comment_current_selection": "selection",
        "set_uncomment_current_line": "editable",
        "set_uncomment_current_selection": "selection",
        "set_duplicate_current_line": "editable",
        "set_duplicate_current_selection": "selection",
        "set_goto_definition": "provider",
        "set_goto_declaration": "provider",
        "set_goto_implementation": "provider",
        "set_expand_current_fold": "folds",
        "set_expand_all_folds": "folds",
        "set_collapse_current_fold": "folds",
        "set_collapse_all_folds": "folds",
    }

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
                    sub_menu = parent_menu.addMenu(QIcon(resource_path(icon_path)), text)
                else:
                    sub_menu = parent_menu.addMenu(text)
                self._build_menu_items(sub_menu, submenu_items)
            else:
                if icon_path:
                    action = QAction(QIcon(resource_path(icon_path)), text, self)
                else:
                    action = QAction(text, self)

                if action_str:
                    # Dynamically look up local functions or parent methods
                    target = getattr(
                        self,
                        action_str,
                        getattr(self._title_parent, action_str, None),
                    )
                    if target:
                        action.triggered.connect(target)

                if action_str in self._EDITOR_MENU_ACTIONS or (
                    action_str in self._ACTION_REQUIREMENTS
                ):
                    self._menu_actions[action_str] = action
                    if not any(m is parent_menu for m in self._refresh_menus):
                        self._refresh_menus.append(parent_menu)

                parent_menu.addAction(action)

    def _update_menu_state(self, has_tabs: bool) -> None:
        """Enable or disable editor-dependent menu actions.

        Kept as the entry point the main window already calls whenever the
        tab set changes; the per-action states below are always recomputed
        from the live editor instead of the passed hint.
        """
        for action_str in self._EDITOR_MENU_ACTIONS:
            action = self._menu_actions.get(action_str)
            if action is not None:
                action.setEnabled(has_tabs)
        self.refresh_action_states()

    # ------------------------------------------------------------------
    # Action state synchronization
    # ------------------------------------------------------------------

    def refresh_action_states(self) -> None:
        """Synchronize every editor-dependent menu action with the live state.

        Single entry point for the Edit/Code/View actions: the states are
        derived from the active editor and its selection, then the selection
        tracking and the options-bar label are refreshed.  It is called on
        tab changes, editor open/close, menu opening and clipboard changes.
        """
        flags = self._editor_action_flags()
        for action_str, requirement in self._ACTION_REQUIREMENTS.items():
            action = self._menu_actions.get(action_str)
            if action is None:
                continue
            action.setEnabled(bool(flags.get(requirement, False)))

        self._bind_selection_tracking()
        self._sync_options_bar_action()

    def _editor_action_flags(self) -> dict[str, bool]:
        """Return the live capability flags of the active editor.

        Returns:
            A requirement-name to availability mapping; every requirement
            named in ``_ACTION_REQUIREMENTS`` is present, and all of them are
            ``False`` when no code editor is active.
        """
        flags = {
            "always": True,
            "editor": False,
            "editable": False,
            "selection": False,
            "copy": False,
            "paste": False,
            "undo": False,
            "redo": False,
            "provider": False,
            "folds": False,
        }

        editor = self._active_code_editor()
        if editor is None:
            return flags

        readonly = bool(editor.isReadOnly())
        has_selection = bool(editor.hasSelectedText())

        flags["editor"] = True
        flags["editable"] = not readonly
        flags["selection"] = has_selection and not readonly
        flags["copy"] = has_selection
        flags["paste"] = not readonly and bool(self._clipboard_text())
        flags["undo"] = not readonly and bool(editor.isUndoAvailable())
        flags["redo"] = not readonly and bool(editor.isRedoAvailable())
        flags["provider"] = getattr(editor, "current_provider", None) is not None
        flags["folds"] = getattr(editor, "_fold_manager", None) is not None
        return flags
    def _active_code_editor(self):
        """Return the ``CodeEditor`` of the active tab, or ``None``.

        Uses the tab model's own unwrapping helper so a mini-map host tab
        resolves to the same editor every other consumer sees.
        """
        tabs = getattr(self._title_parent, "tab_editors", None)
        if tabs is None:
            return None

        try:
            widget = tabs.currentWidget()
        except RuntimeError:
            return None
        if widget is None:
            return None

        unwrap = getattr(tabs, "_unwrap_code_editor", None)
        if unwrap is None:
            return None
        try:
            return unwrap(widget)
        except RuntimeError:
            return None

    def _bind_selection_tracking(self) -> None:
        """Follow the active editor's selection so states never go stale."""
        editor = self._active_code_editor()
        if editor is self._selection_source:
            return

        if self._selection_source is not None:
            try:
                self._selection_source.selectionChanged.disconnect(
                    self.refresh_action_states
                )
            except (TypeError, RuntimeError):
                pass

        self._selection_source = editor
        if editor is None:
            return
        try:
            editor.selectionChanged.connect(self.refresh_action_states)
        except (TypeError, RuntimeError):
            pass

    @staticmethod
    def _clipboard_text() -> str:
        """Return the current clipboard text, or an empty string."""
        try:
            return QApplication.clipboard().text()
        except RuntimeError:
            return ""

    # ------------------------------------------------------------------
    # Options bar
    # ------------------------------------------------------------------

    def set_toggle_options_bar(self) -> None:
        """Toggle the options bar and keep this action's label in sync."""
        visible = self._title_parent.toggle_options_bar()
        self._sync_options_bar_action(visible)

    def _sync_options_bar_action(self, visible: Optional[bool] = None) -> None:
        """Make the options-bar action label match the real bar visibility.

        Args:
            visible: Known visibility of the options bar.  When omitted it is
                read from the widget; when the widget does not exist yet the
                label is left untouched.
        """
        action = self._menu_actions.get(self._OPTIONS_BAR_ACTION)
        if action is None:
            return

        if visible is None:
            bar = getattr(self._title_parent, "options_menu", None)
            if bar is None:
                return
            visible = bool(bar.isVisible())

        action.setText(
            self._OPTIONS_BAR_HIDE_TEXT if visible else self._OPTIONS_BAR_SHOW_TEXT
        )



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

    def _cleanup_filter(self):
        win = getattr(self, "_filter_window", None)
        if win is not None:
            try:
                win.removeEventFilter(self)
            except Exception:
                pass

    def closeEvent(self, event):
        self._cleanup_filter()
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if obj == getattr(self, "_filter_window", None) or obj == self.window():
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
        self._title_parent._on_welcome_btn_click()
