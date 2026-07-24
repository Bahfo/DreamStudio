import os

from PyQt6.QtCore import Qt, QEvent, QPoint
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from editor.widgets.QToolButton import ToolbarButton


class StackInfoFrame(QFrame):
    """
    An inline container widget with a red border to display breakpoint
    stack info.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet("""
            StackInfoFrame {
                border: 2px solid #E53935;
                border-radius: 0px;
                background-color: #1E1E1E;
            }
            QLabel {
                color: #D4D4D4;
                font-family: Consolas, "Fira Code", monospace;
                font-size: 12px;
                border: none;
            }
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 6, 10, 6)

        self.title_label = QLabel("<b>Stack Context</b> (Paused)", self)
        self.title_label.setTextFormat(Qt.TextFormat.RichText)

        self.content_label = QLabel("Line frame info goes here...", self)

        self._layout.addWidget(self.title_label)
        self._layout.addWidget(self.content_label)


class DebugControlFrame(QFrame):
    """A compact horizontal frame containing debug action buttons.

    Hidden by default. Shown only when a debug session is active.
    Each button delegates its action to the attached ``DebugSession``.
    """

    _ASSET_BASE = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "assets", "system"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DebugControlFrame")

        self.setStyleSheet("""
            DebugControlFrame {
                border: 1px solid #5F5F5F;
                border-radius: 3px;
            }
        """)
        self.setFixedSize(150, 30)

        # Hide by default until called
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        self._is_dragging = False
        self._drag_start_position = QPoint()

        self.drag_handle = QLabel("⣿")
        self.drag_handle.setStyleSheet("color: #555; padding-right: 4px;")
        self.drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)
        layout.addWidget(self.drag_handle)

        self._session = None

        self.btn_next_breakpoint = self._make_btn(
            "step_forward.png", "Step Over (F10)", "_on_step_over"
        )
        self.btn_previous_breakpoint = self._make_btn(
            "step_back.png", "Step Into (F11)", "_on_step_into"
        )
        self.btn_restart = self._make_btn(
            "replay.png", "Restart (Ctrl+Shift+F5)", "_on_restart"
        )
        self.btn_stop = self._make_btn("stop.png", "Stop (Shift+F5)", "_on_stop")

        for btn in (
            self.btn_previous_breakpoint,
            self.btn_next_breakpoint,
            self.btn_restart,
            self.btn_stop,
        ):
            layout.addWidget(btn)

        self.disable_controls()

        if self.parentWidget():
            self.parentWidget().installEventFilter(self)

    def show_at_default_position(self):
        """Shows the widget at 20% from the left and 10% from
        the top of the parent."""
        parent = self.parentWidget()
        if parent:
            x = int(parent.width() * 0.815)
            y = int(parent.height() * 0.10)
            self.move(x, y)

        self.show()
        self.raise_()

    def _constrain_to_parent(self):
        """Keeps the widget inside the parent's boundaries."""
        parent = self.parentWidget()
        if not parent:
            return

        parent_rect = parent.rect()

        # Calculate bounds
        max_x = parent_rect.width() - self.width()
        max_y = parent_rect.height() - self.height()

        new_x = max(0, min(self.x(), max_x))
        new_y = max(0, min(self.y(), max_y))

        if new_x != self.x() or new_y != self.y():
            self.move(new_x, new_y)

    def eventFilter(self, obj, event):
        """Listens to the parent's resize events to adjust position automatically."""
        if obj == self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._constrain_to_parent()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_position = event.pos()
            self.raise_()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            # Calculate new position relative to the parent
            new_pos = self.mapToParent(event.pos() - self._drag_start_position)
            self.move(new_pos)
            self._constrain_to_parent()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

    def _make_btn(self, icon_name, tooltip, handler_name):
        icon_path = os.path.join(self._ASSET_BASE, icon_name)
        btn = ToolbarButton(
            icon_path=icon_path,
            tooltip=tooltip,
            fixed_size=(28, 26),
            icon_size=(19, 19),
        )
        btn.clicked.connect(getattr(self, handler_name))
        return btn

    def set_session(self, session):
        self._session = session

    def enable_controls(self):
        for btn in (
            self.btn_next_breakpoint,
            self.btn_previous_breakpoint,
            self.btn_restart,
            self.btn_stop,
        ):
            btn.setEnabled(True)

    def disable_controls(self):
        for btn in (
            self.btn_next_breakpoint,
            self.btn_previous_breakpoint,
            self.btn_restart,
            self.btn_stop,
        ):
            btn.setEnabled(False)

    def _on_step_over(self):
        if self._session:
            self._session.step_over()

    def _on_step_into(self):
        if self._session:
            self._session.step_into()

    def _on_restart(self):
        if self._session:
            self._session.restart()

    def _on_stop(self):
        if self._session:
            self._session.stop()
