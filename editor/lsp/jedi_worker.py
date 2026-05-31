import jedi
import logging
import traceback
from collections import deque
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition

logger = logging.getLogger(__name__)

_MAX_QUEUE = 20


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
        self._last_script_key = None
        self._cached_script = None

    def set_virtual_environment(self, venv_path: Optional[str]) -> None:
        self.current_venv_path = venv_path
        if venv_path:
            try:
                self._jedi_env = jedi.create_environment(venv_path)
            except Exception:
                self._jedi_env = jedi.get_default_environment()
        else:
            self._jedi_env = jedi.get_default_environment()

    def _enqueue(self, cmd, source, path, line, col, request_id):
        key = (cmd, path)
        self._mutex.lock()
        try:
            for i, existing in enumerate(self._queue):
                if (existing[0], existing[2]) == key:
                    self._queue[i] = (cmd, source, path, line, col, request_id)
                    break
            else:
                if len(self._queue) >= _MAX_QUEUE:
                    self._queue.popleft()
                self._queue.append((cmd, source, path, line, col, request_id))
            self._cond.wakeOne()
        finally:
            self._mutex.unlock()

    def request_completion(self, source, path, line, col, request_id):
        self._enqueue("complete", source, path, line, col, request_id)

    def request_goto(self, source, path, line, col, request_id):
        self._enqueue("goto", source, path, line, col, request_id)

    def request_hover(self, source, path, line, col, request_id):
        self._enqueue("hover", source, path, line, col, request_id)

    def request_references(self, source, path, line, col, request_id):
        self._enqueue("references", source, path, line, col, request_id)

    def _get_script(self, source, path):
        key = (source, path)
        if key == self._last_script_key and self._cached_script is not None:
            return self._cached_script
        script = jedi.Script(code=source, path=path, environment=self._jedi_env)
        self._last_script_key = key
        self._cached_script = script
        return script

    def run(self):
        while self._running:
            item = None
            self._mutex.lock()
            try:
                while self._running and not self._queue:
                    self._cond.wait(self._mutex, 50)
                if not self._running or not self._queue:
                    self._mutex.unlock()
                    continue
                # Drain stale items: if a newer request with the same (cmd,path)
                # is already queued, skip this one
                while self._queue:
                    candidate = self._queue[0]
                    stale = False
                    if len(self._queue) > 1:
                        for later in list(self._queue)[1:]:
                            if (later[0], later[2]) == (candidate[0], candidate[2]):
                                self._queue.popleft()
                                stale = True
                                break
                    if not stale:
                        break
                if not self._queue:
                    self._mutex.unlock()
                    continue
                item = self._queue.popleft()
            finally:
                self._mutex.unlock()

            if item is None:
                continue

            cmd, source, path, line, col, rid = item

            try:
                script = self._get_script(source, path)

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

                elif cmd == "references":
                    result = script.get_references(line, col)
                    refs = []
                    for r in result:
                        refs.append({
                            "file": str(r.module_path) if r.module_path else None,
                            "line": r.line,
                            "column": r.column,
                            "name": r.name,
                            "description": r.description,
                            "type": r.type,
                        })
                    self.results_ready.emit(("references", rid, refs), rid)

            except Exception:
                logger.debug("JediWorker error: %s", traceback.format_exc())
                self.error_occurred.emit(traceback.format_exc(), rid)

    def shutdown(self, timeout=3000):
        self._running = False
        self._mutex.lock()
        self._queue.clear()
        self._cond.wakeOne()
        self._mutex.unlock()
        self.wait(timeout)
        if self.isRunning():
            self.terminate()
            self.wait(1000)
