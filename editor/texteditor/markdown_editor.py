from PyQt6.QtWidgets import QWidget, QPlainTextEdit, QVBoxLayout, QSplitter, QFileDialog
from PyQt6.QtCore import QTimer, Qt

from PyQt6.QtWebEngineWidgets import QWebEngineView

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

        # ---- Layout ----
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # ---- Editor ----
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

        # ---- Preview ----
        self.preview = QWebEngineView()
        self.preview.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.preview.setHtml(self._base_html())

        # ---- Splitter ----
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

        # ---- Debounce ----
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(300)

        self.editor.textChanged.connect(self.schedule_updates)
        self.timer.timeout.connect(self.update_preview)

        self.update_preview()

    def _base_html(self):
        return """
        <html>
        <head>
            <style>
                :root {
                    --bg: #1e1f22;
                    --panel: #26292c;
                    --text: #d4d4d4;
                    --muted: #9aa0a6;
                    --accent: #4fc1ff;
                    --border: #3c3f41;
                }

                body {
                    font-family: JetBrains Mono, Consolas, monospace;
                    background-color: var(--bg);
                    color: var(--text);
                    padding: 22px;
                    margin: 0;
                    line-height: 1.6;
                    font-size: 14px;
                }

                h1, h2, h3 {
                    color: #ffffff;
                    border-bottom: 1px solid var(--border);
                    padding-bottom: 6px;
                    margin-top: 18px;
                }

                h1 { font-size: 24px; }
                h2 { font-size: 20px; }
                h3 { font-size: 17px; }

                p { color: var(--text); }

                code {
                    background: #2b2d30;
                    color: #dcdcaa;
                    padding: 2px 6px;
                    border-radius: 4px;}

                pre {
                    background: var(--panel);
                    border: 1px solid var(--border);
                    padding: 12px;
                    border-radius: 8px;
                    overflow-x: auto;
                }

                pre code { background: none; }

                blockquote {
                    border-left: 4px solid var(--accent);
                    padding: 8px 12px;
                    margin: 12px 0;
                    color: var(--muted);
                    background: #222427;
                }

                a {color: var(--accent);
                   text-decoration: none;}

                a:hover {
                    text-decoration: underline;
                }
                ::-webkit-scrollbar {
                    width: 10px;
                    height: 10px;}
                ::-webkit-scrollbar-track {background: var(--bg);}
                ::-webkit-scrollbar-thumb {
                    background: #4a4d52;
                    border-radius: 6px;}
                ::-webkit-scrollbar-thumb:hover { background: #5a5d62; }
            </style>
        </head>
        <body>
            <div id="content"></div>
        </body>
        </html>
        """

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

        html = markdown.markdown(text, extensions=["fenced_code", "tables", "toc"])

        html = html.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

        js = f"""
            document.getElementById('content').innerHTML = '{html}';
        """

        self.preview.page().runJavaScript(js)
