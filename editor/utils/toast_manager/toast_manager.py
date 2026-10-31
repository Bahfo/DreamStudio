"""Toast notification manager for DreamStudio."""

from editor import *

from editor.utils.notifications.notification_manager import (
    Notification,
    NotificationType,
)


class ToastNotification(QFrame):
    """Individual toast notification widget."""

    dismissed = pyqtSignal(object)

    COLORS = {
        NotificationType.INFO: "#3794FF",
        NotificationType.SUCCESS: "#3FB950",
        NotificationType.WARNING: "#D29922",
        NotificationType.ERROR: "#F85149",
    }

    def __init__(
        self, notification: Notification, duration: int = 4000, parent=None
    ) -> None:
        super().__init__(parent)

        self.notification = notification
        self.duration = duration

        self.setObjectName("ToastNotification")
        self.setFixedWidth(340)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._setup_ui()
        self._setup_animation()

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.dismiss)

    def _setup_ui(self) -> None:
        """Build the toast interface."""
        accent = self.COLORS.get(self.notification.notification_type, "#3794FF")

        self.setStyleSheet(f"""
            QFrame#ToastNotification {{
                border-left: 3px solid {accent};
                border-radius: 0px;}}
            QLabel {{
                background: transparent;
                border: none;}}
            QLabel#ToastTitle {{
                font-size: 13px;
                font-weight: 600;}}
            QLabel#ToastMessage {{font-size: 12px;}}
            QLabel#ToastSource {{font-size: 10px;}}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel(self.notification.title)
        title.setObjectName("ToastTitle")

        close_button = QLabel("×")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setStyleSheet("""
            color: #999999;
            font-size: 17px;
        """)

        close_button.mousePressEvent = lambda event: self.dismiss()

        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_button)

        layout.addLayout(header)

        message = QLabel(self.notification.message)
        message.setObjectName("ToastMessage")
        message.setWordWrap(True)

        layout.addWidget(message)

        if self.notification.source:
            source = QLabel(self.notification.source)
            source.setObjectName("ToastSource")
            layout.addWidget(source)

    def _setup_animation(self) -> None:
        """Configure opacity animations."""
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)

        self.setGraphicsEffect(self.opacity_effect)

        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_in.setDuration(180)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_out.setDuration(160)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out.finished.connect(self._finish_dismiss)

    def show_toast(self) -> None:
        """Display the toast with an entrance animation."""

        self.show()
        self.raise_()
        self.fade_in.start()
        self.timer.start(self.duration)

    def dismiss(self) -> None:
        """Dismiss the toast with an exit animation."""
        if self.fade_out.state() == QPropertyAnimation.State.Running:
            return

        self.timer.stop()
        self.fade_in.stop()

        self.fade_out.setStartValue(self.opacity_effect.opacity())
        self.fade_out.start()

    def _finish_dismiss(self) -> None:
        self.hide()
        self.dismissed.emit(self)
        self.deleteLater()


class ToastManager(QObject):
    """Manage floating toast notifications."""

    def __init__(
        self, parent: QWidget, duration: int = 4000, max_visible: int = 5
    ) -> None:
        super().__init__(parent)

        self.window = parent
        self.duration = duration
        self.max_visible = max(1, max_visible)

        self.margin = 40
        self.spacing = 10

        self._toasts: list[ToastNotification] = []
        self.window.installEventFilter(self)

    def show_notification(self, notification: Notification) -> None:
        """Create and display a toast notification."""
        if len(self._toasts) >= self.max_visible:
            oldest = self._toasts.pop(0)
            oldest.dismiss()

        toast = ToastNotification(
            notification,
            duration=self.duration,
            parent=self.window,
        )

        toast.dismissed.connect(self._on_toast_dismissed)
        self._toasts.append(toast)
        toast.adjustSize()
        self._reposition_toasts()
        toast.show_toast()

    def _reposition_toasts(self) -> None:
        """Position notifications above the bottom-right corner."""
        bottom = self.window.height() - self.margin
        for toast in reversed(self._toasts):
            toast.adjustSize()
            bottom -= toast.height()

            x = self.window.width() - toast.width() - self.margin
            y = bottom

            toast.move(x, y)
            bottom -= self.spacing

    def _on_toast_dismissed(self, toast: ToastNotification) -> None:
        """Remove dismissed notifications and reposition remaining ones."""
        self._toasts = [item for item in self._toasts if item is not toast]
        self._reposition_toasts()

    def eventFilter(self, watched, event) -> bool:
        """Keep notifications positioned when the main window resizes."""
        if watched is self.window:
            if event.type() in (
                QEvent.Type.Resize,
                QEvent.Type.Show,
            ):
                self._reposition_toasts()

        return super().eventFilter(watched, event)
