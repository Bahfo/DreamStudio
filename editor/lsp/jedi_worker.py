import jedi
import logging
import traceback
from collections import deque
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition

logger = logging.getLogger(__name__)


class JediWorker(QThread):
    results_ready = pyqtSignal(object, int)
    error_occurred = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()
        self._cond = QWaitCondition()
        self._queue = deque()
        self._running = True
        self.current_venv_path: Optional[str] = None
        self._jedi_env = jedi.get_default_environment()

    def set_virtual_environment(self, venv_path: Optional[str]) -> None:
        self.current_venv_path = venv_path
        if venv_path:
            try:
                self._jedi_env = jedi.create_environment(venv_path)
            except Exception:
                self._jedi_env = jedi.get_default_environment()
        else:
            self._jedi_env = jedi.get_default_environment()

    def request_completion(self, source: str, path: str, line: int, col: int, request_id: int) -> None:
        self._mutex.lock()
        self._queue.append(("complete", source, path, line, col, request_id))
        self._cond.wakeOne()
        self._mutex.unlock()

    def request_goto(self, source: str, path: str, line: int, col: int, request_id: int) -> None:
        self._mutex.lock()
        self._queue.append(("goto", source, path, line, col, request_id))
        self._cond.wakeOne()
        self._mutex.unlock()

    def request_hover(self, source: str, path: str, line: int, col: int, request_id: int) -> None:
        self._mutex.lock()
        self._queue.append(("hover", source, path, line, col, request_id))
        self._cond.wakeOne()
        self._mutex.unlock()

    def run(self) -> None:
        while self._running:
            item = None
            self._mutex.lock()
            while self._running and not self._queue:
                self._cond.wait(self._mutex, 50)
            if not self._running:
                self._mutex.unlock()
                break
            if not self._queue:
                self._mutex.unlock()
                continue
            item = self._queue.popleft()
            self._mutex.unlock()

            if item is None:
                continue

            cmd, source, path, line, col, rid = item

            try:
                script = jedi.Script(code=source, path=path, environment=self._jedi_env)

                if cmd == "complete":
                    result = script.complete(line, col)
                    items = []
                    seen = set()
                    for c in result:
                        key = (c.name, c.type)
                        if key in seen:
                            continue
                        seen.add(key)
                        items.append({
                            "label": c.name,
                            "type": c.type,
                            "module": c.module_name,
                            "description": c.description,
                            "doc": c.docstring(),
                            "line": c.line,
                            "column": c.column,
                        })
                    self.results_ready.emit(("complete", rid, items), rid)

                elif cmd == "goto":
                    result = script.goto(line, col, follow_imports=True)
                    defs = []
                    for d in result:
                        defs.append({
                            "file": str(d.module_path) if d.module_path else None,
                            "line": d.line,
                            "column": d.column,
                            "name": d.name,
                            "description": d.description,
                            "type": d.type,
                            "in_builtin": d.in_builtin_module(),
                            "doc": d.docstring(),
                        })
                    self.results_ready.emit(("goto", rid, defs), rid)

                elif cmd == "hover":
                    result = script.infer(line, col)
                    hovers = []
                    for h in result:
                        hovers.append({
                            "name": h.name,
                            "description": h.description,
                            "doc": h.docstring(),
                            "type": h.type,
                            "line": h.line,
                            "column": h.column,
                        })
                    self.results_ready.emit(("hover", rid, hovers), rid)

            except Exception:
                logger.debug("JediWorker error: %s", traceback.format_exc())
                self.error_occurred.emit(traceback.format_exc(), rid)

    def shutdown(self, timeout: int = 3000) -> None:
        self._running = False
        self._mutex.lock()
        self._queue.clear()
        self._cond.wakeOne()
        self._mutex.unlock()
        self.wait(timeout)
        if self.isRunning():
            self.terminate()
            self.wait(1000)
