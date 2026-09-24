"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Thread-safe background diagnostics and completions bridge for C/Clang support.

Coordinates asynchronous Clang evaluation tasks off the main thread while
safely rendering calculated visual overlays and completion popups back on
the primary window buffer.
"""

from __future__ import annotations
import logging
import threading
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

# Local Imports
from .clang_domain_models import CContext, CDiagnostic
from .clang_adapter import ClangAdapter

logger = logging.getLogger("DreamStudio.CDiagnostics.Worker")

DIAGNOSTIC_DEBOUNCE_MS: int = 500
COMPLETION_DEBOUNCE_MS: int = 30


@dataclass(frozen=True)
class _DiagnosticRequest:
    request_id: int
    context: CContext


class _CDiagnosticWorker(threading.Thread):
    """
    Runs background libclang diagnostics on a dedicated Python thread.
    """

    def __init__(self, owner: CDiagnosticManager, adapter: ClangAdapter) -> None:
        super().__init__(name="DreamStudio-CDiagnosticsWorker", daemon=True)
        self._owner = owner
        self._adapter = adapter
        self._wake = threading.Event()
        self._started_once = False
        self._current_request: Optional[_DiagnosticRequest] = None
        self._is_shutting_down = False

    def process(self, request_id: int, context: CContext) -> None:
        if self._is_shutting_down:
            return

        self._current_request = _DiagnosticRequest(
            request_id=request_id, context=context
        )
        self._wake.set()
        if not self._started_once:
            self._started_once = True
            self.start()

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
                diagnostics = self._adapter.get_diagnostics(request.context)
            except Exception as exc:
                logger.error("Clang diagnostics worker failed: %s", exc)
                diagnostics = []

            if not self._is_shutting_down and self._current_request is None:
                try:
                    self._owner._results_ready.emit(request.request_id, diagnostics)
                except RuntimeError:
                    pass

    def shutdown(self) -> None:
        self._is_shutting_down = True
        self._current_request = None
        self._wake.set()


class CDiagnosticManager(QObject):
    """
    Manages debouncing and life-cycle for C buffer diagnostics.
    """

    _results_ready = pyqtSignal(int, list)

    def __init__(
        self,
        editor,
        adapter: ClangAdapter,
        debounce_ms: int = DIAGNOSTIC_DEBOUNCE_MS,
        file_path: Optional[str] = None,
        compile_args: Optional[List[str]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        self._adapter = adapter
        self._file_path = file_path
        self._compile_args = compile_args or []
        self._owner_id = id(editor)
        self._enabled = True
        self._request_counter: int = 0

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._on_debounce_fired)

        self._worker = _CDiagnosticWorker(self, self._adapter)
        self._results_ready.connect(self._apply_results)

        self._editor.textChanged.connect(self._on_text_changed)
        destroyed = getattr(self._editor, "destroyed", None)
        if destroyed is not None:
            destroyed.connect(self.shutdown)

    def set_compile_args(self, args: List[str]) -> None:
        """
        Dynamically update include flags (e.g., when target build system changes).
        """
        self._compile_args = args

    @pyqtSlot()
    def _on_text_changed(self) -> None:
        self._request_counter += 1
        self._debounce_timer.start()

    @pyqtSlot()
    def _on_debounce_fired(self) -> None:
        if not self._enabled:
            return
        try:
            source = self._editor.text()
            context = CContext(
                source_code=source,
                line=1,
                col=1,
                file_path=self._file_path,
                compile_args=self._compile_args,
            )
            self._worker.process(self._request_counter, context)
        except Exception as exc:
            logger.debug("Failed to read editor text for C diagnostics: %s", exc)

    @pyqtSlot(int, list)
    def _apply_results(self, request_id: int, diagnostics: List[CDiagnostic]) -> None:
        if request_id < self._request_counter:
            return

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
            logger.debug("Failed to apply C diagnostics to UI: %s", exc)

    def shutdown(self) -> None:
        try:
            self._editor.textChanged.disconnect(self._on_text_changed)
        except (TypeError, RuntimeError):
            pass

        self._debounce_timer.stop()
        self._worker.shutdown()


@dataclass(frozen=True)
class _CompletionRequest:
    request_id: int
    context: CContext


class _CCompletionWorker(threading.Thread):
    """
    Runs background libclang completions on a dedicated thread.
    """

    def __init__(self, owner: CCompletionManager, adapter: ClangAdapter) -> None:
        super().__init__(name="DreamStudio-CCompletionWorker", daemon=True)
        self._owner = owner
        self._adapter = adapter
        self._wake = threading.Event()
        self._started_once = False
        self._current_request: Optional[_CompletionRequest] = None
        self._is_shutting_down = False

    def process(self, request_id: int, context: CContext) -> None:
        if self._is_shutting_down:
            return

        self._current_request = _CompletionRequest(
            request_id=request_id, context=context
        )
        self._wake.set()
        if not self._started_once:
            self._started_once = True
            self.start()

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
                completions = self._adapter.get_completions(request.context)
            except Exception as exc:
                logger.error("Clang completions worker failed: %s", exc)
                completions = []

            if not self._is_shutting_down and self._current_request is None:
                if request.request_id < self._owner._request_counter:
                    continue
                try:
                    self._owner.completions_ready.emit(request.request_id, completions)
                except RuntimeError:
                    pass

    def shutdown(self) -> None:
        self._is_shutting_down = True
        self._current_request = None
        self._wake.set()


class CCompletionManager(QObject):
    """
    Debounced background completion manager for C code buffers.
    """

    completions_ready = pyqtSignal(int, list)

    def __init__(
        self,
        editor,
        adapter: ClangAdapter,
        file_path: Optional[str] = None,
        compile_args: Optional[List[str]] = None,
        debounce_ms: int = COMPLETION_DEBOUNCE_MS,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        self._adapter = adapter
        self._file_path = file_path
        self._compile_args = compile_args or []
        self._enabled = True
        self._request_counter: int = 0
        self._pending_context: Optional[CContext] = None

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._on_debounce_fired)

        self._worker = _CCompletionWorker(self, self._adapter)

    def request(
        self, source: str, line: int, col: int, file_path: Optional[str] = None
    ) -> None:
        self._request_counter += 1

        self._pending_context = CContext(
            source_code=source,
            line=line + 1,
            col=col + 1,
            file_path=file_path or self._file_path,
            compile_args=self._compile_args,
        )
        self._debounce_timer.start()

    @pyqtSlot()
    def _on_debounce_fired(self) -> None:
        if not self._enabled or not self._pending_context:
            return
        try:
            self._worker.process(self._request_counter, self._pending_context)
        except Exception as exc:
            logger.debug("Failed to submit C completion request: %s", exc)

    def shutdown(self) -> None:
        self._debounce_timer.stop()
        self._worker.shutdown()
