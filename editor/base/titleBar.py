from editor import *
from editor.utils.resource_path import resource_path

from editor.utils.tools.commands_window import CommandWindow

import logging

logger = logging.getLogger("[TitleBar]")


class DreamStudioTitleBar(QWidget):
    maximize_requested = pyqtSignal()

    _TITLE_BAR_BLUE_ENDS = {
        "dark": QColor("#004E98"),
        "light": QColor("#0081F2"),
        "material_dark": QColor("#6E1F24"),
        "material_light": QColor("#D64545"),
    }

    _EDITOR_MENU_ACTIONS = frozenset(
        {
            "set_save_current_file",
            "set_save_file_as",
            "set_save_all_files",
            "set_save_all_and_close",
            "set_close_editor",
        }
    )

    _OPTIONS_BAR_ACTION = "set_toggle_options_bar"
    _OPTIONS_BAR_HIDE_TEXT = "Hide Options Bar"
    _OPTIONS_BAR_SHOW_TEXT = "Show Options Bar"

    _UNAVAILABLE_ACTIONS = frozenset(
        {
            "generic_callback",
            "set_new_window",
            "set_open_marketplace",
        }
    )
    _UNAVAILABLE_TOOLTIP = "Not available in this release."

    _ACTION_REQUIREMENTS = {
        # ---- Edit -----------------------------------------------------
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
        "set_find_replace": "workspace",
        "set_find_replace_in_files": "workspace",
        "set_search_in_selected": "selection",
        "set_manage_indentation": "editor",
        # ---- View -----------------------------------------------------
        _OPTIONS_BAR_ACTION: "always",
        "set_toggle_left_bar": "always",
        "set_toggle_right_bar": "always",
        "set_toggle_sidebar_side": "always",
        "set_reset_appearance": "always",
        "set_full_screen": "always",
        "set_zen_mode": "always",
        # ---- Tools ----------------------------------------------------
        "_show_command_window": "always",
        "set_tasks_todo": "workspace",
        "set_show_analysis_manager": "workspace",
        "_toggle_notifications": "always",
        "_toggle_ether_ai": "always",
        "_toggle_python_console": "always",
        "_toggle_python_packages": "workspace",
        "_toggle_python_process_output": "always",
        "_toggle_outputs_window": "always",
        "_toggle_problems": "always",
        "_toggle_system_monitor": "always",
        "_toggle_git_source_control": "repo",
        "_toggle_server_explorer": "workspace",
        # ---- Code -----------------------------------------------------
        "set_format_code": "editable",
        "set_comment_current_line": "editable",
        "set_comment_current_selection": "selection",
        "set_uncomment_current_line": "editable",
        "set_uncomment_current_selection": "selection",
        "set_duplicate_current_line": "editable",
        "set_duplicate_current_selection": "selection",
        "set_goto_definition": "provider",
        "set_goto_declaration": "provider_declaration",
        "set_goto_implementation": "provider_implementation",
        "set_find_usages": "provider_references",
        "set_goto_symbol": "editor",
        "set_add_copyright": "editable",
        "set_update_copyright": "editable",
        "set_expand_current_fold": "folds",
        "set_expand_all_folds": "folds",
        "set_collapse_current_fold": "folds",
        "set_collapse_all_folds": "folds",
        "set_collapse_includes": "folds",
        # ---- Run ------------------------------------------------------
        "set_run_current_file": "runnable",
        "set_run_with_arguments": "runnable",
        "set_run_without_debugging": "runnable",
        "_debug_current_file": "runnable",
        "_stop_debug": "debug_running",
        "_restart_debug": "debug_running",
        "_step_over": "debug_paused",
        "_step_into": "debug_paused",
        "_step_out": "debug_paused",
        "_continue_debug": "debug_paused",
        "set_toggle_breakpoint": "editable",
        "set_enable_all_breakpoints": "breakpoints",
        "set_disable_all_breakpoints": "breakpoints",
        "set_remove_all_breakpoints": "breakpoints",
        # ---- File / Help ----------------------------------------------
        "set_import_configurations": "always",
        "set_export_configurations": "always",
        "set_open_settings": "always",
        "set_show_about": "always",
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

        self.icon_btn = QPushButton("    DreamStudio")
        self.icon_btn.setObjectName("iconButton")
        self.icon_btn.setIcon(QIcon(resource_path("assets/dreamStudio_icon.png")))
        self.icon_btn.setIconSize(QSize(26, 26))
        self.icon_btn.setFixedSize(120, 30)
        self.icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.icon_btn)

        self.menubar = QMenuBar(self)
        layout.addWidget(self.menubar)
        layout.addSpacing(30)

        self._ide_search = QLineEdit()
        self._ide_search.setObjectName("DreamStudioTitleBarSearch")
        self._ide_search.setPlaceholderText("Search Anywhere in DreamStudio")
        layout.addWidget(self._ide_search)

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

        for menu in self.menubar.findChildren(QMenu):
            try:
                menu.setToolTipsVisible(True)
                menu.aboutToShow.connect(self.refresh_action_states)
            except (TypeError, RuntimeError):
                pass

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
                if icon_path and os.path.exists(resource_path(icon_path)):
                    sub_menu = parent_menu.addMenu(
                        QIcon(resource_path(icon_path)), text
                    )
                else:
                    if icon_path:
                        logger.warning("Menu icon missing: %s", icon_path)
                    sub_menu = parent_menu.addMenu(text)
                self._build_menu_items(sub_menu, submenu_items)
            else:
                if icon_path and os.path.exists(resource_path(icon_path)):
                    action = QAction(QIcon(resource_path(icon_path)), text, self)
                else:
                    if icon_path:
                        logger.warning("Menu icon missing: %s", icon_path)
                    action = QAction(text, self)

                if action_str:
                    target = getattr(
                        self,
                        action_str,
                        getattr(self._title_parent, action_str, None),
                    )
                    if target:
                        action.triggered.connect(target)
                    elif action_str in self._UNAVAILABLE_ACTIONS:
                        action.triggered.connect(self._on_unavailable_action)

                if action_str in self._UNAVAILABLE_ACTIONS:
                    action.setEnabled(False)
                    action.setToolTip(self._UNAVAILABLE_TOOLTIP)

                if action_str in self._EDITOR_MENU_ACTIONS or (
                    action_str in self._ACTION_REQUIREMENTS
                ):
                    self._menu_actions[action_str] = action
                    if not any(m is parent_menu for m in self._refresh_menus):
                        self._refresh_menus.append(parent_menu)

                parent_menu.addAction(action)

    def _on_unavailable_action(self, _checked: bool = False) -> None:
        """Log a trigger of a menu entry that has no implementation yet."""
        sender = self.sender()
        label = sender.text() if sender is not None else "(unknown)"
        logger.info("Unavailable menu action triggered: %s", label)

    def _update_menu_state(self, has_tabs: bool) -> None:
        """Enable or disable editor-dependent menu actions."""
        for action_str in self._EDITOR_MENU_ACTIONS:
            action = self._menu_actions.get(action_str)
            if action is not None:
                action.setEnabled(has_tabs)
        self.refresh_action_states()

    def refresh_action_states(self) -> None:
        """Synchronize every editor-dependent menu action with the live state."""
        flags = self._editor_action_flags()
        for action_str, requirement in self._ACTION_REQUIREMENTS.items():
            action = self._menu_actions.get(action_str)
            if action is None:
                continue
            action.setEnabled(bool(flags.get(requirement, False)))

        self._bind_selection_tracking()
        self._sync_options_bar_action()

    def _editor_action_flags(self) -> dict[str, bool]:
        """Return the live capability flags of the active editor and workspace."""
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
            "provider_declaration": False,
            "provider_implementation": False,
            "provider_references": False,
            "folds": False,
            "breakpoints": False,
            "workspace": bool(self._workspace_path()),
            "repo": self._has_git_repository(),
            "runnable": self._active_file_is_runnable(),
            "debug_running": self._debug_is_running(),
            "debug_paused": self._debug_is_paused(),
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
        flags["folds"] = getattr(editor, "_fold_manager", None) is not None
        flags["breakpoints"] = self._has_breakpoints(editor)

        provider = getattr(editor, "current_provider", None)
        if provider is not None:
            flags["provider"] = True
            flags["provider_declaration"] = bool(
                getattr(provider, "supports_declaration", lambda: False)()
            )
            flags["provider_implementation"] = bool(
                getattr(provider, "supports_implementation", lambda: False)()
            )
            flags["provider_references"] = bool(
                getattr(provider, "supports_references", lambda: False)()
            )
        return flags

    def _workspace_path(self) -> str:
        """Return the active workspace root, or an empty string."""
        path = getattr(self._title_parent, "title_bar", None)
        directory = getattr(path, "directory", "") if path is not None else ""
        if directory:
            return str(directory)

        registry = getattr(self._title_parent, "_registry", None)
        if registry is not None and registry.has("workspace"):
            return str(getattr(registry.get("workspace"), "current_path", "") or "")
        return ""

    def _has_git_repository(self) -> bool:
        """Return ``True`` when the active workspace is a git repository."""
        path = self._workspace_path()
        if not path or not os.path.isdir(path):
            return False

        cached = getattr(self, "_repo_cache", None)
        if cached is not None and cached[0] == path:
            return cached[1]

        try:
            from editor.utils.git_control.git_control import return_repository

            result = return_repository(path) is not None
        except Exception:
            result = False

        self._repo_cache = (path, result)
        return result

    def _active_file_is_runnable(self) -> bool:
        """Return ``True`` when the active tab holds a runnable Python file."""
        controller = getattr(self._title_parent, "_run_menu", None)
        if controller is None:
            return False
        try:
            from editor.debugger.run.run_menu import is_runnable_python_file

            return is_runnable_python_file(controller.current_file_path())
        except Exception:
            return False

    def _debug_session(self):
        """Return the active debug session, or ``None``."""
        return getattr(self._title_parent, "_active_debug_session", None)

    def _debug_is_running(self) -> bool:
        """Return ``True`` while a debug session is alive."""
        session = self._debug_session()
        if session is None:
            return False
        try:
            return bool(session.is_running())
        except Exception:
            return False

    def _debug_is_paused(self) -> bool:
        """Return ``True`` while a debug session is stopped on a breakpoint."""
        session = self._debug_session()
        if session is None:
            return False
        try:
            return bool(session.is_paused())
        except Exception:
            return False

    @staticmethod
    def _has_breakpoints(editor) -> bool:
        """Return ``True`` when the editor holds armed or disabled breakpoints."""
        if editor is None:
            return False
        try:
            if editor.get_breakpoint_lines():
                return True
        except Exception:
            pass
        return bool(getattr(editor, "_disabled_breakpoints", None))

    def _active_code_editor(self):
        """Return the ``CodeEditor`` of the active tab, or ``None``."""
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

    def set_toggle_options_bar(self) -> None:
        """Toggle the options bar and keep this action's label in sync."""
        visible = self._title_parent.toggle_options_bar()
        self._sync_options_bar_action(visible)

    def _sync_options_bar_action(self, visible: Optional[bool] = None) -> None:
        """Make the options-bar action label match the real bar visibility."""
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
        """Draw the title bar with a horizontal gradient derived from the stylesheet."""
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

    def show_welcome(self) -> None:
        """Open the IDE welcome / start page tab."""
        handler = getattr(self._title_parent, "show_welcome", None)
        if callable(handler):
            handler()
            return

        center = getattr(self._title_parent, "_text_editor_center", None)
        tabs = getattr(center, "tabs", None)
        if tabs is not None:
            tabs.open_welcome_window()
