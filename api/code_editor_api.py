"""
CodeEditorAPI - Wraps CodeEditor (QsciScintilla) functionality.

Provides access to text editing, syntax highlighting, code completion,
navigation, and file operations for the active code editor.
"""

from typing import Optional, Any


class CodeEditorAPI:
    """API for interacting with the code editor."""

    def __init__(self, main_window):
        self._main = main_window

    def _editor(self):
        return self._main._get_current_editor()

    def getText(self) -> str:
        """Get the full text content of the current editor."""
        editor = self._editor()
        if editor is None:
            return ""
        return editor.text()

    def setText(self, text: str) -> None:
        """Set the full text content of the current editor."""
        editor = self._editor()
        if editor is not None:
            editor.setText(text)

    def getSelectedText(self) -> str:
        """Get the currently selected text."""
        editor = self._editor()
        if editor is None:
            return ""
        return editor.selectedText()

    def replaceSelectedText(self, text: str) -> None:
        """Replace the currently selected text."""
        editor = self._editor()
        if editor is not None:
            editor.replaceSelectedText(text)

    def insertText(self, text: str) -> None:
        """Insert text at the current cursor position."""
        editor = self._editor()
        if editor is not None:
            editor.insert(text)

    def getCursorPosition(self) -> tuple:
        """Get the current cursor position as (line, column)."""
        editor = self._editor()
        if editor is None:
            return (0, 0)
        return editor.getCursorPosition()

    def setCursorPosition(self, line: int, column: int) -> None:
        """Set the cursor position."""
        editor = self._editor()
        if editor is not None:
            editor.setCursorPosition(line, column)

    def getLineCount(self) -> int:
        """Get the total number of lines in the editor."""
        editor = self._editor()
        if editor is None:
            return 0
        return editor.lines()

    def getLineText(self, line: int) -> str:
        """Get the text content of a specific line."""
        editor = self._editor()
        if editor is None:
            return ""
        return editor._get_line_text(line)

    def getCurrentLineText(self) -> str:
        """Get the text of the current line."""
        editor = self._editor()
        if editor is None:
            return ""
        line, _ = editor.getCursorPosition()
        return editor._get_line_text(line)

    def selectAll(self) -> None:
        """Select all text in the editor."""
        editor = self._editor()
        if editor is not None:
            editor.selectAll()

    def undo(self) -> None:
        """Undo the last action."""
        editor = self._editor()
        if editor is not None:
            editor.undo()

    def redo(self) -> None:
        """Redo the last undone action."""
        editor = self._editor()
        if editor is not None:
            editor.redo()

    def cut(self) -> None:
        """Cut the selected text."""
        editor = self._editor()
        if editor is not None:
            editor.cut()

    def copy(self) -> None:
        """Copy the selected text."""
        editor = self._editor()
        if editor is not None:
            editor.copy()

    def paste(self) -> None:
        """Paste text from clipboard."""
        editor = self._editor()
        if editor is not None:
            editor.paste()

    def copyAsPlainText(self) -> None:
        """Copy selected text as plain text (no formatting)."""
        editor = self._editor()
        if editor is not None:
            editor.copy_selection_as_plain_text()

    def deleteSelection(self) -> None:
        """Delete the currently selected text."""
        editor = self._editor()
        if editor is not None:
            editor.removeSelectedText()

    def isDirty(self) -> bool:
        """Check if the current editor has unsaved changes."""
        editor = self._editor()
        if editor is None:
            return False
        return editor.is_dirty()

    def clearDirty(self) -> None:
        """Mark the current editor as clean (no unsaved changes)."""
        editor = self._editor()
        if editor is not None:
            editor.clear_dirty()

    def save(self) -> bool:
        """Save the current file. Returns True on success."""
        editor = self._editor()
        if editor is None:
            return False
        return editor.save()

    def saveAs(self) -> bool:
        """Save the current file with a new name. Returns True on success."""
        editor = self._editor()
        if editor is None:
            return False
        return editor.save_as()

    def saveToFile(self, file_path: str) -> bool:
        """Save the current editor content to a specific file path."""
        editor = self._editor()
        if editor is None:
            return False
        return editor.save_to_file(file_path)

    def loadFromFile(self, file_path: str) -> None:
        """Load content from a file into the current editor."""
        editor = self._editor()
        if editor is not None:
            editor.load_from_file(file_path)

    def getFilePath(self) -> Optional[str]:
        """Get the file path of the current editor."""
        editor = self._editor()
        if editor is None:
            return None
        return getattr(editor, "current_file_path", None)

    def getLanguage(self) -> Optional[str]:
        """Get the language of the current editor."""
        editor = self._editor()
        if editor is None:
            return None
        return getattr(editor, "language", None)

    def setLanguage(self, lang: str) -> None:
        """Set the language for syntax highlighting."""
        editor = self._editor()
        if editor is not None:
            editor.setLanguage(lang)

    def setEditorFont(self, font_name: str) -> None:
        """Set the editor font."""
        editor = self._editor()
        if editor is not None:
            from PyQt6.QtGui import QFont
            editor.setEditorFont(QFont(font_name, editor.font_size))

    def setEditorFontSize(self, size: int) -> None:
        """Set the editor font size."""
        editor = self._editor()
        if editor is not None:
            editor.set_editor_font_size(size)

    def setWrapMode(self, enabled: bool = False) -> None:
        """Enable or disable word wrap."""
        editor = self._editor()
        if editor is not None:
            editor.set_wrap_mode(enabled)

    def applyTheme(self, theme_manager=None) -> None:
        """Apply a theme to the current editor."""
        editor = self._editor()
        if editor is not None:
            editor.apply_theme(theme_manager)

    def gotoDefinition(self) -> None:
        """Navigate to the definition of the symbol under cursor."""
        editor = self._editor()
        if editor is not None:
            editor.goto_definition_at_cursor()

    def findUsages(self) -> None:
        """Find all usages of the symbol under cursor."""
        editor = self._editor()
        if editor is not None:
            editor.find_usages()

    def requestCompletion(self) -> None:
        """Request code completion at the current cursor position."""
        editor = self._editor()
        if editor is not None:
            editor.request_completion()

    def getCompletionContext(self) -> Optional[dict]:
        """Get the current completion context."""
        editor = self._editor()
        if editor is None:
            return None
        return editor.get_completion_context()

    def getCompletionItems(self, context: dict) -> list:
        """Get completion items for a given context."""
        editor = self._editor()
        if editor is None:
            return []
        return editor.get_completion_items(context)

    def updateDocumentSymbols(self) -> None:
        """Update the document symbol table (functions, classes, variables)."""
        editor = self._editor()
        if editor is not None:
            editor.update_document_symbols()

    def getDocumentSymbols(self) -> dict:
        """Get the current document symbols."""
        editor = self._editor()
        if editor is None:
            return {"variables": set(), "functions": set(), "classes": set()}
        return dict(editor.document_symbols)

    def runComplexityAnalysis(self) -> None:
        """Run complexity analysis on the current file."""
        editor = self._editor()
        if editor is not None:
            editor._run_complexity_analysis()

    def getComplexityResults(self) -> Optional[dict]:
        """Get the last complexity analysis results."""
        editor = self._editor()
        if editor is None:
            return None
        return getattr(editor, "_complexity_results", None)

    def ensureLineVisible(self, line: int) -> None:
        """Ensure a specific line is visible in the viewport."""
        editor = self._editor()
        if editor is not None:
            editor.ensureLineVisible(line)

    def zoomIn(self, zoom: int = 1) -> None:
        """Zoom in the editor."""
        editor = self._editor()
        if editor is not None:
            editor.zoomIn(zoom)

    def zoomOut(self, zoom: int = 1) -> None:
        """Zoom out the editor."""
        editor = self._editor()
        if editor is not None:
            editor.zoomOut(zoom)

    def setIndentationWidth(self, width: int) -> None:
        """Set the indentation width in spaces."""
        editor = self._editor()
        if editor is not None:
            editor.setIndentationWidth(width)
            editor._indentation_spacing = width

    def getIndentationWidth(self) -> int:
        """Get the current indentation width."""
        editor = self._editor()
        if editor is None:
            return 4
        return getattr(editor, "_indentation_spacing", 4)

    def setTabWidth(self, width: int) -> None:
        """Set the tab width."""
        editor = self._editor()
        if editor is not None:
            editor.setTabWidth(width)

    def setAutoIndent(self, enabled: bool = True) -> None:
        """Enable or disable auto indentation."""
        editor = self._editor()
        if editor is not None:
            editor.setAutoIndent(enabled)

    def setEdgeColumn(self, column: int) -> None:
        """Set the edge column indicator position."""
        editor = self._editor()
        if editor is not None:
            editor.setEdgeColumn(column)

    def setMarginWidth(self, margin: int, width: str) -> None:
        """Set the width of a margin."""
        editor = self._editor()
        if editor is not None:
            editor.setMarginWidth(margin, width)

    def setReadOnly(self, read_only: bool) -> None:
        """Set the editor to read-only mode."""
        editor = self._editor()
        if editor is not None:
            editor.setReadOnly(read_only)

    def isReadOnly(self) -> bool:
        """Check if the editor is in read-only mode."""
        editor = self._editor()
        if editor is None:
            return False
        return editor.isReadOnly()

    def getTextLength(self) -> int:
        """Get the total text length in characters."""
        editor = self._editor()
        if editor is None:
            return 0
        return editor.length()

    def getLexer(self) -> Optional[Any]:
        """Get the current lexer object."""
        editor = self._editor()
        if editor is None:
            return None
        return getattr(editor, "_lexer", None)

    def getKeywordMap(self) -> dict:
        """Get the current keyword classification map."""
        editor = self._editor()
        if editor is None:
            return {}
        return dict(getattr(editor, "keyword_map", {}))

    def setLexerFont(self, font) -> None:
        """Apply a font to the current lexer."""
        editor = self._editor()
        if editor is not None and hasattr(editor, "_lexer") and editor._lexer:
            if hasattr(editor._lexer, "apply_font"):
                editor._lexer.apply_font(font)
