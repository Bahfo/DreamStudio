import os

from PyQt6.QtCore import Qt, QFileInfo
from PyQt6.QtWidgets import (
    QFrame,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QTreeWidget,
    QHeaderView,
    QTreeWidgetItem,
    QStyledItemDelegate,
)

# Local Imports
from editor.texteditor.code_editor import CodeEditor


class PropertyGridDelegate(QStyledItemDelegate):
    """
    Custom delegate providing themed editors tailored to field data
    length.
    """

    def createEditor(self, parent, option, index):
        if index.column() != 1:
            return None

        item = index.model().data(index, Qt.ItemDataRole.UserRole)
        is_multiline = item in ("details", "code_of_conduct", "license", "contributing")

        if is_multiline:
            editor = QTextEdit(parent)
            editor.setMinimumHeight(90)
            editor.setAcceptRichText(False)
            editor.setStyleSheet(
                "QTextEdit { background-color: #3F3F46; color: #F1F1F1; "
                "border: 1px solid #007ACC; font-family: 'Segoe UI'; }"
            )
            return editor
        else:
            editor = QLineEdit(parent)
            editor.setStyleSheet(
                "QLineEdit { background-color: #3F3F46; color: #F1F1F1; "
                "border: 1px solid #007ACC; font-family: 'Segoe UI'; padding: 2px; }"
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
        self.item_conduct = self._add_prop(
            self.cat_legal, "Code of Conduct", "code_of_conduct"
        )
        self.item_contrib = self._add_prop(
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

    def load_grid_data(self, data: dict) -> None:
        """
        Populates the grid fields using incoming file property
        structures.
        """
        self.item_name.setText(1, data.get("name", ""))
        self.item_authors.setText(1, data.get("authors", ""))
        self.item_details.setText(1, data.get("details", ""))
        self.item_copyright.setText(1, data.get("copyright", ""))
        self.item_conduct.setText(1, data.get("code_of_conduct", ""))
        self.item_contrib.setText(1, data.get("contributing", ""))

        # Force tooltips to easily preview long values
        for item in (
            self.item_name,
            self.item_authors,
            self.item_details,
            self.item_copyright,
            self.item_conduct,
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
            "code_of_conduct": self.item_conduct.text(1),
            "contributing": self.item_contrib.text(1),
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
        self.item_symbol = self._add_prop(self.cat_metrics, "Active Token")

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

    def _create_interactive_widgets(self) -> None:
        """Instantiates and links VS-styled inline editor widgets into column 1."""
        combo_style = (
            "QComboBox { background-color: #1F1F1F; color: #F1F1F1; border: none; "
            "padding-left: 2px; font-family: 'Segoe UI'; }"
            "QComboBox::drop-down { border: none; width: 16px; }"
            "QComboBox QAbstractItemView { background-color: #2D2D30; color: #F1F1F1; "
            "selection-background-color: #3F3F46; border: 1px solid #3E3E42; }"
        )

        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Bash", "C", "C++", "D", "Python", "PowerShell"])
        self.combo_lang.setStyleSheet(combo_style)
        self.setItemWidget(self.item_lang, 1, self.combo_lang)

        self.combo_ext = QComboBox()
        self.combo_ext.addItems(
            [
                ".bash",
                ".sh",
                ".c",
                ".h",
                ".m",
                ".hpp",
                ".cpp",
                ".d",
                ".py",
                ".pyi",
                ".ps1",
            ]
        )
        self.combo_ext.setStyleSheet(combo_style)
        self.setItemWidget(self.item_ext, 1, self.combo_ext)

        # 3. Editable Policy Switcher
        self.combo_editable = QComboBox()
        self.combo_editable.addItems(["True", "False"])
        self.combo_editable.setStyleSheet(combo_style)
        self.setItemWidget(self.item_editable, 1, self.combo_editable)

    def set_active_editor(self, editor: CodeEditor | None) -> None:
        """
        Binds tracking event loops directly to the chosen active editor target
        instance.
        """
        if self._active_editor:
            try:
                self._active_editor.cursorPositionChanged.disconnect(
                    self.refresh_editor_metrics
                )
                self._active_editor.textChanged.disconnect(self.refresh_editor_metrics)
            except Exception:
                pass

        self._active_editor = editor

        if self._active_editor:
            self._active_editor.cursorPositionChanged.connect(
                self.refresh_editor_metrics
            )
            self._active_editor.textChanged.connect(self.refresh_editor_metrics)
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

        file_path = getattr(self._active_editor, "current_file_path", None) or ""
        if not file_path or not os.path.exists(file_path):
            self.item_name.setText(1, "Unsaved Document")
            self.item_path.setText(1, "Memory Cache")
            self.item_size.setText(1, "0 KB")
            self.item_created.setText(1, "--")
            self.item_timestamp.setText(1, "--")
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

        ext = f".{info.suffix().lower()}"
        idx_ext = self.combo_ext.findText(ext)
        if idx_ext != -1:
            self.combo_ext.setCurrentIndex(idx_ext)

        lang_map = {
            ".py": "Python",
            ".pyi": "Python",
            ".cpp": "C++",
            ".hpp": "C++",
            ".c": "C",
            ".h": "C",
            ".sh": "Bash",
            ".bash": "Bash",
            ".d": "D",
            ".ps1": "PowerShell",
        }
        target_lang = lang_map.get(ext, "")
        idx_lang = self.combo_lang.findText(target_lang)
        if idx_lang != -1:
            self.combo_lang.setCurrentIndex(idx_lang)

        for item in (
            self.item_name,
            self.item_path,
            self.item_created,
            self.item_timestamp,
        ):
            item.setToolTip(1, item.text(1))

    def refresh_editor_metrics(self, *args) -> None:
        """Evaluates cursor offsets and token strings under operational views."""
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

        token = ""
        if hasattr(self._active_editor, "wordAtLineAndColumn"):
            token = self._active_editor.wordAtLineAndColumn(line, col) or ""
        self.item_symbol.setText(1, f"'{token}'" if token else "None")

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
            self.item_symbol,
        ):
            item.setText(1, "--")
            item.setToolTip(1, "")
        self.combo_lang.setCurrentIndex(0)
        self.combo_ext.setCurrentIndex(0)
        self.combo_editable.setCurrentIndex(0)
