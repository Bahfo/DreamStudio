import time
import json

from watchdog.events import FileSystemEventHandler, DirMovedEvent

#####################################################
# ERRORS
#####################################################
ERROR_NO_INITIAL_CONFIG = """Bootstrapping Failed:
No initial window was found, or not root directory was configured.\n
"""

ERROR_NO_INFO_FOUND = """Bootstrapping Failed:
No information for the project was given, terminated cretaing file,
terminated DreamStudio because project initialization information was
not given, or perhaps a further crash happened.

For further information, read the documentation.
"""

ERROR_NO_TYPE_GIVEN = """Bootstrapping Failed:
No given project type. DreamStudio terminated.
"""

UNEXPECTED_ERROR_OCCURED = """Project Creation Failed:
Unexpected error happened while creating project's folders. Terminated.
"""

NO_EVENT_HANDLER_EVENT_GIVEN = """Error: No event handler event given
No event for the event handler is specified, watchdog terminated.
"""


class DreamStudioErrors(Exception):

    _ERRORS = {
        (1, 1): ERROR_NO_INITIAL_CONFIG,
        (1, 2): ERROR_NO_INFO_FOUND,
        (1, 3): ERROR_NO_TYPE_GIVEN,
        (2, 1): UNEXPECTED_ERROR_OCCURED,
        (3, 1): NO_EVENT_HANDLER_EVENT_GIVEN,
    }

    def __init__(
        self,
        error_code: int,
        error_description_code: int,
        root_cause: None,
        window_cause: None,
    ):
        self.error_code = error_code
        self.error_desc_code = error_description_code

        message = self._ERRORS.get(
            (error_code, error_description_code), "Unknown IDE Error"
        )
        super.__init__(message)


class WatchdogBridgeHandler(FileSystemEventHandler):
    def __init__(self, debouncer):
        self.debouncer = debouncer

    def on_created(self, event):
        self.debouncer.push({"type": "FILE_ADDED", "path": event.src_path})

    def on_deleted(self, event):
        self.debouncer.push({"type": "FILE_REMOVED", "path": event.src_path})

    def on_modified(self, event):
        self.debouncer.push({"type": "FILE_CHANGED", "path": event.src_path})

    def on_moved(self, event):
        self.debouncer.push(
            {"type": "FILE_MOVED", "path": event.dest_path, "old_path": event.src_path}
        )
        if isinstance(event, DirMovedEvent):
            for old_path, data in list(self.debouncer.pending.items()):
                if old_path.startswith(event.src_path + "/"):
                    relative = old_path[len(event.src_path) :]
                    new_path = event.dest_path + relative
                    self.debouncer.pending[new_path] = self.debouncer.pending.pop(
                        old_path
                    )
                    self.debouncer.pending[new_path]["event"]["path"] = new_path


class Debouncer:
    def __init__(
        self, delay=0.2, output_queue=None, persist_file="debounce_state.json"
    ):
        self.delay = delay
        self.pending = {}  # path -> {"event":..., "time":...}
        self.output_queue = output_queue
        self.persist_file = persist_file
        self.load_state()
        import atexit

        atexit.register(self.save_state)

    def save_state(self):
        serializable = {p: v["event"] for p, v in self.pending.items()}
        with open(self.persist_file, "w") as f:
            json.dump(serializable, f)

    def load_state(self):
        try:
            with open(self.persist_file, "r") as f:
                loaded = json.load(f)
                now = time.monotonic()
                for path, event in loaded.items():
                    self.pending[path] = {"event": event, "time": now}
        except FileNotFoundError:
            pass

    def push(self, event):
        if event["path"].endswith((".tmp", ".swp", "~", ".log")):
            return
        key = event["path"]
        self.pending[key] = {"event": event, "time": time.monotonic()}

    def poll(self):
        now = time.monotonic()
        for path, data in list(self.pending.items()):
            if now - data["time"] >= self.delay:
                stable_event = self.pending.pop(path)
                if self.output_queue:
                    self.output_queue.put(stable_event["event"])
