"""Thread-safe background diagnostics and completions bridge for DreamStudio."""

from __future__ import annotations

import dataclasses
import logging
import threading
from typing import List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from editor.Ironica import completion_profile as _profile
from editor.Ironica.analysis_bridge import AnalysisProcess, AnalysisProcessError
from editor.Ironica.process_manager import process_manager

logger = logging.getLogger("DreamStudio.Diagnostics.Worker")

DEBOUNCE_MS: int = 500

_MAX_DIAGNOSTICS: int = 200
_SYNTAX_COLOR: str = "#F14C4C"


def _merge_spans(diagnostics: List[dict]) -> List[dict]:
    """Merge overlapping/adjacent spans that share a line."""
    by_line: dict = {}
    for entry in diagnostics:
        by_line.setdefault(entry["line"], []).append(entry)
    merged: List[dict] = []
    for line in sorted(by_line):
        group = sorted(by_line[line], key=lambda e: e["start_col"])
        current = None
        for entry in group:
            if current is None:
                current = dict(entry)
                continue
            if entry["start_col"] <= current["end_col"]:
                current["end_col"] = max(current["end_col"], entry["end_col"])
                continue
            merged.append(current)
            current = dict(entry)
        if current is not None:
            merged.append(current)
    return merged


def _diag_field(diag, name: str, default):
    """Read *name* from a diagnostic whether it is a dict or an object."""
    if isinstance(diag, dict):
        return diag.get(name, default)
    return getattr(diag, name, default)


def _syntax_diagnostics(source: str) -> List[dict]:
    """Return syntax diagnostics for *source* as plain wire dicts."""
    try:
        import parso

        message = "Syntax error"
        try:
            compile(source, "<buffer>", "exec")
        except SyntaxError as exc:
            if exc.msg:
                message = exc.msg
        except Exception:
            pass

        lines = source.split("\n")
        module = parso.parse(source, error_recovery=True)
        found: List[dict] = []
        stack = [module]
        while stack and len(found) < _MAX_DIAGNOSTICS:
            node = stack.pop()
            children = getattr(node, "children", None) or ()
            for child in children:
                if getattr(child, "type", "") in ("error_node", "error_leaf"):
                    start_line, start_col = child.start_pos
                    end_line, end_col = child.end_pos
                    for row in range(start_line, end_line + 1):
                        if len(found) >= _MAX_DIAGNOSTICS:
                            break
                        text = lines[row - 1] if 0 < row <= len(lines) else ""
                        first_col = start_col if row == start_line else 0
                        last_col = end_col if row == end_line else len(text)
                        found.append(
                            {
                                "line": row,
                                "start_col": first_col,
                                "end_line": row,
                                "end_col": last_col,
                                "color": _SYNTAX_COLOR,
                                "message": message,
                            }
                        )
                stack.append(child)
        return _merge_spans(found)
    except Exception as exc:
        logger.warning("In-process diagnostics failed: %s", exc)
        return []


@dataclasses.dataclass(frozen=True)
class _AnalysisRequest:
    """Immutable work item handed to the diagnostics worker thread."""
    request_id: int
    source: str
    file_path: Optional[str]


class _DiagnosticWorker(threading.Thread):
    """Runs background diagnostics on a plain Python thread."""

    def __init__(self, owner: "DiagnosticManager") -> None:
        super().__init__(name="DreamStudio-DiagnosticsWorker", daemon=True)
        self._owner = owner
        self._wake = threading.Event()
        self._started_once = False
        self._current_request: Optional[_AnalysisRequest] = None
        self._is_shutting_down = False

    def process(self, request_id: int, source: str, file_path: Optional[str]) -> None:
        """Queue *request*, waking the thread (replacing any pending older item)."""
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
        """Ask the shared analysis subprocess to run jedi over the buffer."""
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

    def _fallback_diagnostics(self, request: _AnalysisRequest) -> List[dict]:
        """Graceful degradation:"""
        return _syntax_diagnostics(request.source)

    def run(self) -> None:
        """Consume the newest request and emit results unless superseded."""
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
                    continue
            except Exception as exc:
                if self._is_shutting_down or not process_manager.is_active(
                    self._owner.owner_id
                ):
                    logger.debug("Diagnostics subprocess failed: %s", exc)
                    continue
                logger.error("Diagnostics subprocess failed: %s", exc)
                diagnostics = self._fallback_diagnostics(request)

            if not self._is_shutting_down and self._current_request is None:
                try:
                    self._owner._results_ready.emit(request.request_id, diagnostics)
                except RuntimeError:
                    pass

    def shutdown(self) -> None:
        """Stop the worker."""
        self._is_shutting_down = True
        self._current_request = None
        self._wake.set()


class DiagnosticManager(QObject):
    """Debounced diagnostics bridge for one editor."""
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
        self._has_painted = False

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
        """Return the id used to address the shared analysis subprocess."""
        return self._owner_id

    def set_enabled(self, active: bool) -> None:
        """Gate submission while this editor is not the focused tab."""
        self._enabled = active
        if not active:
            try:
                self._debounce_timer.stop()
            except RuntimeError:
                pass
            self._request_counter += 1

    def invalidate(self) -> None:
        """Increment the request counter so any pending evaluation is dropped."""
        self._request_counter += 1

    @pyqtSlot()
    def _on_text_changed(self) -> None:
        """Arm the debounce timer on every buffer edit."""
        self._request_counter += 1
        try:
            from editor.Ironica.debounce import adaptive_delay_for_editor

            self._debounce_timer.setInterval(
                adaptive_delay_for_editor(DEBOUNCE_MS, self._editor)
            )
            self._debounce_timer.start()
        except RuntimeError:
            pass
        except Exception:
            try:
                self._debounce_timer.start()
            except RuntimeError:
                pass

    @pyqtSlot()
    def _on_debounce_fired(self) -> None:
        """Submit the current buffer to the worker once debounced."""
        if not self._enabled:
            return
        _profile.mark(self._editor, "diag-fire")
        widget = getattr(self._editor, "_autocompletion_widget", None)
        if getattr(widget, "_request_pending", False):
            try:
                self._debounce_timer.start()
            except RuntimeError:
                pass
            return
        try:
            source = self._editor.text()
            self._worker.process(self._request_counter, source, self._file_path)
        except Exception as exc:
            logger.debug("Failed to read editor text: %s", exc)

    @staticmethod
    def _batch_ranges(diagnostics) -> list:
        """Convert diagnostics to editor ``set_diagnostic_ranges`` tuples."""
        ranges = []
        for diag in diagnostics or []:
            line = _diag_field(diag, "line", 1)
            start_col = _diag_field(diag, "start_col", 0)
            end_col = _diag_field(diag, "end_col", 0)
            color = _diag_field(diag, "color", _SYNTAX_COLOR)
            try:
                ranges.append(
                    (int(line) - 1, int(start_col), int(line) - 1,
                     int(end_col), str(color))
                )
            except (TypeError, ValueError):
                continue
        return ranges

    @pyqtSlot(int, list)
    def _apply_results(self, request_id: int, diagnostics: List[dict]) -> None:
        """Paint worker diagnostics onto the editor on the UI thread."""
        if request_id < self._request_counter:
            return

        try:
            setter = getattr(self._editor, "set_diagnostic_ranges", None)
            if setter is None:
                ranges = self._batch_ranges(diagnostics)
                self._editor.clear_diagnostic_underlines()
                for start_line, start_col, end_line, end_col, color in ranges:
                    self._editor.add_diagnostic_underline(
                        line=start_line,
                        start_col=start_col,
                        end_col=end_col,
                        color_hex=color,
                    )
                self._has_painted = bool(ranges)
                return
            ranges = self._batch_ranges(diagnostics)
            if not ranges and not self._has_painted:
                return
            self._has_painted = bool(ranges)
            setter(ranges)
        except Exception as exc:
            logger.debug("Failed to apply diagnostics to UI: %s", exc)

    def set_file_path(self, path: Optional[str]) -> None:
        """Repoint diagnostics at a new path (save-as, rename)."""
        self._file_path = path

    def trigger_analysis(self) -> None:
        """Force a diagnostics pass immediately, bypassing the debounce."""
        self._on_debounce_fired()

    def shutdown(self) -> None:
        """Disconnect the editor, stop the timer and release the subprocess."""
        try:
            self._editor.textChanged.disconnect(self._on_text_changed)
        except (TypeError, RuntimeError):
            pass

        try:
            self._debounce_timer.stop()
        except RuntimeError:
            pass
        self._worker.shutdown()
        process_manager.release(self._owner_id)


# NOTE: The completion controller already debounces keystrokes (40 ms)
COMPLETION_DEBOUNCE_MS: int = 30
_MAX_COMPLETION_ITEMS: int = 50


@dataclasses.dataclass(frozen=True)
class _CompletionRequest:
    """Immutable work item handed to the completion worker thread."""
    request_id: int
    source: str
    line: int
    col: int
    file_path: Optional[str]
    warmup: bool = False


class _CompletionWorker(threading.Thread):
    """Runs background Jedi completions on a plain Python thread."""

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
        warmup: bool = False,
    ) -> None:
        """Queue *request*, waking the thread (replacing any pending older item)."""
        if self._is_shutting_down:
            return

        self._current_request = _CompletionRequest(
            request_id=request_id,
            source=source,
            line=line,
            col=col,
            file_path=file_path,
            warmup=warmup,
        )
        self._wake.set()
        if not self._started_once:
            self._started_once = True
            self.start()

    def _remote_completions(self, request: _CompletionRequest) -> Optional[list]:
        """Ask the dedicated completion subprocess for Jedi completions."""
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
        """Graceful degradation:"""
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
        """Consume the newest request and emit results unless superseded."""
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
                _profile.mark(self._owner._editor, "engine-start")
                completions = self._remote_completions(request)
                _profile.mark(self._owner._editor, "engine-done")
                if completions is None:
                    continue
            except Exception as exc:
                logger.error("Completions subprocess failed: %s", exc)
                completions = self._fallback_completions(request)

            if not self._is_shutting_down and self._current_request is None:
                if request.request_id < self._owner._request_counter:
                    continue
                if request.warmup:
                    continue
                try:
                    _profile.mark(self._owner._editor, "emit")
                    self._owner.completions_ready.emit(request.request_id, completions)
                except RuntimeError:
                    pass

    def shutdown(self) -> None:
        """Disconnect the editor, stop the timer and release the subprocess."""
        self._is_shutting_down = True
        self._current_request = None
        self._wake.set()


class CompletionManager(QObject):
    """Debounced background completion manager."""

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
        self._dead = False
        self._request_counter: int = 0
        self._pending_source: str = ""
        self._pending_line: int = 0
        self._pending_col: int = 0
        self._pending_file_path: Optional[str] = None

        self._process = AnalysisProcess()

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(debounce_ms)
        self._debounce_timer.timeout.connect(self._on_debounce_fired)

        self._worker = _CompletionWorker(self)

        destroyed = getattr(editor, "destroyed", None)
        if destroyed is not None:
            destroyed.connect(self._on_editor_destroyed)

    @property
    def owner_id(self) -> int:
        """Return the id used to address the shared analysis subprocess."""
        return self._owner_id

    @pyqtSlot()
    def _on_editor_destroyed(self) -> None:
        """Mark this manager dead once its editor's Qt object is gone."""
        self._stop_timer()
        self._dead = True
        self.shutdown()

    def set_enabled(self, active: bool) -> None:
        """Gate submission while this editor is not the focused tab."""
        self._enabled = active
        if not active:
            self._stop_timer()
            self._request_counter += 1

    def set_file_path(self, path: Optional[str]) -> None:
        """Repoint diagnostics at a new path (save-as, rename)."""
        self._file_path = path

    def invalidate(self) -> None:
        """Retire in-flight and armed requests without emitting."""
        self._request_counter += 1
        self._pending_source = ""
        self._pending_file_path = None
        self._stop_timer()

    def _stop_timer(self) -> None:
        """Stop the debounce timer, tolerating an already-deleted C++ side."""
        if self._dead:
            return
        try:
            self._debounce_timer.stop()
        except RuntimeError:
            self._dead = True

    def request(
        self,
        source: str,
        line: int,
        col: int,
        file_path: Optional[str],
        prefix: str = "",
    ) -> bool:
        """Debounce and submit a completion request to the background worker."""
        if self._dead:
            return False
        _profile.mark(self._editor, "queue")
        self._request_counter += 1
        self._pending_source = source
        self._pending_line = line
        self._pending_col = col
        self._pending_file_path = file_path or self._file_path
        try:
            from editor.Ironica.debounce import adaptive_delay_for_editor

            self._debounce_timer.setInterval(
                adaptive_delay_for_editor(COMPLETION_DEBOUNCE_MS, self._editor)
            )
        except Exception:
            pass
        try:
            self._debounce_timer.start()
        except RuntimeError:
            self._dead = True
            return False
        return True

    def warmup(
        self,
        source: str,
        line: int,
        col: int,
        file_path: Optional[str] = None,
    ) -> None:
        """Prime engine caches off the typing path; results are discarded."""
        if self._dead or not self._enabled or not source:
            return
        try:
            self._worker.process(
                self._request_counter, source, line, col,
                file_path or self._file_path, warmup=True,
            )
        except Exception as exc:
            logger.debug("Completion warmup failed: %s", exc)

    @pyqtSlot()
    def _on_debounce_fired(self) -> None:
        """Submit the current buffer to the worker once debounced."""
        if not self._enabled:
            return
        _profile.mark(self._editor, "debounce")
        try:
            self._worker.process(
                self._request_counter,
                self._pending_source,
                self._pending_line,
                self._pending_col,
                self._pending_file_path or self._file_path,
            )
        except Exception as exc:
            logger.debug("Failed to submit completion request: %s", exc)

    def shutdown(self) -> None:
        """Disconnect the editor, stop the timer and release the subprocess."""
        self._enabled = False
        self._stop_timer()
        self._worker.shutdown()
        try:
            self._process.shutdown()
        except Exception as exc:
            logger.debug("Completion process shutdown failed: %s", exc)
