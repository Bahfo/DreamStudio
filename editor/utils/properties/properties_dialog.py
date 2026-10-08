from editor import *

# Local Imports
from editor.Ironica.code_editor import CodeEditor


class PropertyGridDelegate(QStyledItemDelegate):
    """
    Custom delegate providing themed editors tailored to field data
    length.
    """

    def createEditor(self, parent, option, index):
        if index.column() != 1:
            return None

        item = index.model().data(index, Qt.ItemDataRole.UserRole)
        is_multiline = item in ("details",)

        if is_multiline:
            editor = QTextEdit(parent)
            editor.setMinimumHeight(90)
            editor.setAcceptRichText(False)
            editor.setStyleSheet(
                "QTextEdit { background-color: #3F3F46; color: #F1F1F1; "
                "border: 1px solid #007ACC;"
            )
            return editor
        else:
            editor = QLineEdit(parent)
            editor.setStyleSheet(
                "QLineEdit { background-color: #3F3F46; color: #F1F1F1; "
                "border: 1px solid #007ACC; padding: 2px;"
            )
            return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.EditRole) or ""
        if isinstance(editor, QTextEdit):
            editor.setPlainText(value)
        else:
            editor.setText(value)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QTextEdit):
            value = editor.toPlainText()
        else:
            value = editor.text()
        model.setData(index, value, Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        if isinstance(editor, QTextEdit):
            geom = option.rect
            geom.setHeight(90)
            editor.setGeometry(geom)
        else:
            super().updateEditorGeometry(editor, option, index)


class SolutionPropertiesGrid(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderHidden(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAnimated(True)
        self.setIndentation(12)
        self.setRootIsDecorated(True)
        self.setEditTriggers(
            QTreeWidget.EditTrigger.DoubleClicked
            | QTreeWidget.EditTrigger.SelectedClicked
        )
        self.setStyleSheet(
            "QTreeView { border: none; background: transparent; color: #F1F1F1; }"
            "QTreeView::item { height: 24px; border-bottom: 1px solid #2D2D30; }"
            "QTreeView::item:hover { background-color: #333337; }"
            "QTreeView::item:selected { background-color: #3F3F46; color: #F1F1F1; }"
        )

        hdr = self.header()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 160)

        self.setItemDelegate(PropertyGridDelegate(self))
        self._create_categories()

    def _create_categories(self) -> None:
        self.cat_meta = QTreeWidgetItem(self)
        self.cat_meta.setText(0, "Project Metadata")
        self.cat_meta.setFlags(self.cat_meta.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.cat_meta.setExpanded(True)

        self.item_name = self._add_prop(self.cat_meta, "Unique Name", "name")
        self.item_authors = self._add_prop(self.cat_meta, "Authors", "authors")
        self.item_details = self._add_prop(self.cat_meta, "Detailed Info", "details")

        self.cat_legal = QTreeWidgetItem(self)
        self.cat_legal.setText(0, "Legal & Community")
        self.cat_legal.setFlags(self.cat_legal.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.cat_legal.setExpanded(True)

        self.item_copyright = self._add_prop(
            self.cat_legal, "Copyright Issue", "copyright"
        )
        self.item_conduct = self._add_status(
            self.cat_legal, "Code of Conduct", "code_of_conduct"
        )
        self.item_license = self._add_status(self.cat_legal, "License", "license")
        self.item_contrib = self._add_status(
            self.cat_legal, "Contributors Info", "contributing"
        )

        for cat in (self.cat_meta, self.cat_legal):
            for col in range(2):
                cat.setBackground(col, Qt.GlobalColor.transparent)
                font = cat.font(col)
                cat.setFont(col, font)

    def _add_prop(
        self, parent: QTreeWidgetItem, label: str, internal_key: str
    ) -> QTreeWidgetItem:
        child = QTreeWidgetItem(parent)
        child.setText(0, label)
        child.setText(1, "")
        # Store the internal key token inside the UserRole data slot
        child.setData(0, Qt.ItemDataRole.UserRole, internal_key)
        child.setData(1, Qt.ItemDataRole.UserRole, internal_key)
        child.setFlags(
            child.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable
        )
        return child

    def _add_status(
        self, parent: QTreeWidgetItem, label: str, internal_key: str
    ) -> QTreeWidgetItem:
        """Read-only presence row (Found / Not found), never edited/saved."""
        child = QTreeWidgetItem(parent)
        child.setText(0, label)
        child.setText(1, "Not found")
        child.setData(0, Qt.ItemDataRole.UserRole, internal_key)
        child.setData(1, Qt.ItemDataRole.UserRole, internal_key)
        child.setFlags(
            (child.flags() & ~Qt.ItemFlag.ItemIsEditable) | Qt.ItemFlag.ItemIsSelectable
        )
        return child

    def load_grid_data(self, data: dict) -> None:
        """
        Populates the grid fields using incoming file property
        structures.
        """
        self.item_name.setText(1, data.get("name", ""))
        self.item_authors.setText(1, data.get("authors", ""))
        self.item_details.setText(1, data.get("details", ""))
        self.item_copyright.setText(1, data.get("copyright", ""))
        self.item_conduct.setText(1, data.get("code_of_conduct", "Not found"))
        self.item_license.setText(1, data.get("license", "Not found"))
        self.item_contrib.setText(1, data.get("contributing", "Not found"))

        # Force tooltips to easily preview long values
        for item in (
            self.item_name,
            self.item_authors,
            self.item_details,
            self.item_copyright,
            self.item_conduct,
            self.item_license,
            self.item_contrib,
        ):
            val = item.text(1)
            item.setToolTip(1, val if val else "--")

    def save_grid_data(self) -> dict:
        """
        Harvests updated input strings from fields to compile into update
        blocks.
        """
        return {
            "name": self.item_name.text(1),
            "authors": self.item_authors.text(1),
            "details": self.item_details.text(1),
            "copyright": self.item_copyright.text(1),
        }


class FilePropertiesGrid(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderHidden(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAnimated(True)
        self.setIndentation(12)
        self.setRootIsDecorated(True)
        self.setStyleSheet(
            "QTreeView { border: none; background: transparent; color: #F1F1F1; }"
            "QTreeView::item { height: 26px; border-bottom: 1px solid #2D2D30; }"
            "QTreeView::item:hover { background-color: #333337; }"
            "QTreeView::item:selected { background-color: #3F3F46; color: #F1F1F1; }"
        )

        hdr = self.header()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 130)

        self._active_editor = None
        self._display_to_lang: dict[str, str] = {}
        self._create_categories()
        self._create_interactive_widgets()

    def _create_categories(self) -> None:
        self.cat_file = QTreeWidgetItem(self)
        self.cat_file.setText(0, "File System")
        self.cat_file.setExpanded(True)

        self.item_name = self._add_prop(self.cat_file, "File Name")
        self.item_path = self._add_prop(self.cat_file, "Absolute Path")
        self.item_size = self._add_prop(self.cat_file, "Size On Disk")
        self.item_created = self._add_prop(self.cat_file, "Date Created")
        self.item_timestamp = self._add_prop(self.cat_file, "Timestamp")

        self.cat_config = QTreeWidgetItem(self)
        self.cat_config.setText(0, "Configuration")
        self.cat_config.setExpanded(True)

        self.item_lang = self._add_prop(self.cat_config, "Language")
        self.item_ext = self._add_prop(self.cat_config, "Extension")
        self.item_editable = self._add_prop(self.cat_config, "Is Editable")

        self.cat_metrics = QTreeWidgetItem(self)
        self.cat_metrics.setText(0, "Editor State")
        self.cat_metrics.setExpanded(True)

        self.item_lines = self._add_prop(self.cat_metrics, "Total Lines")
        self.item_cursor = self._add_prop(self.cat_metrics, "Cursor Position")

        for cat in (self.cat_file, self.cat_config, self.cat_metrics):
            cat.setFlags(cat.flags() & ~Qt.ItemFlag.ItemIsEditable)
            for col in range(2):
                cat.setBackground(col, Qt.GlobalColor.transparent)
                cat.setForeground(col, Qt.GlobalColor.white)
                font = cat.font(col)
                font.setBold(True)
                cat.setFont(col, font)

    def _add_prop(self, parent: QTreeWidgetItem, label: str) -> QTreeWidgetItem:
        child = QTreeWidgetItem(parent)
        child.setText(0, label)
        child.setText(1, "--")
        child.setFlags(child.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return child

    @staticmethod
    def _language_choices() -> list[tuple[str, str]]:
        """Return display-name and registry-id pairs for installed languages."""
        try:
            from editor.Ironica.language_engine import LanguageRegistry

            choices: list[tuple[str, str]] = []
            used: set[str] = set()
            for lang_id in LanguageRegistry.list_languages():
                display_name = LanguageRegistry.get_display_name(lang_id)
                if display_name in used:
                    display_name = f"{display_name} ({lang_id})"
                used.add(display_name)
                choices.append((display_name, lang_id))
            return sorted(choices)
        except Exception:
            return []

    @staticmethod
    def _extension_choices() -> list[str]:
        """Return every file extension claimed by an installed language."""
        try:
            from editor.Ironica.language_engine import LanguageRegistry

            return sorted(LanguageRegistry.get_all_extensions())
        except Exception:
            return []

    def refresh_choices(self) -> None:
        """Rebuild language and extension combos from the registry.

        Safe to call any time; preserves the current selection when
        possible. Used when language plugins register after this grid
        was constructed.
        """
        self._refresh_language_choices()
        self._refresh_extension_choices()

    def _refresh_language_choices(self) -> None:
        """Rebuild the language combo from the current language registry."""
        current = self.combo_lang.currentText()
        self.combo_lang.blockSignals(True)
        try:
            self.combo_lang.clear()
            self.combo_lang.addItem("--")
            self._display_to_lang = {}
            for display_name, lang_id in self._language_choices():
                self.combo_lang.addItem(display_name)
                self._display_to_lang[display_name] = lang_id
            index = self.combo_lang.findText(current)
            self.combo_lang.setCurrentIndex(index if index != -1 else 0)
        finally:
            self.combo_lang.blockSignals(False)

    def _refresh_extension_choices(self) -> None:
        """Rebuild the extension combo from the current language registry."""
        current = self.combo_ext.currentText()
        self.combo_ext.blockSignals(True)
        try:
            self.combo_ext.clear()
            self.combo_ext.addItem("--")
            self.combo_ext.addItems(self._extension_choices())
            index = self.combo_ext.findText(current)
            self.combo_ext.setCurrentIndex(index if index != -1 else 0)
        finally:
            self.combo_ext.blockSignals(False)

    def _create_interactive_widgets(self) -> None:
        """Instantiates and links VS-styled inline editor widgets into column 1."""
        combo_style = (
            "QComboBox { background-color: #1F1F1F; color: #F1F1F1; border: none; "
            "padding-left: 2px; }"
            "QComboBox::drop-down { border: none; width: 16px; }"
            "QComboBox QAbstractItemView { background-color: #2D2D30; color: #F1F1F1; "
            "selection-background-color: #3F3F46; border: 1px solid #3E3E42; }"
        )

        self.combo_lang = QComboBox()
        self.combo_lang.addItem("--")
        self.combo_lang.setStyleSheet(combo_style)
        self.setItemWidget(self.item_lang, 1, self.combo_lang)
        self._refresh_language_choices()
        self._last_valid_lang = self.combo_lang.currentText()
        self.combo_lang.currentTextChanged.connect(self._on_language_selected)

        self.combo_ext = QComboBox()
        self.combo_ext.addItem("--")
        self.combo_ext.setStyleSheet(combo_style)
        self.setItemWidget(self.item_ext, 1, self.combo_ext)
        self._refresh_extension_choices()
        self.combo_ext.currentTextChanged.connect(self._on_extension_selected)

        # 3. Editable Policy Switcher
        self.combo_editable = QComboBox()
        self.combo_editable.addItems(["True", "False"])
        self.combo_editable.setStyleSheet(combo_style)
        self.setItemWidget(self.item_editable, 1, self.combo_editable)
        self.combo_editable.currentTextChanged.connect(self._on_editable_selected)

    def set_active_editor(self, editor: CodeEditor | None) -> None:
        """
        Binds tracking event loops directly to the chosen active editor target
        instance.
        """
        if self._active_editor:
            for signal_name in ("cursorPositionChanged", "textChanged"):
                try:
                    signal = getattr(self._active_editor, signal_name, None)
                    if signal is not None and hasattr(signal, "disconnect"):
                        signal.disconnect(self.refresh_editor_metrics)
                except Exception:
                    pass

        self._active_editor = editor

        if self._active_editor:
            for signal_name in ("cursorPositionChanged", "textChanged"):
                try:
                    signal = getattr(self._active_editor, signal_name, None)
                    if signal is not None and hasattr(signal, "connect"):
                        signal.connect(self.refresh_editor_metrics)
                except Exception:
                    pass
            self.refresh_static_file_info()
            self.refresh_editor_metrics()
        else:
            self.clear_grid()

    def refresh_static_file_info(self) -> None:
        """
        Extracts fixed file system history attributes and matches configuration
        profiles.
        """
        if not self._active_editor:
            return

        self._refresh_language_choices()
        self._refresh_extension_choices()
        file_path = getattr(self._active_editor, "current_file_path", None) or ""
        if not file_path or not os.path.exists(file_path):
            self.item_name.setText(1, "Unsaved Document")
            self.item_path.setText(1, "Memory Cache")
            self.item_size.setText(1, "0 KB")
            self.item_created.setText(1, "--")
            self.item_timestamp.setText(1, "--")
            for combo in (self.combo_lang, self.combo_ext):
                try:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(0)
                finally:
                    try:
                        combo.blockSignals(False)
                    except Exception:
                        pass
            return

        info = QFileInfo(file_path)
        self.item_name.setText(1, info.fileName())
        self.item_path.setText(1, info.absoluteFilePath())

        size_kb = max(1, round(info.size() / 1024))
        self.item_size.setText(1, f"{size_kb} KB")

        fmt = "yyyy-MM-dd hh:mm:ss"
        birth = info.birthTime()
        if not birth.isValid():
            birth = info.metadataChangeTime()

        self.item_created.setText(1, birth.toString(fmt))
        self.item_timestamp.setText(1, info.lastModified().toString(fmt))

        try:
            self.combo_ext.blockSignals(True)
            ext = f".{info.suffix().lower()}"
            idx_ext = self.combo_ext.findText(ext)
            self.combo_ext.setCurrentIndex(idx_ext if idx_ext != -1 else 0)
        finally:
            try:
                self.combo_ext.blockSignals(False)
            except Exception:
                pass

        lang_map = {}
        try:
            from editor.Ironica.language_engine import LanguageRegistry

            lang_id = LanguageRegistry.get_language_by_extension(ext)
            if lang_id:
                lang_map = {ext: LanguageRegistry.get_display_name(lang_id)}
        except Exception:
            lang_map = {}
        try:
            self.combo_lang.blockSignals(True)
            target_lang = lang_map.get(ext, "")
            idx_lang = self.combo_lang.findText(target_lang) if target_lang else -1
            self.combo_lang.setCurrentIndex(idx_lang if idx_lang != -1 else 0)
            self._last_valid_lang = self.combo_lang.currentText()
        finally:
            try:
                self.combo_lang.blockSignals(False)
            except Exception:
                pass

        try:
            self.combo_editable.blockSignals(True)
            editable = True
            try:
                if hasattr(self._active_editor, "isReadOnly"):
                    editable = not bool(self._active_editor.isReadOnly())
            except Exception:
                editable = True
            self.combo_editable.setCurrentIndex(0 if editable else 1)
        finally:
            try:
                self.combo_editable.blockSignals(False)
            except Exception:
                pass

        for item in (
            self.item_name,
            self.item_path,
            self.item_created,
            self.item_timestamp,
        ):
            item.setToolTip(1, item.text(1))

    def refresh_editor_metrics(self, *args) -> None:
        """Show live line count and cursor position for the active editor."""
        if not self._active_editor:
            return

        if hasattr(self._active_editor, "lines"):
            total_lines = self._active_editor.lines()
        else:
            total_lines = self._active_editor.text().count("\n") + 1
        self.item_lines.setText(1, str(total_lines))

        line, col = 0, 0
        if hasattr(self._active_editor, "getCursorPosition"):
            line, col = self._active_editor.getCursorPosition()
        self.item_cursor.setText(1, f"Ln {line + 1}, Col {col + 1}")

    def _on_language_selected(self, language: str) -> None:
        """Preview highlighting temporarily; reopening restores the default.

        Display names are mapped to registry ids; unregistered languages
        leave the current lexer untouched so highlighting never breaks.
        """
        if not language or language == "--":
            return
        editor = self._active_editor
        if editor is None:
            return
        lang_id = self._display_to_lang.get(language, "")
        if not lang_id:
            return
        try:
            from editor.Ironica.language_engine import LanguageRegistry

            if not LanguageRegistry.is_registered(lang_id):
                self._revert_language_combo()
                return
        except Exception:
            pass
        try:
            if hasattr(editor, "apply_visual_language"):
                editor.apply_visual_language(lang_id)
            elif hasattr(editor, "setLanguage"):
                editor.setLanguage(lang_id)
            self._last_valid_lang = language
        except Exception:
            pass

    def _revert_language_combo(self) -> None:
        """Restore the combo to the last working language selection."""
        try:
            self.combo_lang.blockSignals(True)
            previous = getattr(self, "_last_valid_lang", "--")
            idx = self.combo_lang.findText(previous)
            self.combo_lang.setCurrentIndex(idx if idx != -1 else 0)
        finally:
            try:
                self.combo_lang.blockSignals(False)
            except Exception:
                pass

    def _on_extension_selected(self, extension: str) -> None:
        """Rename the file on disk and refresh its configs/highlighting."""
        if not extension or extension == "--":
            return
        editor = self._active_editor
        if editor is None:
            return
        current = getattr(editor, "current_file_path", None) or ""
        if not current or not os.path.isfile(current):
            return
        root, _old_ext = os.path.splitext(current)
        target = root + extension
        if os.path.abspath(target) == os.path.abspath(current):
            return
        if os.path.exists(target):
            try:
                self.combo_ext.blockSignals(True)
                current_ext = f".{QFileInfo(current).suffix().lower()}"
                idx = self.combo_ext.findText(current_ext)
                if idx != -1:
                    self.combo_ext.setCurrentIndex(idx)
            finally:
                try:
                    self.combo_ext.blockSignals(False)
                except Exception:
                    pass
            return
        try:
            os.rename(current, target)
        except OSError:
            return
        try:
            editor.current_file_path = target
        except Exception:
            pass
        try:
            from editor.Ironica.language_engine import LanguageRegistry

            new_lang = LanguageRegistry.get_language_by_extension(extension)
        except Exception:
            new_lang = None
        try:
            if hasattr(editor, "setLanguage"):
                editor.setLanguage(new_lang or "")
            try:
                editor.retheme(
                    getattr(editor, "_theme_name", None) or editor._active_theme()
                )
            except Exception:
                pass
        except Exception:
            pass
        try:
            self._sync_renamed_tab(current, target)
        except Exception:
            pass
        try:
            self.refresh_static_file_info()
            self.refresh_editor_metrics()
        except Exception:
            pass

    def _sync_renamed_tab(self, old_path: str, new_path: str) -> None:
        """Point the open tab at the renamed file (title, key, index)."""
        try:
            top = self.window()
            hero = getattr(top, "hero_window", None)
            center = getattr(hero, "_text_editor_center", None)
            tabs = getattr(center, "tabs", None)
            if tabs is None:
                return
            try:
                from editor.Ironica.tab_editor import DreamTabbedEditor
            except Exception:
                DreamTabbedEditor = None  # type: ignore
            old_key = None
            new_key = None
            if DreamTabbedEditor is not None and hasattr(
                DreamTabbedEditor, "resolve_key"
            ):
                try:
                    old_key = DreamTabbedEditor.resolve_key(old_path)
                    new_key = DreamTabbedEditor.resolve_key(new_path)
                except Exception:
                    pass
            for index in range(tabs.count()):
                try:
                    widget = tabs.widget(index)
                except Exception:
                    continue
                try:
                    from editor.Ironica.utils.minimap import ensure_inner

                    inner = ensure_inner(widget) or widget
                except Exception:
                    inner = widget
                if inner is not self._active_editor:
                    continue
                try:
                    if old_key and new_key and hasattr(tabs, "opened_files"):
                        mapping = getattr(tabs, "opened_files", None)
                        if isinstance(mapping, dict):
                            mapping.pop(old_key, None)
                            mapping[new_key] = index
                    try:
                        widget.file_key = new_key or getattr(widget, "file_key", None)
                    except Exception:
                        pass
                    tabs.setTabText(index, os.path.basename(new_path))
                except Exception:
                    pass
                return
        except Exception:
            pass

    def _on_editable_selected(self, value: str) -> None:
        """Toggle read-only via the existing options-bar editor API."""
        editor = self._active_editor
        if editor is None:
            return
        try:
            currently_editable = True
            if hasattr(editor, "isReadOnly"):
                currently_editable = not bool(editor.isReadOnly())
        except Exception:
            currently_editable = True
        want_editable = str(value) == "True"
        if want_editable == currently_editable:
            return
        try:
            top = self.window()
            tabs = None
            try:
                hero = getattr(top, "hero_window", None)
                center = getattr(hero, "_text_editor_center", None)
                tabs = getattr(center, "tabs", None)
            except Exception:
                tabs = None
            if tabs is not None and hasattr(tabs, "_make_file_readonly"):
                tabs._make_file_readonly()
            elif hasattr(editor, "make_file_readonly"):
                editor.make_file_readonly()
        except Exception:
            pass
        try:
            self.refresh_static_file_info()
        except Exception:
            pass

    def clear_grid(self) -> None:
        """
        Reverts visual field components back to default baseline characters.
        """
        for item in (
            self.item_name,
            self.item_path,
            self.item_size,
            self.item_created,
            self.item_timestamp,
            self.item_lines,
            self.item_cursor,
        ):
            item.setText(1, "--")
            item.setToolTip(1, "")
        self.combo_lang.setCurrentIndex(0)
        self.combo_ext.setCurrentIndex(0)
        self.combo_editable.setCurrentIndex(0)
