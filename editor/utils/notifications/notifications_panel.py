"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Notifications panel for DreamStudio.
Displays user-facing notifications mimicking the JetBrains IDE tool window
aesthetic: flat design, color-coded dot indicators, aligned text, and minimal borders.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QWidget,
    QScrollArea,
    QPushButton,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from editor.utils.panel_shell import PanelShell
from editor.utils.notifications.notification_manager import (
    get_notification_manager,
    Notification,
    NotificationType,
)

# Color mapping for notification types (JetBrains-style vibrant indicators)
NOTIFICATION_COLORS = {
    NotificationType.WARNING: "#D4A72C",  # Amber/Gold
    NotificationType.ERROR: "#DB5860",  # Soft Red
    NotificationType.SUCCESS: "#589DF6",  # Standard JB Blue (or use #529B2E for green)
    NotificationType.INFO: "#737373",  # Neutral Gray
}


class NotificationCard(QFrame):
    """
    A flat, JetBrains-style widget representing a single notification.
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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # JetBrains style: transparent background with a subtle hover effect
        # and a very faint bottom border serving as a separator.
        self.setStyleSheet("""
            NotificationCard {
                border-bottom: 1px solid rgba(128, 128, 128, 0.2);
                background-color: transparent;
                margin: 0px;
            }
            NotificationCard:hover {
                background-color: rgba(128, 128, 128, 0.08);
            }
        """)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        # --- HEADER ROW ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # 1. Color-coded Dot Indicator (Instead of a text badge)
        icon_label = QLabel()
        icon_label.setFixedSize(8, 8)
        dot_color = NOTIFICATION_COLORS.get(
            self._notification.notification_type, "#737373"
        )
        icon_label.setStyleSheet(f"""
            background-color: {dot_color};
            border-radius: 4px;
            margin-top: 2px;
        """)
        header_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        # 2. Title
        title_text = QLabel(self._notification.title)
        title_text.setObjectName("NotificationTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_text.setFont(title_font)
        # JetBrains titles usually match the primary text color
        title_text.setStyleSheet("color: palette(window-text); border: none;")
        header_layout.addWidget(title_text, alignment=Qt.AlignmentFlag.AlignTop)

        header_layout.addStretch()

        # 3. Timestamp
        if self._notification.timestamp:
            time_label = QLabel(self._notification.timestamp.strftime("%H:%M"))
            time_label.setStyleSheet(
                "color: palette(mid); font-size: 10px; border: none;"
            )
            header_layout.addWidget(time_label, alignment=Qt.AlignmentFlag.AlignTop)

        # 4. Close Button (Subtle '×')
        close_btn = QPushButton("×")
        close_btn.setObjectName("NotificationCloseBtn")
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Dismiss")
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: palette(mid);
                font-size: 16px;
                font-weight: bold;
                padding-bottom: 2px;
                background: transparent;
            }
            QPushButton:hover {
                color: palette(text);
                background-color: rgba(128, 128, 128, 0.2);
                border-radius: 4px;
            }
        """)
        close_btn.clicked.connect(
            lambda: self.close_clicked.emit(self._notification.id)
        )
        header_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addLayout(header_layout)

        # --- MESSAGE ROW ---
        # Indent the message so it aligns perfectly with the title text
        # (8px icon + 8px spacing = 16px left margin)
        msg_layout = QHBoxLayout()
        msg_layout.setContentsMargins(16, 0, 0, 0)

        inner_vbox = QVBoxLayout()
        inner_vbox.setSpacing(4)

        message_label = QLabel(self._notification.message)
        message_label.setObjectName("NotificationMessage")
        message_label.setWordWrap(True)
        # Slightly muted text for the body
        message_label.setStyleSheet(
            "color: palette(text); opacity: 0.8; font-size: 10px; border: none;"
        )
        inner_vbox.addWidget(message_label)

        # Source link (Optional)
        if self._notification.source:
            source_label = QLabel(self._notification.source)
            # Style like a clickable link or subdued meta-text
            source_label.setStyleSheet("color: #589DF6; font-size: 10px; border: none;")
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
        # Header Toolbar
        header_row = QHBoxLayout()
        header_row.setContentsMargins(8, 4, 8, 4)
        header_row.setSpacing(8)

        self._count_label = QLabel("0 notifications")
        self._count_label.setStyleSheet("color: palette(mid); font-size: 10px;")
        header_row.addWidget(self._count_label)
        header_row.addStretch()

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # JetBrains toolbars often use flat, borderless text buttons that highlight on hover
        self._clear_btn.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 4px 8px;
                font-size: 10px;
                color: #589DF6;
                background: transparent;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 0.15);
                border-radius: 4px;
            }
        """)
        self._clear_btn.clicked.connect(self._on_clear_all)
        header_row.addWidget(self._clear_btn)

        self._frame_layout.addLayout(header_row)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("background: transparent;")

        self._notifications_container = QWidget()
        self._notifications_layout = QVBoxLayout(self._notifications_container)
        # 0 spacing because the cards now handle their own bottom borders/separators
        self._notifications_layout.setContentsMargins(0, 0, 0, 0)
        self._notifications_layout.setSpacing(0)
        self._notifications_layout.addStretch()

        scroll_area.setWidget(self._notifications_container)
        self._frame_layout.addWidget(scroll_area)

        # Empty state
        self._empty_placeholder = QLabel("No new notifications")
        self._empty_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_placeholder.setStyleSheet(
            "color: palette(mid); font-size: 11px; padding: 20px;"
        )
        self._notifications_layout.insertWidget(0, self._empty_placeholder)

        self._update_count_label()

    def _on_notification_added(self, notification: Notification) -> None:
        if self._empty_placeholder.isVisible():
            self._empty_placeholder.setVisible(False)

        card = NotificationCard(notification)
        card.close_clicked.connect(self._on_dismiss_notification)
        self._cards[notification.id] = card

        self._notifications_layout.insertWidget(0, card)
        self._update_count_label()

    def _on_notification_removed(self, notification_id: int) -> None:
        card = self._cards.pop(notification_id, None)
        if card:
            self._notifications_layout.removeWidget(card)
            card.deleteLater()

        if not self._notification_manager.get_notifications():
            self._empty_placeholder.setVisible(True)

        self._update_count_label()

    def _on_notifications_cleared(self) -> None:
        for card in self._cards.values():
            self._notifications_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._empty_placeholder.setVisible(True)
        self._update_count_label()

    def _on_dismiss_notification(self, notification_id: int) -> None:
        self._notification_manager.dismiss_notification(notification_id)

    def _on_clear_all(self) -> None:
        self._notification_manager.clear_all()

    def _update_count_label(self) -> None:
        count = self._notification_manager.notification_count()
        if count == 1:
            self._count_label.setText("1 notification")
        else:
            self._count_label.setText(f"{count} notifications")

    def _header_right_widgets(self) -> list[QWidget]:
        return []
