"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Shared coordinator for background indexing progress.
"""

from editor import *

logger = logging.getLogger(__name__)

MESSAGES = {
    "python": "Please wait while DreamStudio indexes the repository",
    "cpp": "Please wait while DreamStudio indexes C++ sources",
}


class IndexingCoordinator(QObject):
    """Multiplex per-language indexing sessions onto one progress bar."""

    def __init__(self, bar, parent=None) -> None:
        """Bind *bar* driven by per-source indexing sessions."""
        super().__init__(parent)
        self._bar = bar
        self._sessions: dict = {}
        self._order: list = []
        self._messages: dict = {}
        self._bar_source = ""

    @pyqtSlot(str, int, str)
    def start(self, source: str, total: int, message: str = "") -> None:
        """Open (or restart) the indexing session for *source*."""
        total = max(1, int(total))
        self._sessions[source] = [0, total]
        if source in self._order:
            self._order.remove(source)
        self._order.append(source)
        if message:
            self._messages[source] = message
        self._refresh()

    @pyqtSlot(str, int)
    def advance(self, source: str, done: int) -> None:
        """Report *done* processed items for *source*."""
        if source not in self._sessions:
            return
        self._sessions[source][0] = max(0, int(done))
        self._refresh()

    @pyqtSlot(str)
    def finish(self, source: str) -> None:
        """Close the session for *source*, hiding the bar when last."""
        self._sessions.pop(source, None)
        if source in self._order:
            self._order.remove(source)
        self._bar_source = ""
        self._refresh()

    def _refresh(self) -> None:
        """Repaint the bar for the latest active session, if any."""
        try:
            if not self._sessions:
                self._bar.finish_indexing()
                return
            source = self._order[-1]
            done, total = self._sessions[source]
            if self._bar_source != source or not self._bar.isVisible():
                message = self._messages.get(source) or MESSAGES.get(source, "")
                self._bar.start_indexing(total, message)
                self._bar_source = source
            self._bar.advance_indexing(done)
        except Exception as exc:
            logger.debug("indexing coordinator refresh failed: %s", exc)
