import jedi
import logging
import traceback
from collections import deque

from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

logger = logging.getLogger(__name__)


class JediWorker(QThread):
    results_ready = pyqtSignal(object, int)
    error_occurred = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()
        self._queue = deque()
        self._running = True
        self._project_path = None

    def set_project_path(self, path):
        self._project_path = path

    def request_completion(self, source, path, line, col, request_id):
        with QMutexLocker(self._mutex):
            self._queue.append(("complete", source, path, line, col, request_id))

    def request_goto(self, source, path, line, col, request_id):
        with QMutexLocker(self._mutex):
            self._queue.append(("goto", source, path, line, col, request_id))

    def request_hover(self, source, path, line, col, request_id):
        with QMutexLocker(self._mutex):
            self._queue.append(("hover", source, path, line, col, request_id))

    def run(self):
        while self._running:
            item = None
            with QMutexLocker(self._mutex):
                if self._queue:
                    item = self._queue.popleft()

            if item is None:
                self.msleep(15)
                continue

            cmd, source, path, line, col, rid = item

            try:
                script = jedi.Script(code=source, path=path)

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

    def shutdown(self, timeout=3000):
        self._running = False
        with QMutexLocker(self._mutex):
            self._queue.clear()
        self.wait(timeout)
        if self.isRunning():
            self.terminate()
            self.wait(1000)
