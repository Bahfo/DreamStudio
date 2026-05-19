"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

Background dirty-file tracker for DreamStudio. Listens for editor text changes
and debounces state checks so the tab dirty-dot indicator stays in sync
without poll overhead on the GUI thread.
"""

import logging
from typing import Dict, Optional, Set

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class DirtyTracker(QObject):
    dirty_state_changed = pyqtSignal(object, bool)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._editors: Dict[int, object] = {}
        self._dirty_states: Dict[int, bool] = {}
        self._pending: Set[int] = set()
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(100)
        self._debounce.timeout.connect(self._flush)

    def watch(self, editor: object) -> None:
        eid = id(editor)
        self._editors[eid] = editor
        try:
            self._dirty_states[eid] = editor.is_dirty()
        except RuntimeError:
            pass
        if hasattr(editor, "textChanged"):
            try:
                editor.textChanged.connect(self._on_text_changed)
            except (TypeError, RuntimeError):
                pass

    def unwatch(self, editor: object) -> None:
        eid = id(editor)
        self._editors.pop(eid, None)
        self._dirty_states.pop(eid, None)
        self._pending.discard(eid)
        if hasattr(editor, "textChanged"):
            try:
                editor.textChanged.disconnect(self._on_text_changed)
            except (TypeError, RuntimeError):
                pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        self._debounce.stop()

    def _on_text_changed(self, *args) -> None:
        editor = self.sender()
        if editor is None:
            return
        eid = id(editor)
        if eid in self._editors:
            self._pending.add(eid)
            self._debounce.start()

    def _flush(self) -> None:
        for eid in list(self._pending):
            editor = self._editors.get(eid)
            if editor is None:
                self._pending.discard(eid)
                continue
            try:
                current = editor.is_dirty()
                old = self._dirty_states.get(eid)
                if current != old:
                    self._dirty_states[eid] = current
                    self.dirty_state_changed.emit(editor, current)
            except RuntimeError:
                self._editors.pop(eid, None)
                self._dirty_states.pop(eid, None)
            finally:
                self._pending.discard(eid)
