"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

Background dirty-file tracker for DreamStudio.

Immediate dirty-state synchronization without debounce.
"""

from __future__ import annotations

import logging
import weakref
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class DirtyTracker(QObject):
    """Immediate dirty-state tracker."""

    dirty_state_changed = pyqtSignal(object, bool)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._states = weakref.WeakKeyDictionary()

    def watch(self, editor: QObject) -> None:
        if editor in self._states:
            return
        self._states[editor] = self._query_dirty(editor)
        if hasattr(editor, "textChanged"):
            try:
                editor.textChanged.connect(self._on_editor_changed)
            except Exception:
                logger.exception("Failed to connect textChanged.")
        try:
            editor.destroyed.connect(self._on_editor_destroyed)
        except Exception:
            logger.exception("Failed to connect destroyed.")

    def unwatch(self, editor: QObject) -> None:
        self._states.pop(editor, None)
        if hasattr(editor, "textChanged"):
            try:
                editor.textChanged.disconnect(self._on_editor_changed)
            except Exception:
                pass
        try:
            editor.destroyed.disconnect(self._on_editor_destroyed)
        except Exception:
            pass

    def sync_state(self, editor: QObject) -> None:
        self._update(editor)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def watched_count(self) -> int:
        return len(self._states)

    def _query_dirty(self, editor: QObject) -> bool:
        try:
            if hasattr(editor, "is_dirty"):
                return bool(editor.is_dirty())
            if hasattr(editor, "isModified"):
                return bool(editor.isModified())
        except Exception:
            logger.exception("Dirty query failed.")
        return False

    def _on_editor_changed(self, *args) -> None:
        editor = self.sender()
        if editor is not None:
            self._update(editor)

    def _update(self, editor: QObject) -> None:
        if editor not in self._states:
            return
        current = self._query_dirty(editor)
        previous = self._states.get(editor)
        if current != previous:
            self._states[editor] = current
            self.dirty_state_changed.emit(editor, current)

    def _on_editor_destroyed(self, obj) -> None:
        self._states.pop(obj, None)
