from editor import *

class RightClickMenu(QMenu):
    """
    A custom menu dedicated for Ironica with right-aligned shortcuts and custom width.

    Actions that require a condition (e.g. selection, undo history, clipboard
    content) are automatically disabled/grayed-out when the condition is not met.
    This is handled by ``_refresh_action_states`` which runs every time the menu
    is about to show.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._actions = {}

        self.setStyleSheet("""
            QMenu {
                min-width: 260px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                margin: 2px 0px;
            }
        """)

        self.build_actions()
        self.aboutToShow.connect(self._refresh_action_states)

    def _editor(self):
        """Return the parent CodeEditor, or None if unavailable."""
        return self.parent() if self.parent() else None

    def build_actions(self):
        items = [
            {
                "label": "Go to Definition",
                "action": self.go_to_definition,
                "shortcut": "F12",
                "key": "go_to_definition",
            },
            {
                "label": "Go to Usage",
                "action": self.go_to_usage,
                "shortcut": "Ctrl+Alt+B",
                "key": "go_to_usage",
            },
            None,  # Separator
            {
                "label": "Undo",
                "action": self.undo_action,
                "shortcut": "Ctrl+Z",
                "key": "undo",
            },
            {
                "label": "Redo",
                "action": self.redo_action,
                "shortcut": "Ctrl+Y",
                "key": "redo",
            },
            {
                "label": "Cut",
                "action": self.cut,
                "shortcut": "Ctrl+X",
                "key": "cut",
            },
            {
                "label": "Copy",
                "action": self.copy,
                "shortcut": "Ctrl+C",
                "key": "copy",
            },
            {
                "label": "Copy File Path",
                "action": self.copy_file_path,
                "shortcut": "Ctrl+Alt+C",
                "key": "copy_file_path",
            },
            {
                "label": "Paste",
                "action": self.paste,
                "shortcut": "Ctrl+V",
                "key": "paste",
            },
            None,  # Separator
            {
                "label": "Make File Read-Only",
                "action": self.make_file_read_only,
                "shortcut": None,
                "key": "make_file_read_only",
            },
            {
                "label": "Find and Replace",
                "action": self.find_and_replace,
                "shortcut": "Ctrl+R",
                "key": "find_and_replace",
            },
            {
                "label": "Find Usages",
                "action": self.find_usages,
                "shortcut": "Alt+F7",
                "key": "find_usages",
            },
            {
                "label": "Rename Current File",
                "action": self.rename_current_file,
                "shortcut": "Shift+F6",
                "key": "rename_current_file",
            },
            None,  # Separator
            {
                "label": "Expand All Folds",
                "action": self.expand_all_folds,
                "shortcut": "Ctrl+Shift+Num+",
                "key": "expand_all_folds",
            },
            {
                "label": "Collapse All Folds",
                "action": self.collapse_all_folds,
                "shortcut": "Ctrl+Shift+Num-",
                "key": "collapse_all_folds",
            },
            {
                "label": "Expand Current Fold",
                "action": self.expand_current_fold,
                "shortcut": "Ctrl+Num+",
                "key": "expand_current_fold",
            },
            {
                "label": "Collapse Current Fold",
                "action": self.collapse_current_fold,
                "shortcut": "Ctrl+Num-",
                "key": "collapse_current_fold",
            },
            None,  # Separator
            {
                "label": "Format Code",
                "action": self.format_code,
                "shortcut": "Ctrl+Alt+L",
                "key": "format_code",
            },
            {
                "label": "Comment Current Line",
                "action": self.comment_current_line,
                "shortcut": "Ctrl+/",
                "key": "comment",
            },
            {
                "label": "Uncomment Current Line",
                "action": self.uncomment_current_line,
                "shortcut": "Ctrl+/",
                "key": "uncomment",
            },
            None,  # Separator
            {
                "label": "Add File to Chat",
                "action": self.add_file_to_chat,
                "shortcut": "Alt+A",
                "key": "add_file_to_chat",
            },
            {
                "label": "Ask A.I to Analyze File",
                "action": self.ask_ai_to_analyze_file,
                "shortcut": "Alt+I",
                "key": "ask_ai",
            },
        ]

        for item in items:
            if item is None:
                self.addSeparator()
            else:
                qaction = self.addAction(item["label"])

                if item.get("shortcut"):
                    qaction.setShortcut(QKeySequence(item["shortcut"]))

                if item["action"] is not None:
                    qaction.triggered.connect(item["action"])

                self._actions[item["key"]] = qaction

    # ------------------------------------------------------------------
    # Dynamic enable/disable — runs every time the menu opens
    # ------------------------------------------------------------------

    def _refresh_action_states(self):
        """Enable or disable actions based on the current editor state."""
        editor = self._editor()
        if editor is None:
            return

        has_selection = editor.hasSelectedText()
        can_undo = editor.isUndoAvailable()
        can_redo = editor.isRedoAvailable()
        has_clipboard = bool(QApplication.clipboard().text())
        has_provider = editor.current_provider is not None
        has_file = bool(editor.current_file_path)
        has_folds = hasattr(editor, "_fold_manager") and editor._fold_manager is not None
        is_readonly = editor.isReadOnly() if hasattr(editor, "isReadOnly") else False

        self._set_enabled("go_to_definition", has_provider)
        self._set_enabled("undo", can_undo and not is_readonly)
        self._set_enabled("redo", can_redo and not is_readonly)
        self._set_enabled("cut", has_selection and not is_readonly)
        self._set_enabled("copy", has_selection)
        self._set_enabled("copy_file_path", has_file)
        self._set_enabled("paste", has_clipboard and not is_readonly)
        self._set_enabled("make_file_read_only", has_file)
        self._set_enabled("rename_current_file", has_file and not is_readonly)
        self._set_enabled("expand_all_folds", has_folds)
        self._set_enabled("collapse_all_folds", has_folds)
        self._set_enabled("expand_current_fold", has_folds)
        self._set_enabled("collapse_current_fold", has_folds)
        self._set_enabled("comment", has_selection and not is_readonly)
        self._set_enabled("uncomment", has_selection and not is_readonly)
        # Block formatting when read-only.
        self._set_enabled("format_code", not is_readonly)

    def _set_enabled(self, key, enabled):
        action = self._actions.get(key)
        if action is not None:
            action.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def go_to_definition(self):
        editor = self._editor()
        if editor:
            editor.execute_goto_definition()

    def go_to_usage(self):
        pass

    # ------------------------------------------------------------------
    # Clipboard & Undo
    # ------------------------------------------------------------------

    def undo_action(self):
        editor = self._editor()
        if editor and hasattr(editor, "isReadOnly") and editor.isReadOnly():
            return
        if editor and editor.isUndoAvailable():
            editor.undo()

    def redo_action(self):
        editor = self._editor()
        if editor and hasattr(editor, "isReadOnly") and editor.isReadOnly():
            return
        if editor and editor.isRedoAvailable():
            editor.redo()

    def cut(self):
        editor = self._editor()
        if editor and hasattr(editor, "isReadOnly") and editor.isReadOnly():
            return
        if editor and editor.hasSelectedText():
            editor.cut()

    def copy(self):
        editor = self._editor()
        if editor and editor.hasSelectedText():
            editor.copy()

    def copy_file_path(self):
        editor = self._editor()
        if editor and editor.current_file_path:
            QApplication.clipboard().setText(editor.current_file_path)

    def paste(self):
        editor = self._editor()
        if editor and hasattr(editor, "isReadOnly") and editor.isReadOnly():
            return
        if editor:
            editor.paste()

    # ------------------------------------------------------------------
    # File Operations
    # ------------------------------------------------------------------

    def make_file_read_only(self):
        editor = self._editor()
        if editor:
            editor.make_file_readonly()

    def find_and_replace(self):
        editor = self._editor()
        if editor is None:
            return
        win = editor.window()
        if hasattr(win, "_toggle_search_widget"):
            win._toggle_search_widget()

    def find_usages(self):
        pass

    def rename_current_file(self):
        editor = self._editor()
        if editor is None or not editor.current_file_path:
            return
        if hasattr(editor, "isReadOnly") and editor.isReadOnly():
            return
        from editor.utils.explorer.api import ExplorerAPI

        result = ExplorerAPI.rename_item(parent=editor, path=editor.current_file_path)
        if result:
            try:
                from editor.utils.git_control.status_service import get_status_service

                get_status_service().request_scan("editor:rename_current_file")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Folding
    # ------------------------------------------------------------------

    def expand_all_folds(self):
        editor = self._editor()
        if editor and hasattr(editor, "_fold_manager") and editor._fold_manager:
            editor._fold_manager.expand_all()

    def collapse_all_folds(self):
        editor = self._editor()
        if editor and hasattr(editor, "_fold_manager") and editor._fold_manager:
            editor._fold_manager.collapse_all()

    def expand_current_fold(self):
        editor = self._editor()
        if editor is None or not hasattr(editor, "_fold_manager"):
            return
        fm = editor._fold_manager
        if fm is None:
            return
        line, _ = editor.getCursorPosition()
        region = fm.get_region_at_line(line)
        if region is not None:
            fm.expand_region(region)

    def collapse_current_fold(self):
        editor = self._editor()
        if editor is None or not hasattr(editor, "_fold_manager"):
            return
        fm = editor._fold_manager
        if fm is None:
            return
        line, _ = editor.getCursorPosition()
        region = fm.get_region_at_line(line)
        if region is not None:
            fm.collapse_region(region)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_code(self):
        editor = self._editor()
        if editor and hasattr(editor, "isReadOnly") and editor.isReadOnly():
            return
        if editor:
            editor.format_current_file()

    def comment_current_line(self):
        editor = self._editor()
        if editor is None:
            return
        if hasattr(editor, "isReadOnly") and editor.isReadOnly():
            return
        line, _ = editor.getCursorPosition()
        line_text = editor.text(line)
        length = len(line_text.rstrip("\n"))
        editor.beginUndoAction()
        editor.setSelection(line, 0, line, length)
        editor.insertAt("# ", line, 0)
        editor.endUndoAction()
        editor.setCursorPosition(line, length + 2)

    def uncomment_current_line(self):
        editor = self._editor()
        if editor is None:
            return
        if hasattr(editor, "isReadOnly") and editor.isReadOnly():
            return
        line, _ = editor.getCursorPosition()
        line_text = editor.text(line)
        stripped = line_text.lstrip()
        if not stripped.startswith("# "):
            return
        indent = len(line_text) - len(stripped)
        editor.beginUndoAction()
        editor.setSelection(line, indent, line, indent + 2)
        editor.removeSelectedText()
        editor.endUndoAction()
        editor.setCursorPosition(line, max(0, len(stripped) - 2))

    # ------------------------------------------------------------------
    # AI Integration (not yet implemented)
    # ------------------------------------------------------------------

    def add_file_to_chat(self):
        pass

    def ask_ai_to_analyze_file(self):
        pass
