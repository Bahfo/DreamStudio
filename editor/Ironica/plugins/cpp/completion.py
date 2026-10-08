"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

The Completion Manager and Object for C++ Extension - DreamStudio.
"""

from __future__ import annotations

import logging
import threading

from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

# Local Imports
from .models import CppContext

logger = logging.getLogger("DreamStudio.Cpp.CompletionManager")
COMPLETION_DEBOUNCE_MS: int = 30  # Thirty milliseconds


@dataclass(frozen=True)
class _CompletionRequest:
    """
    Immutable snapshot for one worker round-trip.
    """

    request_id: int
    context: CppContext


class _CppCompletionWorker(threading.Thread):
    """Runs engine.complete() off the UI thread, latest-wins."""

    def __init__(self, owner: CppCompletionManager, engine) -> None:
        """
        Store owner/engine refs and prepare the wake event.
        """

        super().__init__(
            name="DreamStudio-CppCompletionWorker",
            daemon=True,
        )

        self._owner = owner
        self._engine = engine
        self._wake = threading.Event()
        self._started_once = False
        self._current: Optional[_CompletionRequest] = None
        self._shutting_down = False

    def process(self, request_id: int, context: CppContext) -> None:
        """
        Queue *context*, waking the thread (drops any pending older item).
        """
        if self._shutting_down:
            return
        self._current = _CompletionRequest(request_id, context)
        self._wake.set()
        if not self._started_once:
            self._started_once = True
            self.start()

    def run(self) -> None:
        """
        Consume latest request, emit results unless superseded.
        """
        while not self._shutting_down:
            self._wake.wait(timeout=0.2)
            self._wake.clear()
            request = self._current
            if request is None:
                continue
            self._current = None
            if self._shutting_down:
                continue
            try:
                items = self._engine.complete(request.context) or []
            except Exception as exc:  # Bad input doesn't kill worker
                logger.warning("C++ completion engine failed: %s", exc)
                items = []
            if self._shutting_down or self._current is not None:
                continue
            if request.request_id < self._owner._request_counter:
                continue
            try:
                self._owner.completions_ready.emit(request.request_id, list(items))
            except RuntimeError:
                pass  # owner deleted with its editor

    def shutdown(self) -> None:
        """
        Stop the thread at editor teardown.
        """
        self._shutting_down = True
        self._current = None
        self._wake.set()


class CppCompletionManager(QObject):
    """
    Per-editor debounced completion bridge (editor-scoped,
    never singleton).
    """

    completions_ready = pyqtSignal(int, list)

    def __init__(
        self,
        editor,
        engine,
        file_path=None,
        compile_args=None,
        debounce_ms: int = COMPLETION_DEBOUNCE_MS,
        parent: Optional[QObject] = None,
    ) -> None:
        """
        Wire debounce timer, worker thread, and editor teardown
        guard.
        """

        super().__init__(parent)
        self._editor = editor
        self._engine = engine
        self._file_path = file_path
        self._compile_args = list(compile_args or [])
        self._enabled = True
        self._dead = False
        self._request_counter = 0
        self._pending: Optional[CppContext] = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._on_debounce_fired)
        self._worker = _CppCompletionWorker(self, self._engine)
        destroyed = getattr(editor, "destroyed", None)
        if destroyed is not None:
            destroyed.connect(self._on_editor_destroyed)

    def set_compile_args(self, args: List[str]) -> None:
        """
        Replace include flags.
        """
        self._compile_args = list(args or [])

    def request(
        self,
        source: str,
        line: int,
        col: int,
        file_path: Optional[str] = None,
        prefix: str = "",
    ) -> bool:
        """
        Debounce one completion query; False means use sync fallback.
        """
        if self._dead:
            return False
        try:
            from .context import classify

            line_text = source.splitlines()[line] if source else ""
            kind, _ = classify(line_text, col)
            if kind in ("none", "comment", "preprocessor"):
                return False
        except Exception:
            pass
        self._request_counter += 1
        self._pending = CppContext(
            source_code=source,
            line=line + 1,  # editor 0-indexed -> clang 1-indexed
            col=col + 1,
            file_path=file_path or self._file_path,
            compile_args=list(self._compile_args),
            prefix=prefix or "",
        )
        try:
            self._timer.start()
        except RuntimeError:
            self._dead = True
            return False
        return True

    @pyqtSlot()
    def _on_debounce_fired(self) -> None:
        """
        Submit the pending context to the worker thread.
        """

        if not self._enabled or self._pending is None:
            return
        try:
            self._worker.process(self._request_counter, self._pending)
        except Exception as exc:
            logger.debug("Failed to submit C++ completion: %s", exc)

    @pyqtSlot()
    def _on_editor_destroyed(self) -> None:
        """
        Mark dead during QObject teardown so later request() no-ops.
        """

        try:
            self._timer.stop()
        except RuntimeError:
            pass
        self._dead = True
        self.shutdown()

    def shutdown(self) -> None:
        """
        Disable timer and worker; safe to call twice.
        """

        self._enabled = False
        try:
            self._timer.stop()
        except RuntimeError:
            pass
        self._worker.shutdown()
