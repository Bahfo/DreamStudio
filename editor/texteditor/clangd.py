import subprocess
import threading
import json
import logging
import os

logger = logging.getLogger(__name__)


class ClangdClient:
    def __init__(self, clangd_path="clangd"):
        self._running = False
        self._proc = None
        self._reader_thread = None
        self._responses = {}
        self._lock = threading.Lock()
        self._request_id = 0
        self._clangd_path = clangd_path

        self._start_process()

    def _start_process(self):
        if not self._find_clangd():
            logger.warning("clangd not found on PATH; ClangdClient is inactive")
            return

        try:
            self._proc = subprocess.Popen(
                [self._clangd_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
            )
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()
        except FileNotFoundError:
            logger.warning("clangd binary not found; ClangdClient disabled")
            self._proc = None
            self._running = False
        except OSError as e:
            logger.warning("Failed to start clangd: %s", e)
            self._proc = None
            self._running = False

    def _find_clangd(self):
        if os.path.isabs(self._clangd_path):
            return os.path.isfile(self._clangd_path) and os.access(
                self._clangd_path, os.X_OK
            )
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            full = os.path.join(path_dir, self._clangd_path)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                return True
        return False

    def is_active(self):
        return self._running and self._proc is not None and self._proc.poll() is None

    def _send(self, method, params):
        if not self.is_active():
            return None
        self._request_id += 1
        req_id = self._request_id
        request = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        raw = json.dumps(request)
        content = f"Content-Length: {len(raw)}\r\n\r\n{raw}"
        try:
            self._proc.stdin.write(content)
            self._proc.stdin.flush()
            return req_id
        except (BrokenPipeError, OSError):
            self.shutdown()
            return None

    def _read_loop(self):
        while self._running:
            try:
                header = self._proc.stdout.readline()
                if not header:
                    break
                header = header.strip()
                if not header.startswith("Content-Length:"):
                    continue
                length = int(header.split(":")[1].strip())
                blank = self._proc.stdout.readline()
                if blank is None:
                    break
                body = self._proc.stdout.read(length)
                if not body:
                    continue
                msg = json.loads(body)
                if "id" in msg:
                    with self._lock:
                        self._responses[msg["id"]] = msg
            except (ValueError, json.JSONDecodeError, AttributeError):
                continue
            except (BrokenPipeError, OSError):
                break

    def _wait_response(self, req_id, timeout=1.0):
        import time

        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                if req_id in self._responses:
                    return self._responses.pop(req_id)
            time.sleep(0.01)
        return None

    def initialize(self, root_path):
        self._send("initialize", {
            "processId": None,
            "rootUri": f"file://{root_path}",
            "capabilities": {},
        })

    def did_open(self, file_path, source):
        self._send("textDocument/didOpen", {
            "textDocument": {
                "uri": f"file://{file_path}",
                "languageId": "cpp",
                "version": 1,
                "text": source,
            }
        })

    def completion(self, file_path, source, line, col):
        req_id = self._send("textDocument/completion", {
            "textDocument": {"uri": f"file://{file_path}"},
            "position": {"line": line, "character": col},
        })
        if req_id is None:
            return None
        return self._wait_response(req_id)

    def shutdown(self):
        self._running = False
        proc = self._proc
        if proc is None:
            return
        try:
            self._send("shutdown", {})
        except Exception:
            pass
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        try:
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=1)
            except Exception:
                pass
        self._proc = None
