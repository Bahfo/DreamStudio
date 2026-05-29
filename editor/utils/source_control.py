from PyQt6.QtCore import Qt, QSize, QPoint, QPropertyAnimation, QSequentialAnimationGroup
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLineEdit,
    QFrame,
    QLabel,
    QDialog,
    QHeaderView,
)

from editor.widgets.QExitDialog import ConfirmDialog

import os


class SourceControl(QFrame):
    _commit_msg_file_key = None
    _commit_msg_editor_ref = None

    def __init__(self, _parent=None):
        super().__init__(_parent)
        self._parent = _parent
        self._repo = None
        self._commit_done = False
        self._syncing_text = False
        self._error_active = False
        self._disabled_shortcuts = []
        self._prev_shortcut_enabled = {}

        self.setFrameShape(QFrame.Shape.Panel)
        self.setStyleSheet("background-color: #171717; border: none;")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.main_layout.addSpacing(10)
        self._source_control_label = QLabel("SOURCE CONTROL")
        self._source_control_label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        self.main_layout.addWidget(self._source_control_label)
        self.main_layout.addSpacing(10)

        # Toolbar
        self.toolbar = QFrame()
        self.toolbar.setStyleSheet("background-color: transparent; border: none;")
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(2)

        self._toolbar_btn_style = """
        QPushButton {
            background-color: transparent;
            border: none;
            color: #afb1b3;
            font-size: 14px;
            padding: 2px 4px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #323232;
            color: #ffffff;
        }
        QPushButton:disabled {
            color: #555555;
        }
        """
        icon_size = QSize(16, 16)
        btn_size = QSize(26, 26)

        self.refresh_btn = QPushButton()
        self.refresh_btn.setFixedSize(btn_size)
        self.refresh_btn.setStyleSheet(self._toolbar_btn_style)
        self.refresh_btn.setIcon(QIcon("assets/menus/refresh.png"))
        self.refresh_btn.setIconSize(icon_size)
        self.refresh_btn.setToolTip("Refresh")
        self.refresh_btn.clicked.connect(self._refresh)

        self.show_diff_btn = QPushButton()
        self.show_diff_btn.setFixedSize(btn_size)
        self.show_diff_btn.setStyleSheet(self._toolbar_btn_style)
        self.show_diff_btn.setIcon(QIcon("assets/menus/refresh.png"))
        self.show_diff_btn.setIconSize(icon_size)
        self.show_diff_btn.setToolTip("Show Diff")

        self.check_all_btn = QPushButton()
        self.check_all_btn.setFixedSize(btn_size)
        self.check_all_btn.setStyleSheet(self._toolbar_btn_style)
        self.check_all_btn.setIcon(QIcon("assets/menus/refresh.png"))
        self.check_all_btn.setIconSize(icon_size)
        self.check_all_btn.setToolTip("Check / Uncheck All")
        self.check_all_btn.clicked.connect(self._toggle_check_all)
        self._all_checked = True

        self.expand_btn = QPushButton()
        self.expand_btn.setFixedSize(btn_size)
        self.expand_btn.setStyleSheet(self._toolbar_btn_style)
        self.expand_btn.setIcon(QIcon("assets/menus/expand.png"))
        self.expand_btn.setIconSize(icon_size)
        self.expand_btn.setToolTip("Expand All")
        self.expand_btn.clicked.connect(self._expand_all)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(btn_size)
        self.collapse_btn.setStyleSheet(self._toolbar_btn_style)
        self.collapse_btn.setIcon(QIcon("assets/menus/collapse.png"))
        self.collapse_btn.setIconSize(icon_size)
        self.collapse_btn.setToolTip("Collapse All")
        self.collapse_btn.clicked.connect(self._collapse_all)

        self.toolbox_btn = QPushButton("···")
        self.toolbox_btn.setFixedSize(QSize(20, 26))
        self.toolbox_btn.setStyleSheet(self._toolbar_btn_style)
        self.toolbox_btn.setToolTip("More options")

        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.show_diff_btn)
        toolbar_layout.addWidget(self.check_all_btn)
        toolbar_layout.addWidget(self.expand_btn)
        toolbar_layout.addWidget(self.collapse_btn)
        toolbar_layout.addWidget(self.toolbox_btn)
        toolbar_layout.addStretch()

        toolbar_layout.addSpacing(20)
        self.maindirectory = QLabel(f"Directory: {os.path.basename(os.getcwd())}")
        self.maindirectory.setStyleSheet("color: #969696; font-size: 13px;")
        toolbar_layout.addWidget(self.maindirectory)
        self.main_layout.addWidget(self.toolbar)
        toolbar_layout.addSpacing(10)

        # Commit Message Input Area
        commit_input_layout = QVBoxLayout()
        commit_input_layout.setSpacing(5)

        self.commit_input = QLineEdit()
        self.commit_input.setMinimumHeight(32)
        self.commit_input.setPlaceholderText("Commit message (Enter to commit)")
        self.commit_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
                background-color: #1E1E1E;
            }
            QLineEdit:focus {border: 1px solid #007acc;}
        """)
        self.commit_input.returnPressed.connect(self._do_commit)
        self.commit_input.textChanged.connect(self._on_input_text_changed)
        commit_input_layout.addWidget(self.commit_input)

        # Long message & commit row
        msg_btn_layout = QHBoxLayout()
        msg_btn_layout.setSpacing(4)

        self.long_msg_btn = QPushButton("Long Message")
        self.long_msg_btn.setMinimumHeight(32)
        self.long_msg_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #444444;
                color: #afb1b3;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #323232;
                border-color: #007acc;
                color: #ffffff;
            }
            QPushButton:disabled {
                color: #555555;
                border-color: #333333;
            }
        """)
        self.long_msg_btn.clicked.connect(self._open_long_message_editor)
        msg_btn_layout.addWidget(self.long_msg_btn)

        self.commit_btn = QPushButton("Commit")
        self.commit_btn.setMinimumHeight(32)
        self.commit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d476d;
                border: none;
                color: #ffffff;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a5a8a;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #555555;
            }
        """)
        self.commit_btn.clicked.connect(self._do_commit)
        msg_btn_layout.addWidget(self.commit_btn)

        commit_input_layout.addLayout(msg_btn_layout)

        # Commit message status label
        self.commit_status_label = QLabel("")
        self.commit_status_label.setStyleSheet("color: #969696; font-size: 11px; padding: 0px;")
        self.commit_status_label.setWordWrap(True)
        commit_input_layout.addWidget(self.commit_status_label)

        # Delete commit message button
        self.delete_msg_btn = QPushButton("Delete Commit Message")
        self.delete_msg_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #444444;
                color: #afb1b3;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #323232;
                color: #ffffff;
            }
            QPushButton:disabled {
                color: #555555;
                border-color: #333333;
            }
        """)
        self.delete_msg_btn.clicked.connect(self._delete_commit_message)
        commit_input_layout.addWidget(self.delete_msg_btn)

        self.main_layout.addLayout(commit_input_layout)

        # TreeView for changed files
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(20)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #171717;
                color: #afb1b3;
                border: none;
                outline: 0;
                font-size: 13px;
            }
            QTreeWidget::item {
                height: 22px;
                padding-left: 2px;
            }
            QTreeWidget::item:hover {
                background-color: #323232;
            }
            QTreeWidget::item:selected {
                background-color: #2d476d;
                color: white;
            }
            QScrollBar:vertical {
                background: #1E1E1E;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3A3A3A;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4A4A4A;
            }
        """)

        self.main_layout.addWidget(self.tree)

        # Initial load
        self._refresh()

    def _expand_all(self):
        self.tree.expandAll()

    def _collapse_all(self):
        self.tree.collapseAll()

    def _refresh(self):
        self._load_changed_files()

    def _toggle_check_all(self):
        self._all_checked = not self._all_checked
        state = Qt.CheckState.Checked if self._all_checked else Qt.CheckState.Unchecked
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                child.setCheckState(0, state)

    def _load_changed_files(self):
        self.tree.clear()
        if self._repo is None:
            try:
                from backend.git.fetch_info import return_repository
                self._repo = return_repository(None)
                if isinstance(self._repo, Exception):
                    self._repo = None
                    item = QTreeWidgetItem(self.tree)
                    item.setText(0, "Not a git repository")
                    item.setForeground(0, QColor("#969696"))
                    self.tree.setColumnCount(1)
                    return
            except Exception:
                self._repo = None
                item = QTreeWidgetItem(self.tree)
                item.setText(0, "Git not available")
                item.setForeground(0, QColor("#969696"))
                self.tree.setColumnCount(1)
                return

        try:
            from backend.git.fetch_info import get_changed_files
            files = get_changed_files(self._repo)
        except Exception:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, "Error reading git changes")
            item.setForeground(0, QColor("#969696"))
            self.tree.setColumnCount(1)
            return

        if not files:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, "No changes detected")
            item.setForeground(0, QColor("#969696"))
            self.tree.setColumnCount(1)
            return

        self.tree.setColumnCount(2)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        modified = [f for f in files if f["status"] in ("M", "S", "R")]
        deleted = [f for f in files if f["status"] == "D"]
        added = [f for f in files if f["status"] in ("U", "A")]

        if modified:
            mod_parent = QTreeWidgetItem(self.tree)
            mod_parent.setText(0, f"Changes ({len(modified)})")
            mod_parent.setForeground(0, QColor("#afb1b3"))
            mod_parent.setFlags(mod_parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            mod_parent.setExpanded(True)
            for f in modified:
                self._add_file_child(mod_parent, f, "#d4872c")

        if deleted:
            del_parent = QTreeWidgetItem(self.tree)
            del_parent.setText(0, f"Deleted ({len(deleted)})")
            del_parent.setForeground(0, QColor("#afb1b3"))
            del_parent.setFlags(del_parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            del_parent.setExpanded(True)
            for f in deleted:
                self._add_file_child(del_parent, f, "#e06b6b")

        if added:
            add_parent = QTreeWidgetItem(self.tree)
            add_parent.setText(0, f"Added ({len(added)})")
            add_parent.setForeground(0, QColor("#afb1b3"))
            add_parent.setFlags(add_parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            add_parent.setExpanded(True)
            for f in added:
                self._add_file_child(add_parent, f, "#6bbf6b")

    def _add_file_child(self, parent: QTreeWidgetItem, file_info: dict, color_hex: str):
        item = QTreeWidgetItem(parent)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)

        path = file_info["path"]
        additions = file_info.get("additions", 0)
        deletions = file_info.get("deletions", 0)

        name = os.path.basename(path)
        dir_part = os.path.dirname(path)
        display_text = name
        if dir_part:
            display_text += f"  [{dir_part}]"

        item.setText(0, display_text)
        item.setForeground(0, QColor(color_hex))

        changes_text = ""
        if additions > 0:
            changes_text += f"+{additions}"
        if deletions > 0:
            if changes_text:
                changes_text += " "
            changes_text += f"-{deletions}"
        if changes_text:
            item.setText(1, changes_text)
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if additions > 0 and deletions == 0:
                item.setForeground(1, QColor("#6BBF6B"))
            elif deletions > 0 and additions == 0:
                item.setForeground(1, QColor("#E06B6B"))
            else:
                item.setForeground(1, QColor("#afb1b3"))
        else:
            item.setText(1, "")

        item.setData(0, Qt.ItemDataRole.UserRole, path)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, file_info["status"])

    def _do_commit(self):
        message = self.commit_input.text().strip()
        if not message:
            self._shake_error("Please enter a commit message")
            return

        checked_files = self._get_checked_files()
        if not checked_files:
            self._shake_error("Select at least one file to commit")
            return

        if self._repo is None:
            try:
                from backend.git.fetch_info import return_repository
                self._repo = return_repository(None)
                if isinstance(self._repo, Exception):
                    self._repo = None
                    self._shake_error("No git repository found")
                    return
            except Exception:
                self._shake_error("Git not available")
                return

        from backend.git.fetch_info import commit_staged
        success, msg = commit_staged(self._repo, message, checked_files)
        if success:
            self._commit_done = True
            self.delete_msg_btn.setEnabled(False)
            self.commit_input.clear()
            self.commit_status_label.setText("Commit message: committed successfully")
            self._load_changed_files()
        else:
            self._shake_error(f"Commit failed: {msg}")

    def _get_checked_files(self) -> list[str]:
        files = []
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    path = child.data(0, Qt.ItemDataRole.UserRole)
                    if path:
                        files.append(path)
        return files

    def _shake_error(self, message: str = ""):
        self._error_active = True
        self.commit_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #FF6B6B;
                border-radius: 4px;
                padding: 4px 8px;
                color: #FF6B6B;
                background-color: #1E1E1E;
            }
        """)
        if message:
            self.commit_input.setText(message)
        self._shake_widget(self.commit_input)

    def _shake_widget(self, widget):
        original = widget.pos()
        group = QSequentialAnimationGroup(self)
        for _ in range(3):
            a = QPropertyAnimation(widget, b"pos")
            a.setDuration(50)
            a.setStartValue(original)
            a.setEndValue(QPoint(original.x() + 8, original.y()))
            group.addAnimation(a)

            a = QPropertyAnimation(widget, b"pos")
            a.setDuration(50)
            a.setStartValue(QPoint(original.x() + 8, original.y()))
            a.setEndValue(QPoint(original.x() - 8, original.y()))
            group.addAnimation(a)

        a = QPropertyAnimation(widget, b"pos")
        a.setDuration(50)
        a.setStartValue(QPoint(original.x() - 8, original.y()))
        a.setEndValue(original)
        group.addAnimation(a)

        group.start()

    def _on_input_text_changed(self, text: str):
        if self._error_active:
            err_msgs = (
                "Please enter a commit message",
                "Select at least one file to commit",
                "No git repository found",
                "Git not available",
            )
            if text not in err_msgs:
                self._error_active = False
                self.commit_input.setStyleSheet("""
                    QLineEdit {
                        border: 1px solid #444444;
                        border-radius: 4px;
                        padding: 4px 8px;
                        color: #ffffff;
                        background-color: #1E1E1E;
                    }
                    QLineEdit:focus {border: 1px solid #007acc;}
                """)

    def _open_long_message_editor(self):
        if self._parent is None:
            return
        tab_editors = getattr(self._parent, "tab_editors", None)
        if tab_editors is None:
            return

        current_msg = self.commit_input.text()
        editor = tab_editors.add_new_editor(
            file_name="COMMIT_EDITMSG",
            content=current_msg,
        )

        file_key = f"__commit_msg_{id(editor)}"
        editor.file_key = file_key
        SourceControl._commit_msg_file_key = file_key
        SourceControl._commit_msg_editor_ref = editor

        self._syncing_text = False

        try:
            editor.textChanged.connect(lambda: self._on_editor_text_changed(editor))
        except Exception:
            pass

        if hasattr(self, "_close_interceptor_ref"):
            try:
                self._connected_tab_editors.remove_close_interceptor(self._close_interceptor_ref)
            except Exception:
                pass

        interceptor = lambda idx, w: self._commit_tab_closing(idx, w, tab_editors)
        tab_editors.add_close_interceptor(interceptor)
        self._close_interceptor_ref = interceptor
        self._connected_tab_editors = tab_editors

        # Disable editor shortcuts
        self._disable_editor_shortcuts(True)

        self.commit_status_label.setText("Commit message: editing in tab ...")

    def _disable_editor_shortcuts(self, disable: bool):
        if self._parent is None:
            return

        shortcuts = []
        tab_editors = getattr(self._parent, "tab_editors", None)
        if tab_editors:
            for attr in ("_save_shortcut", "_save_as_shortcut", "_save_all_shortcut"):
                s = getattr(tab_editors, attr, None)
                if s:
                    shortcuts.append(s)

        for attr in ("new_tab_shortcut", "close_tab_shortcut",
                      "open_file_shortcut", "open_directory_shortcut"):
            s = getattr(self._parent, attr, None)
            if s:
                shortcuts.append(s)

        if disable:
            for s in shortcuts:
                self._prev_shortcut_enabled[id(s)] = s.isEnabled()
                s.setEnabled(False)
        else:
            for s in shortcuts:
                prev = self._prev_shortcut_enabled.get(id(s), True)
                s.setEnabled(prev)
            self._prev_shortcut_enabled.clear()

    def _on_editor_text_changed(self, editor):
        if self._syncing_text:
            return
        try:
            text = editor.text()
            if text != self.commit_input.text():
                self._syncing_text = True
                self.commit_input.setText(text)
                self._syncing_text = False
        except RuntimeError:
            pass

    def _commit_tab_closing(self, index, widget, tab_editors):
        if SourceControl._commit_msg_editor_ref is None:
            return None
        if widget is not SourceControl._commit_msg_editor_ref:
            return None

        self._disable_editor_shortcuts(False)

        try:
            is_dirty = widget.is_dirty()
        except Exception:
            is_dirty = False

        current_text_in_widget = ""
        try:
            current_text_in_widget = widget.text()
        except Exception:
            pass

        if is_dirty:
            dialog = ConfirmDialog(
                self,
                title="Your Message is Not Saved",
                message="Confirm Exiting?",
                confirm_text="EXIT",
                cancel_text="CANCEL",
                destructive=False,
            )
            if hasattr(self._parent, "theme_manager"):
                dialog.retheme(self._parent.theme_manager)
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                SourceControl._commit_msg_file_key = None
                SourceControl._commit_msg_editor_ref = None
                txt_preview = current_text_in_widget[:50]
                self.commit_status_label.setText(
                    f"Commit message: {txt_preview}{'...' if len(current_text_in_widget) > 50 else ''}"
                )
                return True
            else:
                self._disable_editor_shortcuts(True)
                return False
        else:
            SourceControl._commit_msg_file_key = None
            SourceControl._commit_msg_editor_ref = None
            if current_text_in_widget:
                self.commit_input.setText(current_text_in_widget)
                txt_preview = current_text_in_widget[:50]
                self.commit_status_label.setText(
                    f"Commit message: {txt_preview}{'...' if len(current_text_in_widget) > 50 else ''}"
                )
            return True

    def _delete_commit_message(self):
        if self._commit_done:
            return
        self.commit_input.clear()
        self.commit_status_label.setText("")
        if SourceControl._commit_msg_editor_ref is not None:
            tab_editors = getattr(self._parent, "tab_editors", None)
            if tab_editors is not None:
                for i in range(tab_editors.count()):
                    if tab_editors.widget(i) is SourceControl._commit_msg_editor_ref:
                        tab_editors.close_editor(i)
                        break
        SourceControl._commit_msg_file_key = None
        SourceControl._commit_msg_editor_ref = None
        self._disable_editor_shortcuts(False)

    def retheme(self, t):
        bg = t.color("sidebar.background", "#171717")
        txt = t.color("sidebar.text", "#afb1b3")
        hl = t.color("treeview.highlight", "#2d476d")
        hover = t.color("treeview.hover", "#323232")
        added_color = t.color("git.added", "#6bbf6b")
        deleted_color = t.color("git.deleted", "#e06b6b")
        modified_color = t.color("git.modified", "#d4872c")

        self.setStyleSheet(f"background-color: {bg}; border: none;")
        self._source_control_label.setStyleSheet(
            f"color: {txt}; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        self.maindirectory.setStyleSheet(f"color: {txt}; font-size: 13px;")

        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {bg};
                color: {txt};
                border: none;
                outline: 0;
                font-size: 13px;
            }}
            QTreeWidget::item {{
                height: 22px;
                padding-left: 2px;
            }}
            QTreeWidget::item:hover {{
                background-color: {hover};
            }}
            QTreeWidget::item:selected {{
                background-color: {hl};
                color: white;
            }}
            QScrollBar:vertical {{
                background: {t.color("scrollbar.bg", "#1E1E1E")};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {t.color("scrollbar.fg", "#3A3A3A")};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t.color("scrollbar.hover", "#4A4A4A")};
            }}
        """)

        # Re-color tree items
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            label = parent.text(0)
            if label.startswith("Changes"):
                for j in range(parent.childCount()):
                    parent.child(j).setForeground(0, QColor(modified_color))
            elif label.startswith("Deleted"):
                for j in range(parent.childCount()):
                    parent.child(j).setForeground(0, QColor(deleted_color))
            elif label.startswith("Added"):
                for j in range(parent.childCount()):
                    parent.child(j).setForeground(0, QColor(added_color))

        btn_style = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            color: {txt};
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {hover};
            color: {t.color("window.text", "#ffffff")};
        }}
        QPushButton:disabled {{
            color: {t.color("scrollbar.bg", "#555555")};
        }}
        """
        for btn in self.findChildren(QPushButton):
            if btn is self.commit_btn or btn is self.long_msg_btn:
                continue
            btn.setStyleSheet(btn_style)

        self.commit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {hl};
                border: none;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t.color("button.hover", "#3a5a8a")};
            }}
            QPushButton:disabled {{
                background-color: #1a1a1a;
                color: #555555;
            }}
        """)

        btn_border = t.color("widget.border", "#444444")
        btn_border_hover = t.color("button.hover", "#007acc")
        self.long_msg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {btn_border};
                color: {txt};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {hover};
                border-color: {btn_border_hover};
                color: {t.color("window.text", "#ffffff")};
            }}
            QPushButton:disabled {{
                color: {t.color("scrollbar.bg", "#555555")};
                border-color: #333333;
            }}
        """)
