"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Centralized notification manager for DreamStudio.
"""

from editor import *
from datetime import datetime


logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Notification severity/type classification."""

    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"


@dataclass
class Notification:
    """Data model for a single notification."""

    id: int = 0
    title: str = ""
    message: str = ""
    notification_type: NotificationType = NotificationType.INFO
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    dismissed: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.notification_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "dismissed": self.dismissed,
        }


class NotificationManager(QObject):
    """Notification manager for DreamStudio."""

    notification_added = pyqtSignal(object)
    notification_removed = pyqtSignal(int)
    notifications_cleared = pyqtSignal()

    def __init__(self, parent=None) -> None:
        """Initialize the notification manager."""
        super().__init__(parent)
        self._notifications: list[Notification] = []
        self._next_id: int = 1
        self._max_notifications: int = 100
        import threading as _threading

        self._lock = _threading.Lock()
        logger.info("NotificationManager initialized")


    def add_notification(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        source: str = "",
    ) -> Notification:
        """Add a new notification."""
        notification = Notification(
            id=self._next_id,
            title=title,
            message=message,
            notification_type=notification_type,
            source=source,
        )
        with self._lock:
            self._next_id += 1

            self._notifications.append(notification)

            if len(self._notifications) > self._max_notifications:
                self._notifications = self._notifications[-self._max_notifications :]

        self.notification_added.emit(notification)
        logger.debug(
            "Notification added: [%s] %s - %s",
            notification_type.value,
            title,
            message,
        )
        return notification

    def add_warning(self, title: str, message: str, source: str = "") -> Notification:
        """Convenience method to add a warning notification."""
        return self.add_notification(title, message, NotificationType.WARNING, source)

    def add_error(self, title: str, message: str, source: str = "") -> Notification:
        """Convenience method to add an error notification."""
        return self.add_notification(title, message, NotificationType.ERROR, source)

    def add_success(self, title: str, message: str, source: str = "") -> Notification:
        """Convenience method to add a success notification."""
        return self.add_notification(title, message, NotificationType.SUCCESS, source)

    def add_info(self, title: str, message: str, source: str = "") -> Notification:
        """Convenience method to add an info notification."""
        return self.add_notification(title, message, NotificationType.INFO, source)

    def dismiss_notification(self, notification_id: int) -> bool:
        """Dismiss a notification by its ID."""
        for notification in self._notifications:
            if notification.id == notification_id:
                notification.dismissed = True
                self.notification_removed.emit(notification_id)
                return True
        return False

    def clear_all(self) -> None:
        """Clear all notifications."""
        self._notifications.clear()
        self.notifications_cleared.emit()

    def get_notifications(self) -> list[Notification]:
        """Return all non-dismissed notifications."""
        return [n for n in self._notifications if not n.dismissed]

    def get_all_notifications(self) -> list[Notification]:
        """Return all notifications including dismissed ones."""
        return list(self._notifications)

    def notification_count(self) -> int:
        """Return the count of non-dismissed notifications."""
        return len(self.get_notifications())


_instance: Optional["NotificationManager"] = None


def get_notification_manager() -> "NotificationManager":
    """Get the singleton NotificationManager instance."""
    global _instance
    if _instance is None:
        _instance = NotificationManager()
    return _instance
