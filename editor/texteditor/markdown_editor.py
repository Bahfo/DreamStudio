from PyQt6.QtWidgets import (
    QWidget,
    QPlainTextEdit,
    QTextBrowser,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QFileDialog,
    QPushButton,
)
from PyQt6.QtCore import QTimer, Qt

import re

import markdown


class MarkdownViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Markdown Editor Engine")
        self.setMinimumSize(900, 600)

        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
        """)

        self._preview_visible = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        toolbar.setContentsMargins(0, 0, 0, 0)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setCheckable(True)
        self.preview_btn.setChecked(False)
        self.preview_btn.clicked.connect(self.toggle_preview)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3f41;
                color: #dcdcdc;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 12px;
                font-family: Inter;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4d50;
            }
            QPushButton:checked {
                background-color: #264f78;
                border-color: #4fc1ff;
            }
        """)

        toolbar.addStretch()
        toolbar.addWidget(self.preview_btn)
        layout.addLayout(toolbar)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("# Markdown...\nStart typing here")

        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1f22;
                color: #dcdcdc;
                border: 1px solid #3c3f41;
                border-radius: 6px;
                padding: 10px;
                font-family: JetBrains Mono;
                font-size: 14px;
                selection-background-color: #264f78;
                selection-color: #ffffff;
            }

            QScrollBar:vertical {
                background: #2b2b2b;
                width: 8px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background: #555;
                min-height: 25px;
            }

            QScrollBar::handle:vertical:hover {
                background: #6a6a6a;
            }

            QScrollBar:horizontal {
                background: #2b2b2b;
                height: 8px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:horizontal {
                background: #555;
                min-width: 25px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #6a6a6a;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
                border: none;
            }
        """)

        self.preview = QTextBrowser()
        self.preview.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.preview.setOpenExternalLinks(True)
        self.preview.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1f22;
                color: #d4d4d4;
                border: 1px solid #3c3f41;
                border-radius: 6px;
                padding: 10px;
                font-family: Inter;
                font-size: 14px;
            }
        """)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setHandleWidth(6)

        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3c3f41;
            }

            QSplitter::handle:hover {
                background-color: #4a4d50;
            }
        """)

        self.splitter.setSizes([1, 0])

        layout.addWidget(self.splitter)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(300)

        self.editor.textChanged.connect(self.schedule_updates)
        self.timer.timeout.connect(self.update_preview)

        self.update_preview()

    def toggle_preview(self):
        self._preview_visible = not self._preview_visible
        if self._preview_visible:
            total = self.splitter.width()
            self.splitter.setSizes([total // 2, total // 2])
            self.preview_btn.setText("Editor")
        else:
            self.splitter.setSizes([1, 0])
            self.preview_btn.setText("Preview")

    def _base_html(self, body_html: str) -> str:
        return f"""<html>
            <head><style>
            body {{ font-family: 'Inter', sans-serif;
            font-size: 14px; line-height: 1.6; padding: 22px; margin: 0; }}
            h1, h2, h3 {{ color: #ffffff; border-bottom: 1px solid #3c3f41; padding-bottom: 6px; }}
            h1 {{ font-size: 24px; }} h2 {{ font-size: 20px; }} h3 {{ font-size: 17px; }}
            code {{ background: #2b2d30; color: #dcdcaa; padding: 2px 6px; border-radius: 4px;
                   font-family: 'JetBrains Mono', 'Consolas', monospace; }}
            pre {{ background: #26292c; border: 1px solid #3c3f41; padding: 12px; border-radius: 8px;
                  white-space: pre; overflow-x: auto; }}
            pre code {{ background: none; padding: 0; font-family: 'JetBrains Mono', 'Consolas', monospace; }}
            blockquote {{ border-left: 4px solid #4fc1ff; padding: 8px 12px; margin: 12px 0;
            color: #9aa0a6; background: #222427; }}
            a {{ color: #4fc1ff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #3c3f41; padding: 8px; text-align: left; }}
            th {{ background: #26292c; }}
            </style></head>
            <body>{body_html}</body></html>"""

    def load_file(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.update_preview()
        except Exception as e:
            self.editor.setPlainText(f"Error loading file:\n{e}")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Markdown File", "", "Markdown Files (*.md);;All Files (*)"
        )
        if path:
            self.load_file(path)

    @staticmethod
    def _sanitize_html(html: str) -> str:
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'\bon\w+\s*=\s*"[^"]*"', '', html, flags=re.IGNORECASE)
        html = re.sub(r"\bon\w+\s*=\s*'[^']*'", '', html, flags=re.IGNORECASE)
        html = re.sub(r'\bon\w+\s*=\s*\w+', '', html, flags=re.IGNORECASE)
        html = re.sub(r'href\s*=\s*"javascript:[^"]*"', 'href="#"', html, flags=re.IGNORECASE)
        html = re.sub(r"href\s*=\s*'javascript:[^']*'", "href='#'", html, flags=re.IGNORECASE)
        html = re.sub(r'src\s*=\s*"javascript:[^"]*"', 'src="#"', html, flags=re.IGNORECASE)
        html = re.sub(r"src\s*=\s*'javascript:[^']*'", "src='#'", html, flags=re.IGNORECASE)
        return html

    def schedule_updates(self):
        self.timer.start()

    def update_preview(self):
        text = self.editor.toPlainText()
        if not text.strip():
            self.preview.setHtml(self._base_html(""))
            return
        try:
            raw_html = markdown.markdown(text, extensions=["fenced_code", "tables"])
            safe_html = self._sanitize_html(raw_html)
            self.preview.setHtml(self._base_html(safe_html))
        except Exception as e:
            self.preview.setPlainText(f"Render error: {e}")
