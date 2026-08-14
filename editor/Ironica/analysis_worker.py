# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Thread-safe whole-document analysis bridge for DreamStudio.

Computes semantic highlights + fold regions off the main thread while
rendering the overlays back on the primary window buffer, so typing in
large files never blocks the UI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import RLock
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

logger = logging.getLogger("DreamStudio.Analysis.Worker")

# Language providers hold mutable caches and are not guaranteed
# thread-safe; serialize every provider call through this lock.
_PROVIDER_LOCK = RLock()


@dataclass(frozen=True)
class _AnalysisRequest:
    """Immutable work item handed to the worker thread."""

    request_id: int
    source: str
    provider: object


class _AnalysisWorker(QThread):
    """Runs provider analysis for the latest buffer (latest-wins)."""

    _results_ready = pyqtSignal(int, object, object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._current_request: Optional[_AnalysisRequest] = None
        self._is_shutting_down = False

    @pyqtSlot(int, str, object)
    def process(self, request_id: int, source: str, provider: object) -> None:
        """Enqueue the newest request, replacing any pending one.

        Args:
            request_id: Monotonic id used to drop stale results.
            source: The full editor buffer content to analyse.
            provider: The language provider to run.
        """
        if self._is_shutting_down:
            return
        self._current_request = _AnalysisRequest(
            request_id=request_id, source=source, provider=provider
        )
        if not self.isRunning():
            self.start()

    @staticmethod
    def _analyze(provider: object, source: str):
        """Compute semantic highlights + fold regions for *source*.

        Args:
            provider: A ``BaseLanguageProvider`` instance.
            source: The full editor buffer content.

        Returns:
            A ``(highlights, fold_regions)`` tuple; either entry is
            ``None`` when the provider does not support that feature.
        """
        highlights = None
        fold_regions = None
        try:
            get_semantic = getattr(provider, "get_semantic_highlights", None)
            if callable(get_semantic):
                highlights = get_semantic(source)
            if getattr(provider, "has_folding", lambda: False)():
                fold_regions = provider.get_fold_regions(source)
        except Exception as exc:
            logger.error("Whole-document analysis failed: %s", exc)
            return None, None
        return highlights, fold_regions

    def run(self) -> None:
        while not self._is_shutting_down:
            request = self._current_request
            if request is None:
                break

            self._current_request = None

            with _PROVIDER_LOCK:
                highlights, fold_regions = self._analyze(
                    request.provider, request.source
                )

            # A newer request may have arrived while we worked; only the
            # newest buffer's result is worth shipping back.
            if not self._is_shutting_down and self._current_request is None:
                self._results_ready.emit(
                    request.request_id, highlights, fold_regions
                )

    def shutdown(self) -> None:
        """Stop the worker and join the underlying thread."""
        self._is_shutting_down = True
        self._current_request = None
        if self.isRunning():
            self.quit()
            self.wait(1000)
        if self.isRunning():
            self.terminate()
            self.wait(500)


class AnalysisManager(QObject):
    """Latest-wins coordinator between a ``CodeEditor`` and the worker."""

    def __init__(
        self, editor, parent: Optional[QObject] = None
    ) -> None:
        """Create the manager, spawning a worker owned by this object.

        Args:
            editor: The ``CodeEditor`` whose text is analysed.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._editor = editor
        self._request_counter: int = 0
        self._worker = _AnalysisWorker(self)
        self._worker._results_ready.connect(self._apply_results)

    @pyqtSlot(str)
    def request_analysis(self, source: str) -> None:
        """Hand the latest buffer to the worker thread.

        Args:
            source: The full editor buffer content.
        """
        if not source:
            return
        self._request_counter += 1
        provider = getattr(self._editor, "current_provider", None)
        self._worker.process(self._request_counter, source, provider)

    @pyqtSlot(int, object, object)
    def _apply_results(
        self, request_id: int, highlights, fold_regions
    ) -> None:
        """Render worker results back on the UI thread.

        Results for superseded requests are dropped so stale overlays
        never repaint a newer buffer.

        Args:
            request_id: Id of the request that produced these results.
            highlights: Semantic overlay list, or ``None``.
            fold_regions: Fold-region list, or ``None``.
        """
        if request_id < self._request_counter:
            return  # Drop out-of-order evaluations

        editor = self._editor
        try:
            if highlights is not None:
                editor._apply_semantic_overlays(highlights)
            if fold_regions is not None:
                editor._apply_fold_regions(fold_regions)
        except Exception as exc:
            logger.debug("Failed to apply analysis results: %s", exc)
        finally:
            try:
                editor._on_analysis_finished()
            except RuntimeError:
                pass

    def shutdown(self) -> None:
        """Shut the worker down before the editor is destroyed."""
        try:
            self._worker.shutdown()
        except Exception as exc:
            logger.debug("Analysis worker shutdown failed: %s", exc)
