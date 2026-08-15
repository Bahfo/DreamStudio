# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Thread-safe background diagnostics bridge for DreamStudio.

Coordinates async evaluation tasks off the main thread while safely
rendering calculated visual overlays back on the primary window buffer.

Jedi analysis is CPU-bound (GIL), so diagnostics are delegated to a
dedicated analysis-server subprocess; the worker thread only performs the
blocking request/response round-trip.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from editor.Ironica.analysis_bridge import AnalysisProcess, AnalysisProcessError
from editor.Ironica.plugins.python.detect_problems import Diagnostic, detect_problems

logger = logging.getLogger("DreamStudio.Diagnostics.Worker")

DEBOUNCE_MS: int = 500


@dataclass(frozen=True)
class _AnalysisRequest:
    request_id: int
    source: str
    file_path: Optional[str]


class _DiagnosticWorker(threading.Thread):
    """Runs background diagnostics on a plain Python thread.

    Like the analysis worker, this intentionally avoids ``QThread`` so an
    editor collected mid-evaluation can never abort Qt; the owner's signal
    is emitted from the worker thread (safe, queued to the owner's thread).
    """

    def __init__(self, owner: "DiagnosticManager") -> None:
        super().__init__(name="DreamStudio-DiagnosticsWorker", daemon=True)
        self._owner = owner
        self._wake = threading.Event()
        self._started_once = False
        self._current_request: Optional[_AnalysisRequest] = None
        self._is_shutting_down = False
        self._process = AnalysisProcess()

    def process(self, request_id: int, source: str, file_path: Optional[str]) -> None:
        if self._is_shutting_down:
            return

        self._current_request = _AnalysisRequest(
            request_id=request_id, source=source, file_path=file_path
        )
        self._wake.set()
        if not self._started_once:
            self._started_once = True
            self.start()

    def _remote_diagnostics(self, request: _AnalysisRequest) -> List[Diagnostic]:
        """Ask the analysis subprocess to run jedi over the buffer."""
        response = self._process.request(
            ("diagnostics", request.request_id, request.source, request.file_path)
        )
        if not isinstance(response, (tuple, list)) or not response:
            raise AnalysisProcessError(f"malformed server response: {response!r}")
        if response[0] != "diagnostics":
            raise AnalysisProcessError(f"server error: {response}")
        return response[2]

    def _fallback_diagnostics(
        self, request: _AnalysisRequest
    ) -> List[Diagnostic]:
        """Graceful degradation: run jedi in-process when the server is down."""
        try:
            return detect_problems(request.source, request.file_path)
        except Exception as exc:
            logger.error("In-process diagnostics failed: %s", exc)
            return []

    def run(self) -> None:
        while not self._is_shutting_down:
            self._wake.wait(timeout=0.2)
            self._wake.clear()

            request = self._current_request
            if request is None:
                continue
            self._current_request = None

            if self._is_shutting_down:
                continue

            try:
                diagnostics = self._remote_diagnostics(request)
            except Exception as exc:
                logger.error("Diagnostics subprocess failed: %s", exc)
                if self._is_shutting_down:
                    continue
                diagnostics = self._fallback_diagnostics(request)

            if not self._is_shutting_down and self._current_request is None:
                try:
                    self._owner._results_ready.emit(
                        request.request_id, diagnostics
                    )
                except RuntimeError:
                    pass  # Owner torn down while we were computing

    def shutdown(self) -> None:
        self._is_shutting_down = True
        self._current_request = None
        self._wake.set()
        try:
            self._process.shutdown()
        except Exception as exc:
            logger.debug("Diagnostics subprocess shutdown failed: %s", exc)
        if self._started_once and self.is_alive():
            self.join(timeout=2.0)


class DiagnosticManager(QObject):
    _results_ready = pyqtSignal(int, list)

    def __init__(
        self,
        editor,
        debounce_ms: int = DEBOUNCE_MS,
        file_path: Optional[str] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        self._file_path = file_path
        self._request_counter: int = 0

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._on_debounce_fired)

        self._worker = _DiagnosticWorker(self)
        self._results_ready.connect(self._apply_results)

        self._editor.textChanged.connect(self._on_text_changed)
        destroyed = getattr(self._editor, "destroyed", None)
        if destroyed is not None:
            destroyed.connect(self.shutdown)

    @pyqtSlot()
    def _on_text_changed(self) -> None:
        self._request_counter += 1
        self._debounce_timer.start()

    @pyqtSlot()
    def _on_debounce_fired(self) -> None:
        try:
            source = self._editor.text()
            self._worker.process(self._request_counter, source, self._file_path)
        except Exception as exc:
            logger.debug("Failed to read editor text: %s", exc)

    @pyqtSlot(int, list)
    def _apply_results(self, request_id: int, diagnostics: List[Diagnostic]) -> None:
        if request_id < self._request_counter:
            return  # Drop out-of-order evaluations

        try:
            self._editor.clear_diagnostic_underlines()
            for diag in diagnostics:
                self._editor.add_diagnostic_underline(
                    line=diag.line - 1,
                    start_col=diag.start_col,
                    end_col=diag.end_col,
                    color_hex=diag.color,
                )
        except Exception as exc:
            logger.debug("Failed to apply diagnostics to UI: %s", exc)

    def set_file_path(self, path: Optional[str]) -> None:
        self._file_path = path

    def trigger_analysis(self) -> None:
        self._on_debounce_fired()

    def shutdown(self) -> None:
        try:
            self._editor.textChanged.disconnect(self._on_text_changed)
        except (TypeError, RuntimeError):
            pass

        self._debounce_timer.stop()
        self._worker.shutdown()
