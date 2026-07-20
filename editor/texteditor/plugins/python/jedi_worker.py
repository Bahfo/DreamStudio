# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Thread-safe background diagnostics bridge for DreamStudio.

Coordinates async evaluation tasks off the main thread while safely
rendering calculated visual overlays back on the primary window buffer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

from editor.texteditor.plugins.python.detect_problems import Diagnostic, detect_problems

logger = logging.getLogger("DreamStudio.Diagnostics.Worker")

DEBOUNCE_MS: int = 500


@dataclass(frozen=True)
class _AnalysisRequest:
    request_id: int
    source: str
    file_path: Optional[str]


class _DiagnosticWorker(QThread):
    _results_ready = pyqtSignal(int, list)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._current_request: Optional[_AnalysisRequest] = None
        self._is_shutting_down = False

    @pyqtSlot(int, str, object)
    def process(self, request_id: int, source: str, file_path: Optional[str]) -> None:
        if self._is_shutting_down:
            return

        self._current_request = _AnalysisRequest(
            request_id=request_id, source=source, file_path=file_path
        )
        if not self.isRunning():
            self.start()

    def run(self) -> None:
        while not self._is_shutting_down:
            request = self._current_request
            if request is None:
                break

            self._current_request = None

            try:
                diagnostics = detect_problems(
                    source=request.source, file_path=request.file_path
                )
            except Exception as exc:
                logger.error("Diagnostics analysis failed: %s", exc)
                diagnostics = []

            if not self._is_shutting_down and self._current_request is None:
                self._results_ready.emit(request.request_id, diagnostics)

    def shutdown(self) -> None:
        self._is_shutting_down = True
        self._current_request = None
        if self.isRunning():
            self.quit()
            self.wait(1000)
        if self.isRunning():
            self.terminate()
            self.wait(500)


class DiagnosticManager(QObject):
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
        self._worker._results_ready.connect(self._apply_results)

        self._editor.textChanged.connect(self._on_text_changed)

    @pyqtSlot()
    def _on_text_changed(self) -> None:
        self._debounce_timer.start()

    @pyqtSlot()
    def _on_debounce_fired(self) -> None:
        self._request_counter += 1
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
