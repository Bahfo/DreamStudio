from PyQt6.QtWidgets import (
    QWidget, QPlainTextEdit, QTextBrowser, QVBoxLayout, QSplitter, QFileDialog,
)
from PyQt6.QtCore import QTimer, Qt

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

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
                width: 10px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 4px;
                min-height: 25px;
            }

            QScrollBar::handle:vertical:hover {
                background: #6a6a6a;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
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
                font-family: JetBrains Mono, Consolas, monospace;
                font-size: 14px;
            }
        """)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(6)

        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3c3f41;
            }

            QSplitter::handle:hover {
                background-color: #4a4d50;
            }
        """)

        layout.addWidget(splitter)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(300)

        self.editor.textChanged.connect(self.schedule_updates)
        self.timer.timeout.connect(self.update_preview)

        self.update_preview()

    def _base_html(self, body_html: str) -> str:
        return f"""<html>
<head><style>
body {{ font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 14px; line-height: 1.6; padding: 22px; margin: 0; }}
h1, h2, h3 {{ color: #ffffff; border-bottom: 1px solid #3c3f41; padding-bottom: 6px; }}
h1 {{ font-size: 24px; }} h2 {{ font-size: 20px; }} h3 {{ font-size: 17px; }}
code {{ background: #2b2d30; color: #dcdcaa; padding: 2px 6px; border-radius: 4px; }}
pre {{ background: #26292c; border: 1px solid #3c3f41; padding: 12px; border-radius: 8px; }}
pre code {{ background: none; }}
blockquote {{ border-left: 4px solid #4fc1ff; padding: 8px 12px; margin: 12px 0; color: #9aa0a6; background: #222427; }}
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

    def schedule_updates(self):
        self.timer.start()

    def update_preview(self):
        text = self.editor.toPlainText()
        if not text.strip():
            self.preview.setHtml(self._base_html(""))
            return
        try:
            html = markdown.markdown(text, extensions=["fenced_code", "tables"])
            self.preview.setHtml(self._base_html(html))
        except Exception as e:
            self.preview.setPlainText(f"Render error: {e}")
