import subprocess
import threading
import json


class ClangdClient:
    def __init__(self, clangd_path="clangd"):
        self.proc = subprocess.Popen(
            [clangd_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
        )

        self._responses = {}
        self._lock = threading.Lock()
        self._running = True

        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        self._request_id = 0

    def _send(self, method, params):
        self._request_id += 1
        req_id = self._request_id

        request = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}

        raw = json.dumps(request)

        content = f"Content-Length: {len(raw)}\r\n\r\n{raw}"
        self.proc.stdin.write(content)
        self.proc.stdin.flush()

        return req_id

    def _read_loop(self):
        buffer = ""

        while self._running:
            try:
                line = self.proc.stdout.readline()
                if not line:
                    continue

                buffer += line

                if line.startswith("Content-Length:"):
                    length = int(line.split(":")[1].strip())

                    # skip header end
                    self.proc.stdout.readline()

                    body = self.proc.stdout.read(length)
                    if not body:
                        continue

                    msg = json.loads(body)

                    if "id" in msg:
                        with self._lock:
                            self._responses[msg["id"]] = msg

            except Exception:
                continue

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
        self._send(
            "initialize",
            {"processId": None, "rootUri": f"file://{root_path}", "capabilities": {}},
        )

    def did_open(self, file_path, source):
        self._send(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": f"file://{file_path}",
                    "languageId": "cpp",
                    "version": 1,
                    "text": source,
                }
            },
        )

    def completion(self, file_path, source, line, col):
        req_id = self._send(
            "textDocument/completion",
            {
                "textDocument": {"uri": f"file://{file_path}"},
                "position": {"line": line, "character": col},
            },
        )

        return self._wait_response(req_id)

    def shutdown(self):
        self._running = False
        try:
            self.proc.terminate()
        except Exception:
            pass
