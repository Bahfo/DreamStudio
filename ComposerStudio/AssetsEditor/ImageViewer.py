from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolBar, QStyle, QLabel
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtCore import Qt, QSize


class ImageViewer(QWidget):
    def __init__(self, _parent=None):
        super().__init__(_parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))

        self.action_zoom_in = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton),
            "",
            self,
        )
        self.action_zoom_out = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown), "", self
        )
        self.action_reset_zoom = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "", self
        )

        self.toolbar.addAction(self.action_zoom_in)
        self.toolbar.addAction(self.action_zoom_out)
        self.toolbar.addAction(self.action_reset_zoom)

        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(200, 200)

        self._layout.addWidget(self.toolbar)
        self._layout.addWidget(self.image_label)

        self._original_pixmap = None

    def load_image(self, file_path):
        pixmap = QPixmap(file_path)

        if not pixmap.isNull():
            self._original_pixmap = pixmap
            self._update_image()
        else:
            self._original_pixmap = None
            self.image_label.setText("Failed to load image format.")

    def _update_image(self):
        if not self._original_pixmap:
            return

        label_size = self.image_label.size()
        pixmap_size = self._original_pixmap.size()

        if (
            pixmap_size.width() > label_size.width()
            or pixmap_size.height() > label_size.height()
        ):
            scaled = self._original_pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setPixmap(self._original_pixmap)

    def resizeEvent(self, event):
        self._update_image()
        super().resizeEvent(event)
