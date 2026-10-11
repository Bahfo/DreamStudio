"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

The Completion Manager and Object for C++ Extension - DreamStudio.
"""

from __future__ import annotations

import logging
import re
import threading

from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from editor.Ironica import completion_profile as _profile

# Local Imports
from ..models import CppContext

logger = logging.getLogger("DreamStudio.Cpp.CompletionManager")
COMPLETION_DEBOUNCE_MS: int = 30  # Thirty milliseconds
IDLE_PREQUERY_MS: int = 1500  # Pause before a speculative warm query


@dataclass(frozen=True)
class _CompletionRequest:
    """
    Immutable snapshot for one worker round-trip.
    """

    request_id: int
    context: CppContext
    warmup: bool = False
    prefetch: bool = False


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
        self._running = False
        self._last_hint_key = None
        from .symbols import SymbolsCache

        self._symbols = SymbolsCache()

    def is_busy(self) -> bool:
        """Return ``True`` while a request is queued or executing."""
        return self._current is not None or self._running

    def process(self, request_id: int, context: CppContext,
                warmup: bool = False, prefetch: bool = False) -> None:
        """
        Queue *context*, waking the thread (drops any pending older item).
        """
        if self._shutting_down:
            return
        self._current = _CompletionRequest(request_id, context, warmup, prefetch)
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
            self._running = True
            try:
                _profile.mark(self._owner._editor, "engine-start")
                if request.warmup:
                    self._engine.prime(request.context)
                    self._running = False
                    continue
                if request.prefetch:
                    self._prefetch(request)
                    self._running = False
                    continue
                self._emit_symbol_rows(request)
                items = self._engine.complete(request.context) or []
                if not items and not request.warmup:
                    items = self._index_fallback(request)
                _profile.mark(self._owner._editor, "engine-done")
            except Exception as exc:  # Bad input doesn't kill worker
                logger.warning("C++ completion engine failed: %s", exc)
                items = []
            if self._shutting_down or self._current is not None:
                self._running = False
                continue
            if request.request_id < self._owner._request_counter:
                self._running = False
                continue
            self._maybe_hint(request, items)
            try:
                _profile.mark(self._owner._editor, "emit")
                self._owner.completions_ready.emit(request.request_id, list(items))
            except RuntimeError:
                pass  # owner deleted with its editor
            self._running = False

    def _prefetch(self, request: _CompletionRequest) -> None:
        """Warm TU and completion caches without presenting anything.

        Runs :meth:`prime` plus one discarded :meth:`complete` so the
        next keystroke at this caret finds warm caches. Never emits,
        never raises.

        Args:
            request: The prefetch request carrying the caret context.
        """
        try:
            self._engine.prime(request.context)
            self._engine.complete(request.context)
        except Exception as exc:
            logger.debug("prefetch failed: %s", exc)

    def _emit_symbol_rows(self, request: _CompletionRequest) -> None:
        """Emit instant buffer-name rows ahead of the semantic result.

        The symbol cache refreshes on every new buffer version (~1ms),
        so names being defined right now are included. Only plain naming
        contexts qualify — member scopes and preprocessor lines keep
        their dedicated engines. The full result replaces this batch
        through the normal latest-wins path.
        """
        try:
            from .context import classify

            context = request.context
            self._symbols.update(context.source_code or "")
            lines = (context.source_code.splitlines()
                     if context.source_code else [])
            row = lines[context.line - 1] if 0 <= context.line - 1 < len(
                lines) else ""
            kind, _ = classify(row, context.col - 1)
            if kind not in ("identifier", "call", "construction",
                            "template_args"):
                return
            rows = self._symbols.match(context.prefix or "")
            rows = list(rows) + self._sysindex_rows(request)
            if not rows:
                return
            if (self._shutting_down or self._current is not None
                    or request.request_id < self._owner._request_counter):
                return
            self._owner.completions_ready.emit(request.request_id, rows)
        except RuntimeError:
            pass
        except Exception as exc:
            logger.debug("symbol fast path failed: %s", exc)

    def _sysindex_rows(self, request: _CompletionRequest) -> list:
        """Return preloaded system-index rows for the request prefix.

        Served under workspace rows; the semantic result replaces the
        merged batch through the normal latest-wins path.

        Args:
            request: The completion request carrying file and prefix.

        Returns:
            System rows (possibly empty) — never raises.
        """
        try:
            from ..intellisense.index import get_cpp_indexer

            return get_cpp_indexer().search_sys(request.context.prefix or "")
        except Exception as exc:
            logger.debug("sysindex fast path failed: %s", exc)
            return []

    def _index_fallback(self, request: _CompletionRequest) -> list:
        """Search workspace and system indexes when the TU yields nothing.

        Args:
            request: The finished completion request.

        Returns:
            Index rows (possibly empty) — never raises.
        """
        try:
            from ..intellisense.index import search_for_file

            rows = search_for_file(
                request.context.file_path, request.context.prefix or ""
            )
            return list(rows) + self._sysindex_rows(request)
        except Exception as exc:
            logger.debug("index fallback failed: %s", exc)
            return []

    def _maybe_hint(self, request: _CompletionRequest, items: list) -> None:
        """Emit a missing-include hint when semantic completion is empty.

        Fires at most once per ``(file, headers)`` combination so typing
        does not spam notifications. Runs on the worker thread; delivery
        to the GUI thread happens through the ``completion_hint`` signal.

        Args:
            request: The finished completion request.
            items: Semantic items produced for it (possibly empty).
        """
        try:
            if request.warmup or items:
                return
            getter = getattr(self._engine, "missing_includes", None)
            if getter is None:
                return
            missing = getter(request.context) or []
            if not missing:
                return
            key = (request.context.file_path, tuple(missing))
            if key == self._last_hint_key:
                return
            self._last_hint_key = key
            shown = ", ".join(missing[:4])
            if len(missing) > 4:
                shown += f", +{len(missing) - 4} more"
            self._owner.completion_hint.emit(request.request_id, shown)
        except RuntimeError:
            pass  # owner deleted with its editor
        except Exception as exc:
            logger.debug("completion hint failed: %s", exc)

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
    completion_hint = pyqtSignal(int, str)

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
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(IDLE_PREQUERY_MS)
        self._idle_timer.timeout.connect(self._on_idle_fired)
        self._worker = _CppCompletionWorker(self, self._engine)
        destroyed = getattr(editor, "destroyed", None)
        if destroyed is not None:
            destroyed.connect(self._on_editor_destroyed)

    def set_compile_args(self, args: List[str]) -> None:
        """
        Replace include flags.
        """
        self._compile_args = list(args or [])

    def query_cost_ms(self) -> float:
        """Return the engine's smoothed parse+complete cost in milliseconds.

        Used by the cost-scaled debounce. Never raises.

        Returns:
            Smoothed cost (``0.0`` when unknown).
        """
        try:
            getter = getattr(self._engine, "query_cost_ms", None)
            if getter is None:
                return 0.0
            return float(getter() or 0.0)
        except Exception:
            return 0.0

    def current_flags(
        self,
        source: str,
        line: int,
        col: int,
        file_path: Optional[str] = None,
        prefix: str = "",
    ) -> tuple:
        """Return the TU flags the engine would use for this position.

        Pure computation (no parsing) so the controller can detect flag
        changes without submitting a query. Never raises.

        Args:
            source: Full buffer content.
            line: 0-indexed cursor line.
            col: 0-indexed cursor column.
            file_path: File being edited.
            prefix: Current completion prefix.

        Returns:
            Ordered flag tuple (possibly empty on any failure).
        """
        try:
            context = CppContext(
                source_code=source,
                line=line + 1,
                col=col + 1,
                file_path=file_path or self._file_path,
                compile_args=list(self._compile_args),
                prefix=prefix or "",
            )
            getter = getattr(self._engine, "flags_for", None)
            if getter is None:
                return ()
            return tuple(getter(context) or ())
        except Exception:
            return ()

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
        _profile.mark(self._editor, "queue")
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
            from editor.Ironica.debounce import adaptive_delay_for_cost

            self._timer.setInterval(
                adaptive_delay_for_cost(
                    COMPLETION_DEBOUNCE_MS, self._editor, self.query_cost_ms()
                )
            )
        except Exception:
            pass
        try:
            self._timer.start()
        except RuntimeError:
            self._dead = True
            return False
        try:
            self._idle_timer.start()
        except RuntimeError:
            pass
        return True

    def warmup(
        self,
        source: str,
        line: int,
        col: int,
        file_path: Optional[str] = None,
    ) -> None:
        """Prime engine caches off the typing path; results are discarded.

        Safe to call once per editor while idle: a real request always
        supersedes the queued warmup, and a running warmup costs no more
        than the cold parse the first keystroke would pay anyway.
        """
        if self._dead or not self._enabled or not source:
            return
        try:
            context = CppContext(
                source_code=source,
                line=line + 1,
                col=col + 1,
                file_path=file_path or self._file_path,
                compile_args=list(self._compile_args),
            )
            self._worker.process(self._request_counter, context, warmup=True)
        except Exception as exc:
            logger.debug("C++ completion warmup failed: %s", exc)

    def invalidate(self) -> None:
        """Retire in-flight and armed requests without emitting.

        Used when the user commits a completion: any background result
        still computing belongs to the pre-commit buffer and must never
        repaint the popup.
        """
        self._request_counter += 1
        self._pending = None
        try:
            self._timer.stop()
        except RuntimeError:
            self._dead = True
        try:
            self._idle_timer.stop()
        except RuntimeError:
            pass

    @pyqtSlot()
    def _on_debounce_fired(self) -> None:
        """
        Submit the pending context to the worker thread.
        """

        if not self._enabled or self._pending is None:
            return
        _profile.mark(self._editor, "debounce")
        try:
            self._worker.process(self._request_counter, self._pending)
        except Exception as exc:
            logger.warning("Failed to submit C++ completion: %s", exc)

    @pyqtSlot()
    def _on_idle_fired(self) -> None:
        """Speculatively warm caches at the idle caret; never presents.

        Fires after a typing pause. Skipped while the worker is busy or
        the caret sits outside a completable context — a real keystroke
        always supersedes the prefetch through latest-wins numbering.
        """
        if not self._enabled or self._dead:
            return
        if self._worker.is_busy():
            try:
                self._idle_timer.start()
            except RuntimeError:
                pass
            return
        try:
            from .context import classify

            source = self._editor.text()
            if not source:
                return
            line, col = self._editor.getCursorPosition()
            lines = source.splitlines()
            row = lines[line] if 0 <= line < len(lines) else ""
            kind, _ = classify(row, col)
            if kind in ("none", "comment", "preprocessor"):
                return
            match = re.search(r"([A-Za-z_]\w*)$", row[:col])
            context = CppContext(
                source_code=source,
                line=line + 1,
                col=col + 1,
                file_path=self._file_path,
                compile_args=list(self._compile_args),
                prefix=match.group(1) if match else "",
            )
            _profile.mark(self._editor, "prefetch")
            self._worker.process(self._request_counter, context, prefetch=True)
        except Exception as exc:
            logger.debug("C++ prefetch failed: %s", exc)

    @pyqtSlot()
    def _on_editor_destroyed(self) -> None:
        """
        Mark dead during QObject teardown so later request() no-ops.
        """

        try:
            self._timer.stop()
        except RuntimeError:
            pass
        try:
            self._idle_timer.stop()
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
        try:
            self._idle_timer.stop()
        except RuntimeError:
            pass
        self._worker.shutdown()
