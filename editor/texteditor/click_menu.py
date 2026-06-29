from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction, QKeySequence


class ClickMenu(QMenu):
    def __init__(self, parent_editor):
        super().__init__(parent_editor)
        self.editor = parent_editor

        self._bg = "#1E1E1E"
        self._fg = "#BCBEC4"
        self._border = "#808080"
        self._sel_bg = "#2F3135"
        self._sel_fg = "#DFE1E5"
        self._disabled_fg = "#5F6165"
        self._sep_color = "#808080"

        self._build_stylesheet()

        has_selection = self.editor.hasSelectedText()
        can_undo = self.editor.isUndoAvailable()
        can_redo = self.editor.isRedoAvailable()

        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setEnabled(can_undo)
        undo_action.triggered.connect(self.editor.undo)
        self.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setEnabled(can_redo)
        redo_action.triggered.connect(self.editor.redo)
        self.addAction(redo_action)

        cut_action = QAction("Cut", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.setEnabled(has_selection)
        cut_action.triggered.connect(self.editor.cut)
        self.addAction(cut_action)

        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setEnabled(has_selection)
        copy_action.triggered.connect(self.editor.copy)
        self.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.editor.paste)
        self.addAction(paste_action)

        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self.editor.selectAll)
        self.addAction(select_all_action)
        self.addSeparator()

        find_usage_action = QAction("Find Usages", self)
        find_usage_action.triggered.connect(self.editor.find_usages)
        self.addAction(find_usage_action)

        goto_definition_action = QAction("Go To Definition", self)
        goto_definition_action.setShortcut(QKeySequence("Ctrl+B"))
        goto_definition_action.triggered.connect(self.editor.goto_definition_at_cursor)
        self.addAction(goto_definition_action)

        ai_explain = QAction("Explain with Ether AI", self)
        ai_explain.setEnabled(has_selection)
        ai_explain.triggered.connect(self._handle_ai_explain)
        self.addAction(ai_explain)

        self.addSeparator()

        refactor_submenu = QMenu("Refactor", self)
        refactor_submenu.setStyleSheet(self._build_submenu_style())

        rename_action = QAction("Rename Symbol...", refactor_submenu)
        refactor_submenu.addAction(rename_action)

        extract_method = QAction("Extract Method...", refactor_submenu)
        refactor_submenu.addAction(extract_method)

        inline_variable = QAction("Inline Variable...", refactor_submenu)
        refactor_submenu.addAction(inline_variable)

        extract_method = QAction("Refactor Code File", refactor_submenu)
        refactor_submenu.addAction(extract_method)
        self.addMenu(refactor_submenu)

        comment_selection = QAction("Comment Selection", self)
        comment_selection.setEnabled(has_selection)
        self.addAction(comment_selection)

        uncomment_selection = QAction("Uncomment Selection", self)
        uncomment_selection.setEnabled(has_selection)
        self.addAction(uncomment_selection)

        indent_selection = QAction("Indent Selection", self)
        indent_selection.setEnabled(has_selection)
        self.addAction(indent_selection)

        unindent_selection = QAction("Unindent Selection", self)
        unindent_selection.setEnabled(has_selection)
        self.addAction(unindent_selection)

        analysis_submenu = QMenu("Analysis", self)
        analysis_submenu.setStyleSheet(self._build_submenu_style())

        inspect_action = QAction("Inspect Code", analysis_submenu)
        analysis_submenu.addAction(inspect_action)

        code_cleanup = QAction("Code Cleanup", analysis_submenu)
        analysis_submenu.addAction(code_cleanup)

        config_cleanup = QAction("Configure Current File Analysis", analysis_submenu)
        analysis_submenu.addAction(config_cleanup)

        self.addMenu(analysis_submenu)

    def _build_stylesheet(self):
        self.setStyleSheet(
            f"""
            QMenu {{
                background-color: {self._bg};
                color: {self._fg};
                border: 1px solid {self._border};
                border-radius: 0px;
                padding: 4px 0px;
                font-family: 'inter', Arial;
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 6px 24px 6px 32px;
                background-color: transparent;
            }}
            QMenu::item:selected {{
                background-color: {self._sel_bg};
                color: {self._sel_fg};
            }}
            QMenu::item:disabled {{
                color: {self._disabled_fg};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {self._sep_color};
                margin: 4px 0px;
            }}
            QMenu::icon {{
                padding-left: 10px;
            }}
        """
        )

    def _build_submenu_style(self):
        return f"""
            QMenu {{
                background-color: {self._bg};
                color: {self._fg};
                border: 1px solid {self._border};
                border-radius: 0px;
                padding: 4px 0px;
                font-family: 'inter', Arial;
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 6px 24px 6px 32px;
                background-color: transparent;
            }}
            QMenu::item:selected {{
                background-color: {self._sel_bg};
                color: {self._sel_fg};
            }}
            QMenu::item:disabled {{
                color: {self._disabled_fg};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {self._sep_color};
                margin: 4px 0px;
            }}
        """

    def retheme(self, t):
        if t is None:
            return
        self._bg = t.color("menu.background", "#1E1E1E")
        self._fg = t.color("menu.text", "#BCBEC4")
        self._border = t.color("menu.border", "#808080")
        self._sel_bg = t.color("menu.selection_bg", "#2F3135")
        self._sel_fg = t.color("menu.selection_fg", "#DFE1E5")
        self._disabled_fg = t.color("menu.disabled_fg", "#5F6165")
        self._sep_color = t.color("menu.separator", "#808080")
        self._build_stylesheet()
        for action in self.actions():
            if action.menu():
                action.menu().setStyleSheet(self._build_submenu_style())

    def _handle_ai_explain(self):
        selected_text = self.editor.selectedText()
        if selected_text:
            print(f"Sending to AI:\n{selected_text}")
