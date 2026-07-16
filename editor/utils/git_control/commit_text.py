from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtCore import Qt


class ExpandingTextEdit(QPlainTextEdit):
    """
    A multi-line text field that expands automatically with text input
    and adapts natively when its parent container layout resizes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Commit message...")
        self.min_h = 50
        self.max_h = 200
        self.setMinimumHeight(self.min_h)
        self.textChanged.connect(self.adjust_height)

    def adjust_height(self) -> None:
        """
        Dynamically adjusts height constraints based on document content.
        """
        doc = self.document()
        doc_h = int(doc.documentLayout().documentSize().height())
        padding = (self.frameWidth() * 2) + 16
        target_h = max(self.min_h, min(doc_h + padding, self.max_h))

        self.setMinimumHeight(target_h)
        if target_h >= self.max_h:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def resizeEvent(self, event) -> None:
        """
        Ensures height matches text requirements when stretched by splitter.
        """
        super().resizeEvent(event)
        self.adjust_height()
