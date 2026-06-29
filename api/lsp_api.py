"""
LspAPI - Wraps Jedi LSP worker functionality.

Provides access to code intelligence (completion, goto, hover, references).
"""

from typing import Optional


class LspAPI:
    """API for Language Server Protocol operations."""

    def __init__(self, main_window):
        self._main = main_window

    def _worker(self):
        return getattr(self._main, "_jedi_worker", None)

    def isRunning(self) -> bool:
        """Check if the Jedi worker is running."""
        worker = self._worker()
        if worker is None:
            return False
        return worker.isRunning() if hasattr(worker, "isRunning") else True

    def setVirtualEnvironment(self, venv_path: Optional[str]) -> None:
        """Set the virtual environment path for Jedi."""
        worker = self._worker()
        if worker is not None:
            worker.set_virtual_environment(venv_path)

    def requestCompletion(self, source: str, file_path: str,
                          line: int, col: int, request_id: int) -> None:
        """Request code completions from Jedi."""
        worker = self._worker()
        if worker is not None:
            worker.request_completion(source, file_path, line, col, request_id)

    def requestGoto(self, source: str, file_path: str,
                    line: int, col: int, request_id: int) -> None:
        """Request goto definition from Jedi."""
        worker = self._worker()
        if worker is not None:
            worker.request_goto(source, file_path, line, col, request_id)

    def requestHover(self, source: str, file_path: str,
                     line: int, col: int, request_id: int) -> None:
        """Request hover information from Jedi."""
        worker = self._worker()
        if worker is not None:
            worker.request_hover(source, file_path, line, col, request_id)

    def requestReferences(self, source: str, file_path: str,
                          line: int, col: int, request_id: int) -> None:
        """Request find references from Jedi."""
        worker = self._worker()
        if worker is not None:
            worker.request_references(source, file_path, line, col, request_id)

    def shutdown(self) -> None:
        """Shut down the Jedi worker."""
        worker = self._worker()
        if worker is not None:
            worker.shutdown()

    def getRequestCounter(self) -> int:
        """Get the current request counter value."""
        return getattr(self._main, "_jedi_request_counter", 0)
