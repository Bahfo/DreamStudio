from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction, QKeySequence


class ClickMenu(QMenu):
    def __init__(self, parent_editor):
        super().__init__(parent_editor)
        self.editor = parent_editor

        self.menu_style = """
            QMenu {
                background-color: #1E1E1E;
                color: #BCBEC4;
                border: 1px solid #808080;
                border-radius: 0px;
                padding: 4px 0px;
                font-family: 'Inter', Arial;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 24px 6px 32px; 
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #2F3135;
                color: #DFE1E5;
            }
            QMenu::item:disabled {
                color: #5F6165;
            }
            QMenu::separator {
                height: 1px;
                background-color: #808080;
                margin: 4px 0px;
            }
            QMenu::icon {
                padding-left: 10px;
            }
        """
        self.setStyleSheet(self.menu_style)

        has_selection = self.editor.hasSelectedText()
        can_undo = self.editor.isUndoAvailable()
        can_redo = self.editor.isRedoAvailable()

        #############################
        # Text Editing Options
        #############################

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

        #############################
        # Code Definition Options
        #############################
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

        #############################
        # Code Related Options
        #############################
        refactor_submenu = QMenu("Refactor", self)
        refactor_submenu.setStyleSheet(self.menu_style)

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

        #############################
        # Code Analysis Options
        #############################
        analysis_submenu = QMenu("Analysis", self)
        analysis_submenu.setStyleSheet(self.menu_style)

        inspect_action = QAction("Inspect Code", analysis_submenu)
        analysis_submenu.addAction(inspect_action)

        code_cleanup = QAction("Code Cleanup", analysis_submenu)
        analysis_submenu.addAction(code_cleanup)

        config_cleanup = QAction("Configure Current File Analysis", analysis_submenu)
        analysis_submenu.addAction(config_cleanup)

        self.addMenu(analysis_submenu)

    def _handle_ai_explain(self):
        """Extracts text context and passes it safely to the IDE interface layer."""
        selected_text = self.editor.selectedText()
        if selected_text:
            print(f"Sending to AI:\n{selected_text}")
