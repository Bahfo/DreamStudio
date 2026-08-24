# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Thread-safe background diagnostics and completions bridge for DreamStudio.

Coordinates async evaluation tasks off the main thread while safely
rendering calculated visual overlays back on the primary window buffer.

Jedi analysis is CPU-bound (GIL), so diagnostics and completions are
delegated to a dedicated analysis-server subprocess; the worker thread
only performs the blocking request/response round-trip.
"""

from __future__ import annotations

from editor import *

from editor.Ironica.analysis_bridge import AnalysisProcess, AnalysisProcessError
from editor.Ironica.plugins.python.detect_problems import Diagnostic, detect_problems
from editor.Ironica.process_manager import process_manager

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

    def _remote_diagnostics(self, request: _AnalysisRequest):
        """Ask the shared analysis subprocess to run jedi over the buffer.

        Returns the diagnostics list, or ``None`` when the request was
        dropped because this owner is no longer the focused tab.
        """
        response = process_manager.request(
            self._owner.owner_id,
            ("diagnostics", request.request_id, request.source, request.file_path),
        )
        if response is None:
            return None
        if not isinstance(response, (tuple, list)) or not response:
            raise AnalysisProcessError(f"malformed server response: {response!r}")
        if response[0] != "diagnostics":
            raise AnalysisProcessError(f"server error: {response}")
        return response[2]

    def _fallback_diagnostics(self, request: _AnalysisRequest) -> List[Diagnostic]:
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
                if diagnostics is None:
                    continue  # dropped — owner is no longer active
            except Exception as exc:
                if self._is_shutting_down or not process_manager.is_active(
                    self._owner.owner_id
                ):
                    # Intentional teardown / lost focus — not a bug.
                    logger.debug("Diagnostics subprocess failed: %s", exc)
                    continue
                logger.error("Diagnostics subprocess failed: %s", exc)
                diagnostics = self._fallback_diagnostics(request)

            if not self._is_shutting_down and self._current_request is None:
                try:
                    self._owner._results_ready.emit(request.request_id, diagnostics)
                except RuntimeError:
                    pass  # Owner torn down while we were computing

    def shutdown(self) -> None:
        """Stop the worker.

        The shared process is deliberately left untouched: it is owned by
        the process manager and stays warm for other tabs.  The worker is
        a daemon thread, so it simply exits once its current round-trip
        finishes — never blocking the caller on a busy child.
        """
        self._is_shutting_down = True
        self._current_request = None
        self._wake.set()


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
        self._owner_id = id(editor)
        self._enabled = True
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

    @property
    def owner_id(self) -> int:
        return self._owner_id

    def set_enabled(self, active: bool) -> None:
        """Gate submission while this editor is not the focused tab."""
        self._enabled = active
        if not active:
            self._debounce_timer.stop()
            self._request_counter += 1  # invalidate any pending evaluation

    def invalidate(self) -> None:
        self._request_counter += 1

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
        process_manager.release(self._owner_id)


# =====================================================================
# Completion Worker
# =====================================================================

# NOTE: The completion controller already debounces keystrokes (40 ms)
# before reaching this manager, so only a token coalescing delay is kept
# here to merge bursts arriving from multiple editors.
COMPLETION_DEBOUNCE_MS: int = 30
_MAX_COMPLETION_ITEMS: int = 50


@dataclass(frozen=True)
class _CompletionRequest:
    request_id: int
    source: str
    line: int
    col: int
    file_path: Optional[str]


class _CompletionWorker(threading.Thread):
    """Runs background Jedi completions on a plain Python thread.

    Uses a dedicated ``AnalysisProcess`` subprocess so completions never
    queue behind diagnostics or semantic-analysis requests.  Like the
    diagnostics worker this avoids QThread so an editor collected
    mid-evaluation can never abort Qt.
    """

    def __init__(self, owner: "CompletionManager") -> None:
        super().__init__(name="DreamStudio-CompletionWorker", daemon=True)
        self._owner = owner
        self._wake = threading.Event()
        self._started_once = False
        self._current_request: Optional[_CompletionRequest] = None
        self._is_shutting_down = False

    def process(
        self,
        request_id: int,
        source: str,
        line: int,
        col: int,
        file_path: Optional[str],
    ) -> None:
        if self._is_shutting_down:
            return

        self._current_request = _CompletionRequest(
            request_id=request_id,
            source=source,
            line=line,
            col=col,
            file_path=file_path,
        )
        self._wake.set()
        if not self._started_once:
            self._started_once = True
            self.start()

    def _remote_completions(self, request: _CompletionRequest) -> Optional[list]:
        """Ask the dedicated completion subprocess for Jedi completions.

        Returns the raw completion dicts, or ``None`` if the request was
        superseded by a newer one.
        """
        process = self._owner._process
        response = process.request(
            (
                "completions",
                request.request_id,
                request.source,
                request.line,
                request.col,
                request.file_path,
            ),
        )
        if response is None:
            return None
        if not isinstance(response, (tuple, list)) or not response:
            raise AnalysisProcessError(f"malformed server response: {response!r}")
        if response[0] != "completions":
            raise AnalysisProcessError(f"server error: {response}")
        return response[2]

    def _fallback_completions(self, request: _CompletionRequest) -> list:
        """Graceful degradation: run jedi in-process when the server is down."""
        try:
            import jedi

            lines = request.source.split("\n")
            jedi_line = max(1, min(request.line + 1, len(lines)))
            jedi_col = request.col
            if 0 < jedi_line <= len(lines):
                line_len = len(lines[jedi_line - 1])
                jedi_col = min(jedi_col, max(0, line_len - 1))

            script = jedi.Script(code=request.source, path=request.file_path)
            comps = script.complete(line=jedi_line, column=jedi_col)
            results = []
            for c in comps:
                sigs = [sig.to_string() for sig in c.get_signatures()]
                results.append(
                    {
                        "text": c.name,
                        # NOTE: c.complete is a suffix; full word required.
                        "insert_text": c.name,
                        "kind": c.type if c.type else "",
                        "signature": ", ".join(sigs),
                    }
                )
                if len(results) >= _MAX_COMPLETION_ITEMS:
                    break
            return results
        except Exception as exc:
            logger.error("In-process completions failed: %s", exc)
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
                completions = self._remote_completions(request)
                if completions is None:
                    continue  # superseded by a newer request
            except Exception as exc:
                logger.error("Completions subprocess failed: %s", exc)
                completions = self._fallback_completions(request)

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


class CompletionManager(QObject):
    """Debounced background completion manager.

    Owns a dedicated ``AnalysisProcess`` subprocess so completions never
    block behind diagnostics or semantic-analysis requests.  The process
    is lazy — spawned on the first completion request — and torn down
    with the manager.
    """

    completions_ready = pyqtSignal(int, list)

    def __init__(
        self,
        editor,
        file_path: Optional[str] = None,
        debounce_ms: int = COMPLETION_DEBOUNCE_MS,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        self._file_path = file_path
        self._owner_id = id(editor)
        self._enabled = True
        self._request_counter: int = 0
        self._pending_source: str = ""
        self._pending_line: int = 0
        self._pending_col: int = 0

        self._process = AnalysisProcess()

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._on_debounce_fired)

        self._worker = _CompletionWorker(self)

    @property
    def owner_id(self) -> int:
        return self._owner_id

    def set_enabled(self, active: bool) -> None:
        self._enabled = active
        if not active:
            self._debounce_timer.stop()
            self._request_counter += 1

    def set_file_path(self, path: Optional[str]) -> None:
        self._file_path = path

    def request(
        self, source: str, line: int, col: int, file_path: Optional[str]
    ) -> None:
        """Debounce and submit a completion request to the background worker."""
        self._request_counter += 1
        self._pending_source = source
        self._pending_line = line
        self._pending_col = col
        self._debounce_timer.start()

    @pyqtSlot()
    def _on_debounce_fired(self) -> None:
        if not self._enabled:
            return
        try:
            self._worker.process(
                self._request_counter,
                self._pending_source,
                self._pending_line,
                self._pending_col,
                self._file_path,
            )
        except Exception as exc:
            logger.debug("Failed to submit completion request: %s", exc)

    def shutdown(self) -> None:
        self._debounce_timer.stop()
        self._worker.shutdown()
        try:
            self._process.shutdown()
        except Exception as exc:
            logger.debug("Completion process shutdown failed: %s", exc)
