"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Notifications panel for DreamStudio.

Displays user-facing notifications as cards with color-coded left borders
based on notification type (WARNING: yellow, ERROR: red, SUCCESS: green,
INFO: blue). Adapts to the current IDE theme via QSS object names.
"""

from editor import *

from editor.utils.panel_shell import PanelShell
from editor.utils.notifications.notification_manager import (
    get_notification_manager,
    Notification,
    NotificationType,
)

NOTIFICATION_COLORS = {
    NotificationType.WARNING: "#F59E0B",
    NotificationType.ERROR: "#EF4444",
    NotificationType.SUCCESS: "#10B981",
    NotificationType.INFO: "#3B82F6",
}


class NotificationCard(QFrame):
    """
    A card widget representing a single notification.

    Displays the notification title, message, and source with a
    color-coded left border based on notification type.
    """

    close_clicked = pyqtSignal(int)

    def __init__(self, notification: Notification, parent=None):
        """Initialize the notification card."""
        super().__init__(parent)
        self._notification = notification
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the card UI."""
        self.setObjectName("NotificationCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        border_color = NOTIFICATION_COLORS.get(
            self._notification.notification_type, "#3B82F6"
        )
        self.setStyleSheet(
            f"QFrame#NotificationCard {{ border-left: 4px solid {border_color}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # --- HEADER ROW ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Title
        title_text = QLabel(self._notification.title)
        title_text.setObjectName("NotificationTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_text.setFont(title_font)
        header_layout.addWidget(title_text)

        header_layout.addStretch()

        # Timestamp
        if self._notification.timestamp:
            time_label = QLabel(self._notification.timestamp.strftime("%H:%M"))
            time_label.setObjectName("NotificationTimestamp")
            header_layout.addWidget(time_label)

        # Close button
        close_btn = QPushButton("x")
        close_btn.setObjectName("NotificationCloseBtn")
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Dismiss")
        close_btn.clicked.connect(
            lambda: self.close_clicked.emit(self._notification.id)
        )
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

        # --- MESSAGE ROW ---
        msg_layout = QHBoxLayout()
        msg_layout.setContentsMargins(0, 0, 0, 0)

        inner_vbox = QVBoxLayout()
        inner_vbox.setSpacing(4)

        message_label = QLabel(self._notification.message)
        message_label.setObjectName("NotificationMessage")
        message_label.setWordWrap(True)
        inner_vbox.addWidget(message_label)

        # Source
        if self._notification.source:
            source_label = QLabel(self._notification.source)
            source_label.setObjectName("NotificationSource")
            inner_vbox.addWidget(source_label)

        msg_layout.addLayout(inner_vbox)
        layout.addLayout(msg_layout)


class NotificationsPanel(PanelShell):
    """
    IDE sidebar panel for displaying user-facing notifications.
    """

    PANEL_OBJECT_NAME = "NotificationsPanel"
    FRAME_OBJECT_NAME = "NotificationsFrame"
    TITLE_OBJECT_NAME = "NotificationsTitle"
    TITLE_TEXT = "Notifications"

    def __init__(self, parent=None):
        """Initialize the Notifications panel."""
        self._notification_manager = get_notification_manager()
        self._cards: dict[int, NotificationCard] = {}
        super().__init__(parent)
        self.setMinimumWidth(350)

        self._notification_manager.notification_added.connect(
            self._on_notification_added
        )
        self._notification_manager.notification_removed.connect(
            self._on_notification_removed
        )
        self._notification_manager.notifications_cleared.connect(
            self._on_notifications_cleared
        )

    def _build_body(self) -> None:
        """Construct the panel body."""
        header_row = QHBoxLayout()
        header_row.setContentsMargins(8, 4, 8, 4)
        header_row.setSpacing(8)

        self._count_label = QLabel("0 notifications")
        self._count_label.setObjectName("NotificationsCountLabel")
        header_row.addWidget(self._count_label)
        header_row.addStretch()

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.setObjectName("NotificationsClearBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._on_clear_all)
        header_row.addWidget(self._clear_btn)

        self._frame_layout.addLayout(header_row)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._notifications_container = QWidget()
        self._notifications_layout = QVBoxLayout(self._notifications_container)
        self._notifications_layout.setContentsMargins(0, 0, 0, 0)
        self._notifications_layout.setSpacing(0)
        self._notifications_layout.addStretch()

        scroll_area.setWidget(self._notifications_container)
        self._frame_layout.addWidget(scroll_area)

        # Empty state
        self._empty_placeholder = QLabel("No new notifications")
        self._empty_placeholder.setObjectName("NotificationsEmpty")
        self._empty_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notifications_layout.insertWidget(0, self._empty_placeholder)

        self._update_count_label()

    def _on_notification_added(self, notification: Notification) -> None:
        """Handle new notification added."""
        if self._empty_placeholder.isVisible():
            self._empty_placeholder.setVisible(False)

        card = NotificationCard(notification)
        card.close_clicked.connect(self._on_dismiss_notification)
        self._cards[notification.id] = card

        self._notifications_layout.insertWidget(0, card)
        self._update_count_label()

    def _on_notification_removed(self, notification_id: int) -> None:
        """Handle notification dismissed."""
        card = self._cards.pop(notification_id, None)
        if card:
            self._notifications_layout.removeWidget(card)
            card.deleteLater()

        if not self._notification_manager.get_notifications():
            self._empty_placeholder.setVisible(True)

        self._update_count_label()

    def _on_notifications_cleared(self) -> None:
        """Handle all notifications cleared."""
        for card in self._cards.values():
            self._notifications_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._empty_placeholder.setVisible(True)
        self._update_count_label()

    def _on_dismiss_notification(self, notification_id: int) -> None:
        """Handle dismiss button click."""
        self._notification_manager.dismiss_notification(notification_id)

    def _on_clear_all(self) -> None:
        """Handle clear all button click."""
        self._notification_manager.clear_all()

    def _update_count_label(self) -> None:
        """Update the notification count label."""
        count = self._notification_manager.notification_count()
        if count == 1:
            self._count_label.setText("1 notification")
        else:
            self._count_label.setText(f"{count} notifications")

    def _header_right_widgets(self) -> list[QWidget]:
        """Provide header widgets."""
        return []
