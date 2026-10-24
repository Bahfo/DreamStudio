"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Async navigation manager for C++ go-to actions; runs navigation
on a worker thread with latest-wins request IDs so the GUI thread
never blocks.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ..models import CppContext
from .engine import NavigationEngine

if TYPE_CHECKING:
    from editor.Ironica.code_editor import CodeEditor

    from ..provider import CppProvider

logger = logging.getLogger("DreamStudio.Cpp.NavigationManager")


@dataclass(frozen=True)
class _NavigationRequest:
    """Internal request payload for the worker thread."""

    request_id: int
    action: str
    text: str
    line: int
    col: int
    file_path: str | None


class _NavigationWorker(QObject):
    """
    Worker object that runs navigation queries on a dedicated thread.

    It receives requests via `process_request` (called from the GUI thread),
    executes the corresponding NavigationEngine method, and emits
    `navigation_ready` with the request ID so the owner can discard stale results.
    """

    navigation_ready = pyqtSignal(int, str, list, int, str)  # request_id, action, targets, line, file_path

    navigation_started = pyqtSignal(str)

    def __init__(self, engine: NavigationEngine, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._shutdown = False
        self._pending: list[_NavigationRequest] = []
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)

    @pyqtSlot(int, str, str, int, int, str)
    def process_request(
        self,
        request_id: int,
        action: str,
        text: str,
        line: int,
        col: int,
        file_path: str | None,
    ) -> None:
        """
        Enqueue a new navigation request.  The worker thread will pick it up.

        Called from the GUI thread (via NavigationManager.request).
        """
        req = _NavigationRequest(
            request_id=request_id,
            action=action,
            text=text,
            line=line,
            col=col,
            file_path=file_path,
        )
        with self._cv:
            self._pending.clear()
            self._pending.append(req)
            self._cv.notify()

    @pyqtSlot()
    def run(self) -> None:
        """
        Main loop of the worker thread.  Blocks on the condition variable
        until a request arrives, then executes it and emits the result.
        """
        while not self._shutdown:
            req: _NavigationRequest | None = None
            with self._cv:
                while not self._pending and not self._shutdown:
                    self._cv.wait()
                if self._shutdown:
                    break
                req = self._pending.pop(0)

            if req is None:
                continue

            try:
                self.navigation_started.emit(req.action)
                targets = self._execute_navigation(req)
                self.navigation_ready.emit(
                    req.request_id,
                    req.action,
                    targets,
                    req.line,
                    req.file_path or "",
                )
            except Exception as exc:
                logger.debug("Navigation worker error for %s: %s", req.action, exc)
                self.navigation_ready.emit(
                    req.request_id,
                    req.action,
                    [],
                    req.line,
                    req.file_path or "",
                )

    def _execute_navigation(self, req: _NavigationRequest) -> list[tuple[str, int, int]]:
        """Execute the requested navigation action and return target locations."""
        ctx = self._make_context(req)
        if req.action == "implementation":
            results = self._engine.get_implementation(ctx)
        elif req.action == "definition":
            results = self._engine.get_definition(ctx)
        elif req.action == "declaration":
            results = self._engine.get_declaration(ctx)
        elif req.action == "reference":
            results = self._engine.get_references(ctx)
        else:
            return []

        return [(r.file_path, r.line, r.col) for r in results if r.file_path]

    def _make_context(self, req: _NavigationRequest) -> CppContext:
        """Build a CppContext from the request payload."""
        from ..intellisense import args as cpp_args

        file_path = req.file_path or ""
        source = req.text or ""
        return CppContext(
            source_code=source,
            line=req.line + 1,  # CppContext uses 1-based
            col=req.col + 1,
            file_path=file_path,
            compile_args=cpp_args.args_for_file(file_path, source) if file_path else [],
        )

    def shutdown(self) -> None:
        """Signal the worker loop to exit."""
        with self._cv:
            self._shutdown = True
            self._cv.notify_all()

    def is_shutdown(self) -> bool:
        """Return ``True`` once the worker has been asked to stop."""
        return self._shutdown


class NavigationManager(QObject):
    """
    Per-editor navigation manager.  Owns a NavigationEngine and a background
    worker thread.  Provides a non-blocking `request()` API that returns
    immediately; results arrive via the `navigation_ready` signal.

    Usage:
        manager = NavigationManager(editor, file_path, parent, provider)
        manager.navigation_ready.connect(editor._on_navigation_ready)
        manager.request("implementation", text, line, col, file_path)
    """

    navigation_ready = pyqtSignal(int, str, list, int, str)
    navigation_started = pyqtSignal(str)

    def __init__(
        self,
        editor: CodeEditor,
        file_path: str | None = None,
        parent: QObject | None = None,
        provider: CppProvider | None = None,
    ) -> None:
        """
        Create a navigation manager for the given editor.

        Args:
            editor: The editor instance that owns this manager.
            file_path: Current file path (may be None for unsaved buffers).
            parent: Optional QObject parent (typically the editor itself).
            provider: Optional provider that owns the shared C++ index.
        """
        super().__init__(parent)
        self._editor = editor
        self._file_path = file_path
        self._request_counter = 0
        self._engine: NavigationEngine | None = None
        self._symbol_index = None
        self._worker: _NavigationWorker | None = None
        self._worker_thread: threading.Thread | None = None

        from ..provider import CppProvider

        if provider is None:
            candidate = getattr(editor, "current_provider", None)
            if isinstance(candidate, CppProvider):
                provider = candidate
        self._provider = provider

        if provider is not None:
            try:
                self._engine = NavigationEngine(provider._make_engine())
                self._refresh_symbol_index()
            except Exception as exc:
                logger.debug("C++ navigation engine unavailable: %s", exc)
                self._engine = None

        if self._engine is not None:
            self._worker = _NavigationWorker(self._engine)
            self._worker_thread = threading.Thread(
                target=self._worker.run,
                name="DreamStudio-CppNavigation",
                daemon=True,
            )
            self._worker_thread.start()
            self._worker.navigation_ready.connect(self._on_worker_ready)
            self._worker.navigation_started.connect(self.navigation_started.emit)

        destroyed = getattr(editor, "destroyed", None)
        if destroyed is not None:
            destroyed.connect(self.shutdown)

    @property
    def provider(self) -> CppProvider | None:
        """Return the provider that owns this manager, when available."""
        return self._provider

    def set_file_path(self, file_path: str | None) -> None:
        """Update the file path used for index lookup and context creation."""
        self._file_path = file_path
        self._refresh_symbol_index()

    def _refresh_symbol_index(self) -> None:
        """Attach the newest ready index for this file to the engine."""
        if self._engine is None or self._provider is None:
            return
        try:
            index = self._provider.get_symbol_index(self._file_path)
        except Exception as exc:
            logger.debug("Symbol index lookup failed: %s", exc)
            return
        if index is not None and index is not self._symbol_index:
            self._engine.set_symbol_index(index)
            self._symbol_index = index

    def request(
        self,
        action: str,
        text: str,
        line: int,
        col: int,
        file_path: str | None = None,
    ) -> bool:
        """
        Submit a navigation request.  Returns True if the request was
        accepted (always True unless the manager is shutting down).
        """
        if self._worker is None or self._worker.is_shutdown():
            return False

        if file_path is not None:
            self._file_path = file_path
        self._refresh_symbol_index()

        self._request_counter += 1
        req_id = self._request_counter

        self._worker.process_request(req_id, action, text, line, col, self._file_path)
        return True

    @pyqtSlot(int, str, list, int, str)
    def _on_worker_ready(
        self,
        request_id: int,
        action: str,
        targets: list[tuple[str, int, int]],
        line: int,
        file_path: str,
    ) -> None:
        """
        Slot called when the worker finishes a request.  We only forward
        the result if the request_id matches the latest request counter
        (latest-wins semantics).  Stale results are silently discarded.
        """
        if self._worker is None or request_id != self._request_counter:
            return
        self.navigation_ready.emit(request_id, action, targets, line, file_path)

    def shutdown(self) -> None:
        """Shut down the worker thread and clean up. Safe to call twice."""
        worker = self._worker
        if worker is not None:
            worker.shutdown()
        thread = self._worker_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        self._worker = None
        self._worker_thread = None


def create_navigation_manager(
    editor: CodeEditor,
    file_path: str | None = None,
    parent: QObject | None = None,
    provider: CppProvider | None = None,
) -> NavigationManager:
    """
    Factory function to create a NavigationManager for the given editor.
    This is the preferred way to instantiate the manager.
    """
    return NavigationManager(editor, file_path, parent, provider)
