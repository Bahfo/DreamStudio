from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt

import fitz


class PDFViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc = None
        self.current_page = 0

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.page_label = QLabel("No PDF loaded")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumSize(400, 500)
        self._layout.addWidget(self.page_label, stretch=1)

        # Navigation Controls
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_prev = QPushButton("Previous")
        self.btn_prev.setFixedSize(80, 30)

        self.lbl_page_info = QLabel("Page: 0 / 0")

        self.btn_next = QPushButton("Next")
        self.btn_next.setFixedSize(80, 30)

        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)

        self.controls_layout.addSpacing(10)
        self.controls_layout.addWidget(self.btn_prev)
        self.controls_layout.addWidget(self.lbl_page_info)
        self.controls_layout.addWidget(self.btn_next)
        self.controls_layout.addSpacing(10)

        self._layout.addLayout(self.controls_layout)

    def load_pdf(self, file_path):
        """Opens the PDF and initializes the first page."""
        try:
            self.doc = fitz.open(file_path)
            self.current_page = 0
            self.render_page()
        except Exception as e:
            self.page_label.setText(f"Error loading PDF: {e}")

    def render_page(self):
        """Converts the current PyMuPDF page to a QPixmap."""
        if not self.doc:
            return

        page = self.doc.load_page(self.current_page)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        fmt = (
            QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
        )

        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
        pixmap = QPixmap.fromImage(qimg)

        scaled_pixmap = pixmap.scaled(
            self.page_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.page_label.setPixmap(scaled_pixmap)

        self.lbl_page_info.setText(f"Page: {self.current_page + 1} / {len(self.doc)}")

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()
