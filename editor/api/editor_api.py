import re

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QColor

# Local Imports
from editor.utils.find_replace.find_replace import FindReplace


class EditorAPI:
    """Mixin that holds all editor API callbacks (toggles, theme setters,
    file operations, clipboard actions, status updates, etc.).

    Designed to be mixed into the DreamStudio QMainWindow so that
    ``getattr(self, callback_name)`` dispatch still works.
    """

    # ------------------------------------------------------------------
    # Panel toggles
    # ------------------------------------------------------------------

    def _toggle_file_explorer(self) -> None:
        api = self.hero_window._vertical_menus_api
        if api.is_visible("solution_explorer"):
            self.hero_window._left_utils_manager.set_current_panel("solution_explorer")
        else:
            api.activate_panel("solution_explorer")

    def _toggle_git_source_control(self) -> None:
        api = self.hero_window._vertical_menus_api
        if api.is_visible("source_control"):
            self.hero_window._left_utils_manager.set_current_panel("source_control")
        else:
            api.activate_panel("source_control")

    def _toggle_properties(self) -> None:
        api = self.hero_window._vertical_menus_api
        if api.is_visible("properties"):
            self.hero_window._right_utils_manager.set_current_panel("properties")
        else:
            api.activate_panel("properties")

    def _toggle_todo_search(self) -> None:
        api = self.hero_window._vertical_menus_api
        if api.is_visible("todo_search"):
            self.hero_window._right_utils_manager.set_current_panel("todo_search")
        else:
            api.activate_panel("todo_search")

    def _toggle_terminal(self) -> None:
        terminal = self.hero_window.terminal_window
        splitter = self.hero_window._main_vertical_splitter
        if terminal.isVisible():
            terminal.setVisible(False)
            splitter.setSizes([1, 0])
        else:
            terminal.setVisible(True)
            splitter.setSizes([600, 400])
            terminal.switch_tab(0)

    def _toggle_search_widget(self) -> None:
        if (
            not hasattr(self, "_find_replace_window")
            or self._find_replace_window is None
        ):
            self._find_replace_window = FindReplace(
                parent=self,
                hanging_widget=self.title_bar._ide_search,
                current_directory=self.title_bar.directory,
            )
            self._find_replace_window.setStyleSheet(self.styleSheet())

        if self._find_replace_window.isVisible():
            self._find_replace_window.hide()
        else:
            self._find_replace_window._show()

    def _open_toolbox(self) -> None:
        self.hero_window._text_editor_center.tabs.open_designer_tab()

    # ------------------------------------------------------------------
    # Sidebar button state
    # ------------------------------------------------------------------

    def _update_left_button_state(self, active_id: str) -> None:
        buttons = self.left_sidebar.findChildren(QPushButton)
        for btn in buttons:
            btn.setChecked(False)
        idx = {
            "solution_explorer": 0,
            "source_control": 2,
        }.get(active_id)
        if idx is not None and idx < len(buttons):
            buttons[idx].setChecked(True)

    def _on_panel_visibility_changed(self, panel_id: str, visible: bool) -> None:
        if panel_id not in (
            "solution_explorer",
            "source_control",
        ):
            return
        if visible:
            self._update_left_button_state(panel_id)
        else:
            api = self.hero_window._vertical_menus_api
            for pid in (
                "solution_explorer",
                "source_control",
            ):
                if api.is_visible(pid):
                    self._update_left_button_state(pid)
                    return
            buttons = self.left_sidebar.findChildren(QPushButton)
            for btn in buttons:
                btn.setChecked(False)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _new_file(self) -> None:
        self.hero_window._text_editor_center.methods.open_new_tab()

    def _open_file(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")
        if path:
            self.hero_window._text_editor_center.methods.open_file(path)

    def _save_file(self) -> None:
        self.hero_window._text_editor_center.methods.save_current()

    def _save_all_files(self) -> None:
        self.hero_window._text_editor_center.methods.save_all()

    # ------------------------------------------------------------------
    # Clipboard & undo/redo
    # ------------------------------------------------------------------

    def _cut_text(self) -> None:
        api = self.hero_window._text_editor_center.methods.current_editor()
        if api:
            api.cut()

    def _copy_text(self) -> None:
        api = self.hero_window._text_editor_center.methods.current_editor()
        if api:
            api.copy()

    def _paste_text(self) -> None:
        api = self.hero_window._text_editor_center.methods.current_editor()
        if api:
            api.paste()

    def _undo_action(self) -> None:
        api = self.hero_window._text_editor_center.methods.current_editor()
        if api:
            api.undo()

    def _redo_action(self) -> None:
        api = self.hero_window._text_editor_center.methods.current_editor()
        if api:
            api.redo()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme_content(self, content: str) -> None:
        """Apply a QSS stylesheet string and propagate colours to child widgets.

        This is the single internal method that all theme application
        ultimately reaches.  It injects the user-configured font-family
        into the global ``QMainWindow, QWidget`` rule before applying,
        so the setting survives theme switches.
        """
        font_family = self._get_configured_font_family()
        if font_family:
            content = self._inject_font_family(content, font_family)
        self.setStyleSheet(content)

        self._qss_bg = (
            self._extract_qss_color(
                content, r"QMainWindow\s*,\s*QWidget", "background-color"
            )
            or "#1E1E1E"
        )
        self._qss_fg = (
            self._extract_qss_color(content, r"QMainWindow\s*,\s*QWidget", "color")
            or "#CCCCCC"
        )
        self._qss_sel = (
            self._extract_qss_color(
                content, r"UtilityTabBar::tab:selected", "background-color"
            )
            or self._qss_bg
        )

        self.current_theme = (
            "dark" if QColor(self._qss_bg).lightness() < 128 else "light"
        )
        self._apply_custom_theme()
        self._retheme_editors()

    def _set_theme_by_name(self, name: str) -> None:
        """Load a theme by name through ResourceManager and apply it.

        When a bootstrap ``ServiceRegistry`` with a ``resource_manager``
        is available the theme content is obtained from there.  Otherwise
        falls back to a direct file read via ``_parse_styleSheet``.
        """
        self._current_theme_name = name
        resource_manager = self._get_resource_manager()
        if resource_manager is not None:
            content = resource_manager.load_theme(name)
            if content:
                self._apply_theme_content(content)
                return

        # Fallback: direct file read (e.g. during testing without registry).
        self._parse_styleSheet(f"editor/qss/{name}.qss")

    def _toggle_theme(self) -> None:
        alt = "light" if self.current_theme == "dark" else "dark"
        self._set_theme_by_name(alt)

    def _set_theme_dark(self) -> None:
        self._set_theme_by_name("dark")

    def _set_theme_light(self) -> None:
        self._set_theme_by_name("light")

    def _set_theme_moses(self) -> None:
        self._set_theme_by_name("moses")

    def _set_theme_davy(self) -> None:
        self._set_theme_by_name("davy")

    def _set_theme_tokyonight(self) -> None:
        self._set_theme_by_name("tokyonight")

    def _set_theme_solarized_dark(self) -> None:
        self._set_theme_by_name("solarized_dark")

    def _set_theme_solarized_light(self) -> None:
        self._set_theme_by_name("solarized_light")

    def _set_theme_monokai(self) -> None:
        self._set_theme_by_name("monokai")

    def _set_theme_dark_hc(self) -> None:
        self._set_theme_by_name("dark_hc")

    def _set_theme_light_hc(self) -> None:
        self._set_theme_by_name("light_hc")

    def _set_theme_coffee_dark(self) -> None:
        self._set_theme_by_name("coffee_dark")

    def _set_theme_coffee_light(self) -> None:
        self._set_theme_by_name("coffee_light")

    def _apply_custom_theme(self) -> None:
        self.hero_window.set_theme(self._qss_bg, self._qss_fg, self._qss_sel)
        self.hero_window.terminal_window.set_theme(
            self._qss_bg, self._qss_fg, self._qss_sel
        )

    def _retheme_editors(self) -> None:
        """Re-colour every open code editor to match the current theme."""
        from editor.Ironica.retheme import RethemeEngine

        try:
            RethemeEngine.apply_current(self)
        except Exception:
            pass

    def _get_resource_manager(self):
        """Return the bootstrap ResourceManager if available, else ``None``."""
        registry = getattr(self, "_registry", None)
        if registry is not None and registry.has("resource_manager"):
            return registry.get("resource_manager")
        return None

    def _parse_styleSheet(self, qss_file: str) -> None:
        """Load a QSS file and apply it.

        When a bootstrap ``ResourceManager`` is available, the file is
        loaded through it (benefiting from caching and fallback logic).
        Otherwise reads directly from disk.
        """
        import os as _os

        theme_name = _os.path.splitext(_os.path.basename(qss_file))[0]
        self._current_theme_name = theme_name

        resource_manager = self._get_resource_manager()
        if resource_manager is not None:
            content = resource_manager.load_theme(theme_name)
            if content:
                self._apply_theme_content(content)
                return

        try:
            with open(qss_file, "r") as file:
                content = file.read()
        except OSError:
            return

        self._apply_theme_content(content)

    @staticmethod
    def _extract_qss_color(
        qss_content: str, selector_re: str, property_name: str
    ) -> str | None:
        pattern = re.compile(
            rf"{selector_re}\s*\{{[^}}]*{property_name}\s*:\s*([^;\s}}]+)",
            re.IGNORECASE | re.DOTALL,
        )
        m = pattern.search(qss_content)
        return m.group(1).strip() if m else None

    # ------------------------------------------------------------------
    # Global IDE font (applied everywhere except code editors)
    # ------------------------------------------------------------------

    def _get_configured_font_family(self) -> str | None:
        """Read the configured font family from the bootstrap config.

        Returns the family name string, or ``None`` if no config is
        available or the value is empty.
        """
        registry = getattr(self, "_registry", None)
        if registry is None:
            return None
        if not registry.has("config"):
            return None
        config = registry.get("config")
        editor_cfg = config.get("editor", {}) if isinstance(config, dict) else {}
        return editor_cfg.get("font_family")

    @staticmethod
    def _inject_font_family(qss: str, family: str) -> str:
        """Inject or replace ``font-family`` in the global widget rule.

        If a ``font-family`` declaration already exists inside the
        ``QMainWindow, QWidget`` block it is replaced.  Otherwise the
        property is appended to that block.
        """
        family_value = f'"{family}", "Segoe UI", "Inter", Arial, sans-serif'
        pattern = re.compile(
            r"(QMainWindow\s*,\s*QWidget\s*\{[^}]*?)" r"font-family\s*:\s*[^;]+;",
            re.IGNORECASE | re.DOTALL,
        )
        if pattern.search(qss):
            qss = pattern.sub(rf"\1font-family: {family_value};", qss)
        else:
            qss = re.sub(
                r"(QMainWindow\s*,\s*QWidget\s*\{)\s*\n",
                rf"\1\n    font-family: {family_value};\n",
                qss,
                count=1,
            )
        return qss

    def set_global_font(self, font_name: str) -> None:
        """Set the global UI font across the entire IDE.

        Re-applies the current theme with the new font injected, so
        all colours, borders, and sizing are preserved.  Code editors
        are unaffected — they manage their own monospace font
        independently via ``DreamTabbedEditor.set_editor_font_by_name``.

        Args:
            font_name: Font family name — use ``Fonts.FONT_INTER``,
                       ``Fonts.FONT_SEGOE_UI``, or any installed family.
        """
        # Persist to config so the choice survives restarts.
        registry = getattr(self, "_registry", None)
        if registry is not None and registry.has("config"):
            config = registry.get("config")
            if isinstance(config, dict):
                config.setdefault("editor", {})["font_family"] = font_name

        # Re-apply the current theme with the new font injected.
        resource_manager = self._get_resource_manager()
        theme_name = getattr(self, "_current_theme_name", None)
        if resource_manager is not None and theme_name:
            content = resource_manager.load_theme(theme_name)
            if content:
                content = self._inject_font_family(content, font_name)
                self.setStyleSheet(content)
                self._apply_custom_theme()
                return

        # Fallback: inject into whatever stylesheet is currently active.
        current = self.styleSheet()
        if current:
            self.setStyleSheet(self._inject_font_family(current, font_name))

    # ------------------------------------------------------------------
    # Editor state & status
    # ------------------------------------------------------------------

    def _get_current_editor(self):
        return self.hero_window._text_editor_center.current_editor()

    def update_editor_visibility(self) -> None:
        pass

    def update_position_status(self) -> None:
        api = self._get_current_editor()
        if api is None:
            return
        editor = api.editor
        line, col = editor.getCursorPosition()
        self.status_bar.lines_and_cols.setText(f"Ln {line + 1} : Col {col + 1}")

    # ------------------------------------------------------------------
    # Debugging
    # ------------------------------------------------------------------

    def _debug_current_file(self) -> None:
        """Launch a debug session for the active editor.

        Guard conditions (Edge Case 3 — button state collision):
        If a debug session is already running, this is a no-op so that
        switching tabs and re-clicking cannot launch a second session.

        Auto-save (Edge Case 2 — unsaved changes):
        If the editor buffer is dirty the file is saved to disk before
        breakpoints are collected so that the on-disk file and the
        editor display stay in sync.
        """
        # Edge Case 3: prevent double-launch while session is active.
        active = getattr(self, "_active_debug_session", None)
        if active is not None and active.is_running():
            return

        tabs = self.hero_window._text_editor_center.tabs
        widget = tabs.currentWidget()

        # No file open.
        if widget is None:
            return

        file_path = getattr(widget, "current_file_path", None)
        if not file_path:
            return

        # Not a .py file.
        if not file_path.endswith(".py"):
            return

        # Edge Case 2: auto-save dirty buffer before debugging.
        if hasattr(widget, "isModified") and widget.isModified():
            if hasattr(widget, "save"):
                widget.save()

        # Gather breakpoints from the editor.
        breakpoints = set()
        if hasattr(widget, "get_breakpoint_lines"):
            breakpoints = widget.get_breakpoint_lines()

        # Warn if no breakpoints are set.
        if not breakpoints:
            from editor.widgets.QExitDialog import ConfirmDialog

            dlg = ConfirmDialog(
                parent=self,
                title="Warning",
                message="No breakpoints are initialized.\nStart debugging anyway?",
                confirm_text="START",
                cancel_text="CANCEL",
            )
            if dlg.exec() != ConfirmDialog.DialogCode.Accepted:
                return

        from editor.debugger.python_debug import DebugSession

        session = DebugSession(file_path, breakpoints, self)
        self._active_debug_session = session

        # Expose the options-bar debug button so the session can
        # re-enable it on stop (Edge Case 3).
        self._debug_btn_ref = getattr(self.options_menu, "_debug_button", None)

        session.start()

    def _stop_debug(self) -> None:
        active = getattr(self, "_active_debug_session", None)
        if active is not None and active.is_running():
            active.stop()
        self._active_debug_session = None

    def _continue_debug(self) -> None:
        active = getattr(self, "_active_debug_session", None)
        if active is not None and active.is_running():
            active.continue_execution()

    def _restart_debug(self) -> None:
        active = getattr(self, "_active_debug_session", None)
        if active is not None:
            active.restart()

    def _step_over(self) -> None:
        active = getattr(self, "_active_debug_session", None)
        if active is not None and active.is_running():
            active.step_over()

    def _step_into(self) -> None:
        active = getattr(self, "_active_debug_session", None)
        if active is not None and active.is_running():
            active.step_into()

    def _step_out(self) -> None:
        active = getattr(self, "_active_debug_session", None)
        if active is not None and active.is_running():
            active.step_out()

    def stop_all_debug_utils(self) -> None:
        """Terminate any active debug session and reset all debug UI."""
        active = getattr(self, "_active_debug_session", None)
        if active is not None:
            try:
                active.stop()
            except Exception:
                pass
            self._active_debug_session = None
