"""
A QPlainTextEdit-based terminal widget for DayDream.
Provides terminal input behavior without executing system commands.
"""

_help = """(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

DayDream Terminal - A Command Line Interface for DreamStudio and DreamScript.
DayDream is the terminal interface of DreamStudio's scripting language `DreamScript`. 
It is a minimalistic scripting language used for automation tasks and deployment of
DreamStudio projects. DayDream offers the interface, while DreamScript offers 

_____________________________________________________________________________________
Hot-Topic Commands: 

help            - Display general help and hot topic comamnds (you already typed it).
clear           - Clears DayDream screen.
history         - Shows user's history (DayDream's history only).
print           - Prints a user's quoted string onto DayDream's screen.
list-items      - Lists items in current working directory. 
current-dir     - Shows current working directory.
_____________________________________________________________________________________
DreamScript:

DreamScript is a special scripting language made to package with DreamStudio. 
It is a language made to automate developer's routine tasks and everyday's time-
consuming tasks. DreamScript is a very similar language to Bash or PowerShell. 
However, it includes a huge set of automated commands and scripts so users can simply
execute large command scripts in seconds.
_____________________________________________________________________________________

For more info, please check out related documentations on EXcellent TechStacks page.

                                END OF DOCUMENTATION
"""

import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QFont,
    QColor,
    QTextCursor,
    QKeySequence,
    QTextCharFormat,
    QSyntaxHighlighter,
)
from PyQt6.QtWidgets import QPlainTextEdit


class DayDreamSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for the DayDream Console."""

    PROMPT = "DayDream - DreamScript >>> "
    KEYWORDS = {"if", "else", "then", "while", "true", "false"}
    KEYWORD_PATTERN = re.compile(
        r"\b(?:" + "|".join(re.escape(word) for word in sorted(KEYWORDS)) + r")\b",
        re.IGNORECASE,
    )
    NUMBER_PATTERN = re.compile(
        r"(?<![\w.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)" r"(?:[eE][+-]?\d+)?(?![\w.])"
    )
    OPTION_PATTERN = re.compile(r"(?<!\S)--?[A-Za-z][A-Za-z0-9_-]*(?:=[^\s]+)?")
    STRING_PATTERN = re.compile(r"""("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')""")
    ERROR_PATTERN = re.compile(r"ERROR|EXCEPTION|Error|Exception|error|exception")

    def __init__(self, document, prompt=PROMPT):
        super().__init__(document)

        self.prompt = prompt

        self.command_format = self._make_format("#EFCB61", bold=True)
        self.keyword_format = self._make_format("#C678DD", bold=True)
        self.number_format = self._make_format("#B8D166")
        self.option_format = self._make_format("#5661C2")
        self.string_format = self._make_format("#C38979")
        self.prompt_format = self._make_format("#818181")
        self.error_format = self._make_format("#CB0000")

        self.rehighlight()

    @staticmethod
    def _make_format(color, bold=False):
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))

        if bold:
            text_format.setFontWeight(QFont.Weight.Bold)

        return text_format

    def _apply_pattern(self, pattern, text, offset, text_format):
        for match in pattern.finditer(text):
            self.setFormat(
                offset + match.start(),
                match.end() - match.start(),
                text_format,
            )

    def highlightBlock(self, text):
        if not text.startswith(self.prompt):
            return

        self.setFormat(0, len(self.prompt), self.prompt_format)

        command_text = text[len(self.prompt) :]
        offset = len(self.prompt)

        self._apply_pattern(
            self.KEYWORD_PATTERN,
            command_text,
            offset,
            self.keyword_format,
        )
        self._apply_pattern(
            self.NUMBER_PATTERN,
            command_text,
            offset,
            self.number_format,
        )
        self._apply_pattern(
            self.OPTION_PATTERN,
            command_text,
            offset,
            self.option_format,
        )

        self._apply_pattern(
            self.STRING_PATTERN,
            command_text,
            offset,
            self.string_format,
        )

        self._apply_pattern(
            self.ERROR_PATTERN,
            command_text,
            offset,
            self.error_format,
        )

        command_match = re.match(r"\s*\S+", command_text)
        if command_match:
            start, end = command_match.span()

            self.setFormat(offset + start, end - start, self.command_format)


class TerminalWidget(QPlainTextEdit):
    """
    Terminal interface for the DayDream command language.
    """

    commandSubmitted = pyqtSignal(str)
    PROMPT = "DayDream - DreamScript >>> "

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setUndoRedoEnabled(False)

        self._input_start = None

        self._history = []
        self._history_index = 0
        self._history_draft = ""
        self.setFont(QFont("Cascadia Code", 11))
        self.setLineWidth(12)

        self.highlighter = DayDreamSyntaxHighlighter(self.document(), self.PROMPT)

        self._write_prompt()

    # -----------------------------------------------------------------
    # Prompt and output
    # -----------------------------------------------------------------

    def _write_prompt(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if cursor.position() and cursor.block().text():
            cursor.insertText("\n")

        cursor.insertText(self.PROMPT)

        self._input_start = cursor.position()
        self._history_index = len(self._history)
        self._history_draft = ""

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _append_text(self, text):
        if not text:
            return

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(str(text))

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def write_output(self, text):
        """Append output produced by the command handler."""
        self._append_text(text)

    # -----------------------------------------------------------------
    # Command input
    # -----------------------------------------------------------------

    def _current_input(self):
        if self._input_start is None:
            return ""

        block = self.document().findBlock(self._input_start)

        if not block.isValid():
            return ""

        offset = self._input_start - block.position()
        return block.text()[offset:]

    def _replace_input(self, text):
        if self._input_start is None:
            return

        cursor = self.textCursor()
        cursor.setPosition(self._input_start)
        cursor.movePosition(
            QTextCursor.MoveOperation.End,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.insertText(text)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _submit_command(self):
        """Submit the complete, unmodified user input to the command handler."""
        command = self._current_input()

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText("\n")

        self.setTextCursor(cursor)
        self._input_start = None

        first_arg = command.strip()

        if first_arg == "clear":
            self.clear()
            self._write_prompt()
            return

        elif first_arg == "help":
            self._append_text(_help)

        if command.strip():
            if not self._history or self._history[-1] != command:
                self._history.append(command)

            self._history_index = len(self._history)
            self.commandSubmitted.emit(command)

        self._write_prompt()

    # -----------------------------------------------------------------
    # Command history
    # -----------------------------------------------------------------

    def _navigate_history(self, direction):
        if not self._history:
            return

        if direction < 0:
            if self._history_index == len(self._history):
                self._history_draft = self._current_input()

            self._history_index = max(0, self._history_index - 1)
        else:
            self._history_index = min(
                len(self._history),
                self._history_index + 1,
            )

        if self._history_index == len(self._history):
            self._replace_input(self._history_draft)
        else:
            self._replace_input(self._history[self._history_index])

    # -----------------------------------------------------------------
    # Input protection
    # -----------------------------------------------------------------

    def _move_to_input_end_if_needed(self):
        if self._input_start is None:
            return

        cursor = self.textCursor()

        if cursor.position() < self._input_start or (
            cursor.hasSelection() and cursor.selectionStart() < self._input_start
        ):
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

    def _remove_range(self, start, end):
        cursor = QTextCursor(self.document())
        cursor.setPosition(start)
        cursor.setPosition(
            end,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.removeSelectedText()

        self.setTextCursor(cursor)

    def cut(self):
        if self._input_start is None:
            return

        cursor = self.textCursor()

        if cursor.hasSelection() and cursor.selectionStart() >= self._input_start:
            super().cut()

    def insertFromMimeData(self, source):
        if self._input_start is None or not source.hasText():
            return

        self._move_to_input_end_if_needed()

        text = source.text()
        text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

        cursor = self.textCursor()
        cursor.insertText(text)
        self.setTextCursor(cursor)

    # -----------------------------------------------------------------
    # Keyboard behavior
    # -----------------------------------------------------------------

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            super().keyPressEvent(event)
            return

        if event.matches(QKeySequence.StandardKey.Cut):
            self.cut()
            return

        if self._input_start is None:
            if event.key() in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
                super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()
        control = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

        # Submit input.
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._submit_command()
            return

        # Navigate command history.
        if modifiers == Qt.KeyboardModifier.NoModifier:
            if key == Qt.Key.Key_Up:
                self._navigate_history(-1)
                return

            if key == Qt.Key.Key_Down:
                self._navigate_history(1)
                return

        # Clear the visible transcript.
        if control and key == Qt.Key.Key_L:
            self.clear()
            self._input_start = None
            self._write_prompt()
            return

        # Move to the beginning or end of the current input.
        if control and key == Qt.Key.Key_A:
            cursor = self.textCursor()
            cursor.setPosition(self._input_start)
            self.setTextCursor(cursor)
            return

        if control and key == Qt.Key.Key_E:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            return

        if key == Qt.Key.Key_Home:
            cursor = self.textCursor()
            cursor.setPosition(self._input_start)
            self.setTextCursor(cursor)
            return

        # Prevent Backspace from deleting the prompt.
        if key == Qt.Key.Key_Backspace:
            cursor = self.textCursor()

            if not cursor.hasSelection() and cursor.position() <= self._input_start:
                return

            if cursor.hasSelection() and cursor.selectionStart() < self._input_start:
                self._move_to_input_end_if_needed()
                return

        # Clear input before the cursor.
        if control and key == Qt.Key.Key_U:
            self._move_to_input_end_if_needed()
            self._remove_range(
                self._input_start,
                self.textCursor().position(),
            )
            return

        # Clear input after the cursor.
        if control and key == Qt.Key.Key_K:
            self._move_to_input_end_if_needed()

            cursor = self.textCursor()
            end = cursor.block().position() + len(cursor.block().text())

            self._remove_range(cursor.position(), end)
            return

        # Delete the word before the cursor.
        if control and key == Qt.Key.Key_W:
            self._move_to_input_end_if_needed()

            cursor = self.textCursor()
            text = self._current_input()
            position = max(
                0,
                cursor.position() - self._input_start,
            )
            position = min(position, len(text))

            start = position

            while start > 0 and text[start - 1].isspace():
                start -= 1

            while start > 0 and not text[start - 1].isspace():
                start -= 1

            self._remove_range(
                self._input_start + start,
                self._input_start + position,
            )
            return

        # Do not let the cursor move into the prompt.
        cursor = self.textCursor()

        if (
            key == Qt.Key.Key_Left
            and not cursor.hasSelection()
            and cursor.position() <= self._input_start
        ):
            return

        self._move_to_input_end_if_needed()
        super().keyPressEvent(event)
