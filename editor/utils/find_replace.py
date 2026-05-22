import re

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QSizePolicy,
    QLineEdit,
    QLabel,
    QFrame,
)


class FindReplaceWidget(QFrame):

    FIND_ALL_INDICATOR = 11
    CURRENT_MATCH_INDICATOR = 12
    NO_MATCH_INDICATOR = 13

    def __init__(self, editor_container, tab_widget, parent=None):
        super().__init__(parent or editor_container)
        self.editor_container = editor_container
        self.tab_widget = tab_widget
        self._matches = []
        self._current_match = -1
        self._last_tab = None

        self.setObjectName("findReplaceWidget")
        self.setFixedHeight(76)
        self.setFixedWidth(430)

        self.setStyleSheet("""
            QFrame#findReplaceWidget {
                background-color: #252526;
                border: 1px solid #454545;
                border-radius: 4px;
            }

            QLineEdit {
                background-color: #3C3C3C;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                padding: 4px;
                font-family: "JetBrains Mono";
                font-size: 12px;
            }

            QLineEdit:focus {
                border: 1px solid #007ACC;
            }

            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
                color: #858585;
                padding: 3px 6px;
            }

            QPushButton:hover {
                background-color: #3A3A3C;
            }

            QPushButton:checked {
                background-color: #007ACC;
                color: white;
            }

            QLabel {
                color: #C5C5C5;
                font-size: 11px;
                background-color: #252526;
            }
        """)

        self._setup_ui()
        self.hide()

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._refresh_live_search)

    # UI
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(5)

        # ---------------- FIND ROW ----------------
        find_row = QHBoxLayout()
        find_row.setSpacing(4)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find")
        self.btn_case = QPushButton("Aa")
        self.btn_case.setCheckable(True)
        self.btn_word = QPushButton("ab")
        self.btn_word.setCheckable(True)
        self.btn_regex = QPushButton(".*")
        self.btn_regex.setCheckable(True)
        self.result_label = QLabel("")
        self.btn_prev = QPushButton("↑")
        self.btn_next = QPushButton("↓")
        self.btn_close = QPushButton("✕")

        find_row.addWidget(self.find_input)
        find_row.addWidget(self.btn_case)
        find_row.addWidget(self.btn_word)
        find_row.addWidget(self.btn_regex)
        find_row.addWidget(self.result_label)
        find_row.addWidget(self.btn_prev)
        find_row.addWidget(self.btn_next)
        find_row.addWidget(self.btn_close)

        # ---------------- REPLACE ROW ----------------
        replace_row = QHBoxLayout()
        replace_row.setSpacing(4)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace")
        self.btn_replace = QPushButton("Replace")
        self.btn_replace_all = QPushButton("All")
        replace_row.addWidget(self.replace_input)
        replace_row.addWidget(self.btn_replace)
        replace_row.addWidget(self.btn_replace_all)
        layout.addLayout(find_row)
        layout.addLayout(replace_row)

        # ---------------- SIGNALS ----------------
        self.find_input.textChanged.connect(self._schedule_live_search)
        self.btn_case.clicked.connect(self._refresh_live_search)
        self.btn_word.clicked.connect(self._refresh_live_search)
        self.btn_regex.clicked.connect(self._refresh_live_search)
        self.btn_next.clicked.connect(lambda: self._navigate(True))
        self.btn_prev.clicked.connect(lambda: self._navigate(False))
        self.find_input.returnPressed.connect(lambda: self._navigate(True))
        self.replace_input.returnPressed.connect(self.replace_next)
        self.btn_replace.clicked.connect(self.replace_next)
        self.btn_replace_all.clicked.connect(self.replace_all)
        self.btn_close.clicked.connect(self.close_panel)

    # Floating overlay positioning
    def reposition(self):
        if not self.parent():
            return
        margin = 12
        x = self.parent().width() - self.width() - margin
        y = margin
        self.setGeometry(x, y, self.width(), self.height())

    # Visibility
    def open_panel(self):
        self.show()
        self.raise_()
        self.reposition()
        editor = self._get_editor()
        if editor and editor.hasSelectedText():
            self.find_input.setText(editor.selectedText())
        self.find_input.setFocus()
        self.find_input.selectAll()
        self._refresh_live_search()

    def close_panel(self):
        editor = self._get_editor()
        if editor:
            self._clear_indicators(editor)
        self.hide()
        if editor:
            editor.setFocus()

    # Editor access
    def _get_editor(self):
        editor = self.tab_widget.currentWidget()
        if editor != self._last_tab:
            self._matches.clear()
            self._current_match = -1
            self._last_tab = editor
        return editor

    # Utility
    def _cursor_pos(self, editor):
        line, index = editor.getCursorPosition()
        return editor.positionFromLineIndex(line, index)

    def _set_selection(self, editor, start, end):
        s_line, s_idx = editor.lineIndexFromPosition(start)
        e_line, e_idx = editor.lineIndexFromPosition(end)
        editor.setSelection(s_line, s_idx, e_line, e_idx)
        editor.setCursorPosition(e_line, e_idx)
        editor.ensureLineVisible(s_line)

    # Indicator operations
    def _clear_indicators(self, editor):
        length = editor.length()
        end_line, end_index = editor.lineIndexFromPosition(length)
        for indicator in (
            self.FIND_ALL_INDICATOR,
            self.CURRENT_MATCH_INDICATOR,
            self.NO_MATCH_INDICATOR,
        ):
            editor.clearIndicatorRange(0, 0, end_line, end_index, indicator)

    def _fill_indicator(self, editor, start, end, indicator):
        s_line, s_idx = editor.lineIndexFromPosition(start)
        e_line, e_idx = editor.lineIndexFromPosition(end)
        editor.fillIndicatorRange(s_line, s_idx, e_line, e_idx, indicator)

    # Match building
    def _build_matches(self, editor):
        pattern = self.find_input.text()
        if not pattern:
            return []
        text = editor.text()
        case_sensitive = self.btn_case.isChecked()
        use_regex = self.btn_regex.isChecked()
        whole_word = self.btn_word.isChecked()
        flags = 0 if case_sensitive else re.IGNORECASE
        matches = []
        if not use_regex:
            pattern = re.escape(pattern)
        if whole_word:
            pattern = rf"\b{pattern}\b"
        try:
            for m in re.finditer(pattern, text, flags):
                matches.append((m.start(), m.end()))
        except re.error:
            return []
        return matches

    # Live search
    def _schedule_live_search(self):
        self.search_timer.start(120)

    def _refresh_live_search(self):
        editor = self._get_editor()
        if not editor:
            return
        self._clear_indicators(editor)
        self._matches = self._build_matches(editor)
        if not self.find_input.text():
            self.result_label.setText("")
            return
        if not self._matches:
            self.result_label.setText("No matches")
            self.result_label.setStyleSheet("color: #FF5555;")
            return
        self.result_label.setStyleSheet("color: #C5C5C5;")
        self.result_label.setText(f"{len(self._matches)} matches")
        for s, e in self._matches:
            self._fill_indicator(editor, s, e, self.FIND_ALL_INDICATOR)
        self._current_match = -1

    # Navigation
    def _navigate(self, forward=True):
        editor = self._get_editor()
        if not editor:
            return
        if not self._matches:
            self._refresh_live_search()
        if not self._matches:
            return
        cursor = self._cursor_pos(editor)
        next_index = None
        if forward:
            for i, (s, e) in enumerate(self._matches):
                if s > cursor:
                    next_index = i
                    break
            if next_index is None:
                next_index = 0
        else:
            for i in range(len(self._matches) - 1, -1, -1):
                if self._matches[i][0] < cursor:
                    next_index = i
                    break

            if next_index is None:
                next_index = len(self._matches) - 1
        self._current_match = next_index
        self._clear_indicators(editor)
        for s, e in self._matches:
            self._fill_indicator(editor, s, e, self.FIND_ALL_INDICATOR)
        s, e = self._matches[next_index]
        self._fill_indicator(editor, s, e, self.CURRENT_MATCH_INDICATOR)
        self._set_selection(editor, s, e)
        self.result_label.setText(f"{next_index + 1} of {len(self._matches)}")

    # Replace
    def replace_next(self):
        editor = self._get_editor()
        if not editor:
            return
        if not self._matches:
            self._refresh_live_search()
        if not self._matches:
            return
        if self._current_match < 0:
            self._navigate(True)
        if self._current_match < 0:
            return
        replace_text = self.replace_input.text()
        start, end = self._matches[self._current_match]
        s_line, s_idx = editor.lineIndexFromPosition(start)
        e_line, e_idx = editor.lineIndexFromPosition(end)
        editor.beginUndoAction()
        try:
            editor.setSelection(s_line, s_idx, e_line, e_idx)
            if self.btn_regex.isChecked():
                original = editor.selectedText()
                pattern = self.find_input.text()
                flags = 0 if self.btn_case.isChecked() else re.IGNORECASE
                replaced = re.sub(pattern, replace_text, original, flags=flags)
                editor.replaceSelectedText(replaced)
            else:
                editor.replaceSelectedText(replace_text)
        finally:
            editor.endUndoAction()

        self._refresh_live_search()
        self._navigate(True)

    def replace_all(self):
        editor = self._get_editor()
        if not editor:
            return
        self._refresh_live_search()
        if not self._matches:
            return
        replace_text = self.replace_input.text()
        pattern = self.find_input.text()
        use_regex = self.btn_regex.isChecked()
        flags = 0 if self.btn_case.isChecked() else re.IGNORECASE
        editor.beginUndoAction()
        try:
            for start, end in reversed(self._matches):
                s_line, s_idx = editor.lineIndexFromPosition(start)
                e_line, e_idx = editor.lineIndexFromPosition(end)
                editor.setSelection(s_line, s_idx, e_line, e_idx)
                original = editor.selectedText()
                if use_regex:
                    replaced = re.sub(pattern, replace_text, original, flags=flags)
                    editor.replaceSelectedText(replaced)
                else:
                    editor.replaceSelectedText(replace_text)
        finally:
            editor.endUndoAction()
        self._refresh_live_search()

    # Events
    def retheme(self, t) -> None:
        self.setStyleSheet(f"""
            QFrame#findReplaceWidget {{
                background-color: {t.color("find_replace.background")};
                border: 1px solid {t.color("find_replace.border")};
                border-radius: 4px;
            }}
            QLineEdit {{
                background-color: {t.color("find_replace.input_bg")};
                color: {t.color("input.text")};
                border: 1px solid {t.color("input.border")};
                border-radius: 2px;
                padding: 4px;
                font-family: "JetBrains Mono";
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {t.color("input.focus_border")};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 2px;
                color: {t.color("widget.text")};
                padding: 3px 6px;
            }}
            QPushButton:hover {{
                background-color: {t.color("button.hover")};
            }}
            QPushButton:checked {{
                background-color: {t.color("widget.accent")};
                color: white;
            }}
            QLabel {{
                color: {t.color("find_replace.result_match")};
                font-size: 11px;
                background-color: {t.color("find_replace.background")};
            }}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reposition()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_panel()
            return
        if (
            event.key() == Qt.Key.Key_Return
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._navigate(False)
            return
        super().keyPressEvent(event)


class GlobalFileSearchEngine(QFrame):
    def __init__(self, _parent=None):
        super().__init__()
        self._parent = _parent
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setStyleSheet("background-color: #171717; border: none;")

        self._init_ui()

    def _init_ui(self):
        self._layout = QVBoxLayout(self)

        self._layout.addSpacing(10)
        self.search_label = QLabel("FIND AND REPLACE")
        self.search_label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        self._layout.addWidget(self.search_label)
        self._layout.addSpacing(10)

        find_row = QHBoxLayout()
        find_row.setSpacing(4)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find")
        self.btn_case = QPushButton("Aa")
        self.btn_case.setCheckable(True)
        self.btn_word = QPushButton("ab")
        self.btn_word.setCheckable(True)
        self.btn_regex = QPushButton(".*")
        self.btn_regex.setCheckable(True)
        self.result_label = QLabel("")
        self.btn_prev = QPushButton("↑")
        self.btn_next = QPushButton("↓")
        self.btn_close = QPushButton("✕")

        find_row.addWidget(self.find_input)
        find_row.addWidget(self.btn_case)
        find_row.addWidget(self.btn_word)
        find_row.addWidget(self.btn_regex)
        find_row.addWidget(self.result_label)
        find_row.addWidget(self.btn_prev)
        find_row.addWidget(self.btn_next)
        find_row.addWidget(self.btn_close)

        replace_row = QHBoxLayout()
        replace_row.setSpacing(4)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace")
        self.btn_replace = QPushButton("Replace")
        self.btn_replace_all = QPushButton("All")
        replace_row.addWidget(self.replace_input)
        replace_row.addWidget(self.btn_replace)
        replace_row.addWidget(self.btn_replace_all)

        self._layout.addLayout(find_row)
        self._layout.addLayout(replace_row)

        self._layout.addSpacing(20)
        self.constraints_label = QLabel("SEARCH CONSTRAINTS")
        self.constraints_label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        self._layout.addWidget(self.constraints_label)
        self._layout.addSpacing(10)

        self.file_mask_input = QLineEdit()
        self.file_mask_input.setPlaceholderText("File Mask (.*)")
        self._layout.addWidget(self.file_mask_input)

        options_row = QHBoxLayout()
        options_row.setSpacing(4)
        self.btn_inProject = QPushButton("In Project")
        self.btn_inProject.setCheckable(True)
        self.btn_inProject.setFixedWidth(90)
        self.btn_Directory = QPushButton("Directory")
        self.btn_Directory.setCheckable(True)
        self.btn_Directory.setFixedWidth(90)
        self.btn_Module = QPushButton("Module")
        self.btn_Module.setCheckable(True)
        self.btn_Module.setFixedWidth(90)
        self.btn_Scope = QPushButton("Scope")
        self.btn_Scope.setCheckable(True)
        self.btn_Scope.setFixedWidth(90)

        options_row.addWidget(self.btn_inProject)
        options_row.addWidget(self.btn_Directory)
        options_row.addWidget(self.btn_Module)
        options_row.addWidget(self.btn_Scope)

        options_row.addStretch()
        self._layout.addLayout(options_row)

        self.setStyleSheet("""
            QFrame#findReplaceWidget {
                background-color: #252526;
                border: 1px solid #454545;
                border-radius: 4px;
            }

            QLineEdit {
                background-color: #3C3C3C;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                padding: 4px;
                font-family: "JetBrains Mono";
                font-size: 12px;
            }

            QLineEdit:focus {
                border: 1px solid #007ACC;
            }

            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
                color: #858585;
                padding: 3px 6px;
            }

            QPushButton:hover {
                background-color: #3A3A3C;
            }

            QPushButton:checked {
                background-color: #007ACC;
                color: white;
            }

            QLabel {
                color: #C5C5C5;
                font-size: 11px;
                background-color: #171717;
            }
        """)

        self._layout.addStretch()

    def retheme(self, t) -> None:
        bg = t.color("find_replace.background")
        border = t.color("find_replace.border")
        input_bg = t.color("find_replace.input_bg")
        txt = t.color("window.text")
        accent = t.color("widget.accent")
        btn_hover = t.color("button.hover")
        self.setStyleSheet(f"""
            QFrame#findReplaceWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {txt};
                border: 1px solid {input_bg};
                border-radius: 2px;
                padding: 4px;
                font-family: "JetBrains Mono";
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 2px;
                color: {txt};
                padding: 3px 6px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
            QPushButton:checked {{
                background-color: {accent};
                color: white;
            }}
            QLabel {{
                color: {txt};
                font-size: 11px;
                background-color: transparent;
            }}
        """)
        self.search_label.setStyleSheet(
            f"color: {txt}; font-size: 11px; font-weight: bold; letter-spacing: 1px; background-color: transparent;"
        )
