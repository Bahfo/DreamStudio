from editor import *

class ExitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedWidth(300)

        self._bg = "#2B2B2B"
        self._border = "#444444"
        self._text = "#BBBBBB"
        self._btn_hover = "#555555"

        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)

        self.label = QLabel("Confirm Exiting?")
        layout.addWidget(self.label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.yes_button = QPushButton("EXIT DREAMSTUDIO")
        self.yes_button.setObjectName("exitButton")

        self.no_button = QPushButton("CANCEL")

        self.yes_button.clicked.connect(self.accept)
        self.no_button.clicked.connect(self.reject)

        button_layout.addWidget(self.yes_button)
        button_layout.addWidget(self.no_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2B2B2B;
                border: 1px solid #444444;
            }
            QLabel {
                color: #BBBBBB;
                font-size: 14px;
                background-color: transparent;
                padding: 10px 5px;
            }
            QPushButton {
                color: #BBBBBB;
                background-color: transparent;
                border: none;
                border-radius: 2px;
                padding: 8px 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
                color: white;
            }
            QPushButton#exitButton {
                color: #FF5555;
            }
            QPushButton#exitButton:hover {
                background-color: #CC0000;
                color: white;
            }
            QPushButton#exitButton:pressed {
                background-color: #990000;
            }
        """)


class ConfirmDialog(QDialog):
    def __init__(
        self,
        parent=None,
        title="Confirm",
        message="Are you sure?",
        confirm_text="CONFIRM",
        cancel_text="CANCEL",
        destructive=False,
    ):
        super().__init__(parent)
        self._destructive = destructive
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedWidth(300)

        self._bg = "#2B2B2B"
        self._border = "#444444"
        self._text = "#BBBBBB"
        self._btn_hover = "#555555"

        self._build_ui(title, message, confirm_text, cancel_text)
        self._apply_styles()

    def _build_ui(self, title, message, confirm_text, cancel_text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)

        if title:
            self.title_label = QLabel(title)
            title_style = "font-weight: bold; font-size: 15px; margin-bottom: 0px;"
            self.title_label.setStyleSheet(
                f"color: {self._text}; background-color: transparent; {title_style}"
            )
            layout.addWidget(self.title_label)

        self.label = QLabel(message)
        layout.addWidget(self.label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.confirm_btn = QPushButton(confirm_text)
        if self._destructive:
            self.confirm_btn.setObjectName("destructiveButton")

        self.cancel_btn = QPushButton(cancel_text)

        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _apply_styles(self):
        destructive_css = ""
        if self._destructive:
            destructive_css = """
            QPushButton#destructiveButton {
                color: #FF5555;
            }
            QPushButton#destructiveButton:hover {
                background-color: #CC0000;
                color: white;
            }
            QPushButton#destructiveButton:pressed {
                background-color: #990000;
            }
            """

        self.setStyleSheet(
            """
            QDialog {
                background-color: #2B2B2B;
                border: 1px solid #444444;
            }
            QLabel {
                color: #BBBBBB;
                font-size: 14px;
                background-color: transparent;
                padding: 10px 5px;
            }
            QPushButton {
                color: #BBBBBB;
                background-color: transparent;
                border: none;
                border-radius: 2px;
                padding: 8px 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
                color: white;
            }
            """
            + destructive_css
            + """
        """
        )


class RenameDialog(QDialog):
    def __init__(
        self,
        parent=None,
        title="Rename",
        message="Enter new name:",
        current_text="",
        confirm_text="RENAME",
        cancel_text="CANCEL",
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedWidth(320)

        self._bg = "#2B2B2B"
        self._border = "#444444"
        self._text = "#BBBBBB"
        self._btn_hover = "#555555"

        self._error_active = False

        self._build_ui(title, message, current_text, confirm_text, cancel_text)
        self._apply_styles()

    def _build_ui(self, title, message, current_text, confirm_text, cancel_text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet(
                f"color: {self._text}; font-weight: bold; font-size: 15px;"
                f" background-color: transparent; padding: 0px 0px 5px 0px;"
            )
            layout.addWidget(title_label)

        if message:
            msg_label = QLabel(message)
            layout.addWidget(msg_label)

        self.line_edit = QLineEdit(current_text)
        self.line_edit.selectAll()
        self.line_edit.setMinimumHeight(32)
        self.line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.line_edit)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet(
            "color: #FF6B6B; font-size: 11px; padding: 0; background: transparent;"
        )
        self._error_label.hide()
        layout.addWidget(self._error_label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.confirm_btn = QPushButton(confirm_text)
        self.cancel_btn = QPushButton(cancel_text)

        self.confirm_btn.clicked.connect(self._validate)
        self.cancel_btn.clicked.connect(self.reject)

        self.line_edit.returnPressed.connect(self._validate)

        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        self.line_edit.setFocus()

    def _validate(self) -> None:
        if self._error_active:
            return
        name = self.line_edit.text().strip()
        if not name:
            self._show_error()
        else:
            self.accept()

    def _show_error(self) -> None:
        self._error_active = True
        self._error_label.setText("Name cannot be Empty")
        self._error_label.show()
        self.line_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self._bg};
                color: #FF6B6B;
                border: 1px solid #FF6B6B;
                border-radius: 3px;
                padding: 6px 10px;
                font-size: 13px;
            }}
        """)
        self._shake_widget(self.line_edit)

    def _on_text_changed(self, text: str) -> None:
        if self._error_active:
            self._error_active = False
            self._error_label.hide()
            self.line_edit.setStyleSheet("")

    def _shake_widget(self, widget) -> None:
        original = widget.pos()
        group = QSequentialAnimationGroup(self)
        self._shake_group = group

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

        group.finished.connect(lambda: self.line_edit.setFocus())
        group.start()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2B2B2B;
                border: 1px solid #444444;
            }
            QLabel {
                color: #BBBBBB;
                font-size: 14px;
                background-color: transparent;
                padding: 2px 0px;
            }
            QLineEdit {
                background-color: #2B2B2B;
                color: #BBBBBB;
                border: 1px solid #444444;
                border-radius: 3px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #555555;
            }
            QPushButton {
                color: #BBBBBB;
                background-color: transparent;
                border: none;
                border-radius: 2px;
                padding: 8px 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
                color: white;
            }
        """)

    def get_name(self) -> str | None:
        if self.exec() == QDialog.DialogCode.Accepted:
            return self.line_edit.text().strip()
        return None


class ErrorDialog(QDialog):
    def __init__(
        self,
        parent=None,
        title="Confirm",
        message="Are you sure?",
        cancel_text="CANCEL",
        destructive=False,
    ):
        super().__init__(parent)
        self._destructive = destructive
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedWidth(300)

        self._bg = "#2B2B2B"
        self._border = "#444444"
        self._text = "#BBBBBB"
        self._btn_hover = "#555555"

        self._build_ui(title, message, cancel_text)
        self._apply_styles()

    def _build_ui(self, title, message, cancel_text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)

        if title:
            self.title_label = QLabel(title)
            title_style = "font-weight: bold; font-size: 15px; margin-bottom: 0px;"
            self.title_label.setStyleSheet(
                f"color: {self._text}; background-color: transparent; {title_style}"
            )
            layout.addWidget(self.title_label)

        self.label = QLabel(message)
        layout.addWidget(self.label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.cancel_btn = QPushButton(cancel_text)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _apply_styles(self):
        destructive_css = ""
        if self._destructive:
            destructive_css = """
            QPushButton#destructiveButton {
                color: #FF5555;
            }
            QPushButton#destructiveButton:hover {
                background-color: #CC0000;
                color: white;
            }
            QPushButton#destructiveButton:pressed {
                background-color: #990000;
            }
            """

        self.setStyleSheet(
            """
            QDialog {
                background-color: #2B2B2B;
                border: 1px solid #444444;
            }
            QLabel {
                color: #BBBBBB;
                font-size: 14px;
                background-color: transparent;
                padding: 10px 5px;
            }
            QPushButton {
                color: #BBBBBB;
                background-color: transparent;
                border: none;
                border-radius: 2px;
                padding: 8px 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
                color: white;
            }
            """
            + destructive_css
            + """
        """
        )


class UnsavedChangesDialog(QDialog):
    """Dialog that prompts the user when closing editors with unsaved changes.

    Displays a list of dirty files and offers three options:
    - Save All: saves every dirty file and proceeds with the close.
    - Don't Save: discards changes and proceeds with the close.
    - Cancel: aborts the close operation entirely.

    Returns:
        QDialog.DialogCode.Accepted with ``result`` set to one of
        ``"save"``, ``"discard"``, or ``"cancel"``.
    """

    RESULT_SAVE = "save"
    RESULT_DISCARD = "discard"
    RESULT_CANCEL = "cancel"

    def __init__(self, parent=None, dirty_files=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setFixedWidth(400)
        self.result = self.RESULT_CANCEL

        self._bg = "#2B2B2B"
        self._border = "#444444"
        self._text = "#BBBBBB"
        self._list_bg = "#1E1E1E"

        self._dirty_files = dirty_files or []
        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        title = QLabel("Unsaved Changes")
        title.setStyleSheet(
            f"color: {self._text}; font-weight: bold; font-size: 15px;"
            " background-color: transparent;"
        )
        layout.addWidget(title)

        count = len(self._dirty_files)
        if count == 1:
            msg_text = (
                "The following file has unsaved changes. "
                "Do you want to save them?"
            )
        else:
            msg_text = (
                f"{count} files have unsaved changes. "
                "Do you want to save them?"
            )
        msg = QLabel(msg_text)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        self.file_list = QListWidget()
        self.file_list.setFixedHeight(min(count * 24 + 10, 160))
        for name in self._dirty_files:
            item = QListWidgetItem(name)
            self.file_list.addItem(item)
        layout.addWidget(self.file_list)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("SAVE ALL")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.clicked.connect(self._on_save)

        self.discard_btn = QPushButton("DON'T SAVE")
        self.discard_btn.setObjectName("discardButton")
        self.discard_btn.clicked.connect(self._on_discard)

        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.clicked.connect(self._on_cancel)

        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.discard_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _on_save(self):
        self.result = self.RESULT_SAVE
        self.accept()

    def _on_discard(self):
        self.result = self.RESULT_DISCARD
        self.accept()

    def _on_cancel(self):
        self.result = self.RESULT_CANCEL
        self.reject()

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self._bg};
                border: 1px solid {self._border};
            }}
            QLabel {{
                color: {self._text};
                font-size: 13px;
                background-color: transparent;
                padding: 2px 0px;
            }}
            QListWidget {{
                background-color: {self._list_bg};
                color: {self._text};
                border: 1px solid {self._border};
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 3px 6px;
                border-radius: 2px;
            }}
            QListWidget::item:selected {{
                background-color: #214283;
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: #333333;
            }}
            QPushButton {{
                color: {self._text};
                background-color: transparent;
                border: none;
                border-radius: 2px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #555555;
                color: white;
            }}
            QPushButton#saveButton {{
                color: #4A9EE2;
            }}
            QPushButton#saveButton:hover {{
                background-color: #214283;
                color: white;
            }}
            QPushButton#discardButton {{
                color: #FF5555;
            }}
            QPushButton#discardButton:hover {{
                background-color: #CC0000;
                color: white;
            }}
        """)
