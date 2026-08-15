"""Tests for the out-of-process analysis bridge and server dispatch.

Covers:
- Wire framing round-trips (length-prefixed pickle) over ``BytesIO``
- EOF / truncated-frame failure behaviour
- ``AnalysisProcess`` spawning a real analysis subprocess and talking to it
- Server request dispatch (analysis + diagnostics + error responses)

The real ``editor`` package is imported eagerly so ``analysis_server``'s
package stubs (which only isolate a *child* process) never clobber the
already-loaded package in the test session.
"""

import io
import threading

import editor  # noqa: F401  (see module docstring)
import pytest

from editor.Ironica.analysis_bridge import (
    AnalysisProcess,
    AnalysisProcessError,
    read_frame,
    write_frame,
)

_PYTHON_CONFIG = {
    "lang": "python",
    "extensions": ["py"],
    "styles": {
        "keyword": "#FF0000",
        "string": "#00FF00",
        "comment": "#6A9955",
        "number": "#B5CEA8",
        "operator": "#D4D4D4",
        "function": "#DCDCAA",
        "class": "#4EC9B0",
        "variable": "#9CDCFE",
        "parameter": "#9CDCFE",
        "module": "#DCDCAA",
        "self": "#569CD6",
        "decorator": "#DCDCAA",
        "definition": "#DCDCAA",
        "exception": "#F48771",
    },
    "keywords": {"keyword": ["def", "class", "if", "return"]},
}


class TestFraming:
    def test_round_trip_payloads(self):
        stream = io.BytesIO()
        payloads = [
            0,
            "plain text",
            {"list": [1, 2, (3, 4)], "bytes": True},
            ("analysis", 7, "def x():\n    pass\n", {"lang": "python"}, "dark"),
            ("diagnostics", 3, "x = 1\n", "/tmp/a.py"),
            None,
        ]
        for payload in payloads:
            write_frame(stream, payload)

        stream.seek(0)
        for payload in payloads:
            assert read_frame(stream) == payload

    def test_truncated_frame_raises(self):
        stream = io.BytesIO(b"\x10\x00\x00\x00\x00\x00\x00\x00" + b"short")
        with pytest.raises(AnalysisProcessError):
            read_frame(stream)

    def test_closed_stream_raises(self):
        stream = io.BytesIO()
        with pytest.raises(AnalysisProcessError):
            read_frame(stream)


class TestAnalysisProcess:
    def test_real_subprocess_analysis(self):
        process = AnalysisProcess()
        try:
            process.start()
            assert process.is_alive()

            kind, rid, highlights, folds = process.request(
                (
                    "analysis",
                    1,
                    "def foo():\n    x = 1\n    return x\n",
                    _PYTHON_CONFIG,
                    "dark",
                )
            )
            assert kind == "analysis"
            assert rid == 1
            assert isinstance(highlights, list)
            assert any(h[:2] == (4, 3) for h in highlights)  # "foo"
            assert isinstance(folds, list)
            assert folds and folds[0].start_line == 0

            kind, rid, diagnostics = process.request(
                ("diagnostics", 2, "x = 1\n", None)
            )
            assert kind == "diagnostics"
            assert rid == 2
            assert isinstance(diagnostics, list)
        finally:
            process.shutdown()
        assert not process.is_alive()

    def test_respawns_dead_process(self):
        process = AnalysisProcess()
        try:
            process.start()
            process._proc.kill()
            process._proc.wait()
            assert not process.is_alive()

            process.start()
            assert process.is_alive()
            kind, rid, _, _ = process.request(
                ("analysis", 9, "x = 1\n", _PYTHON_CONFIG, "dark")
            )
            assert kind == "analysis"
            assert rid == 9
        finally:
            process.shutdown()


class TestServerDispatch:
    def test_diagnostics_dispatch(self):
        from editor.Ironica.analysis_server import handle_request

        kind, rid, diagnostics = handle_request(
            ("diagnostics", 11, "import math\nmath.sq\x01t(2)\n", None)
        )
        assert kind == "diagnostics"
        assert rid == 11
        assert isinstance(diagnostics, list)

    def test_analysis_dispatch(self):
        from editor.Ironica.analysis_server import handle_request

        kind, rid, highlights, folds = handle_request(
            ("analysis", 12, "def foo():\n    return 1\n", _PYTHON_CONFIG, "dark")
        )
        assert kind == "analysis"
        assert rid == 12
        assert isinstance(highlights, list)
        assert isinstance(folds, list)

    def test_unknown_payload_returns_error(self):
        from editor.Ironica.analysis_server import handle_request

        kind, rid, message = handle_request(("bogus", 13))
        assert kind == "error"
        assert rid == 13
        assert isinstance(message, str)

    def test_handler_exception_returns_error(self):
        from editor.Ironica.analysis_server import handle_request

        kind, rid, message = handle_request(
            ("analysis", 14, None, None, None)
        )
        assert kind == "error"
        assert rid == 14
        assert isinstance(message, str)


class TestThreadSafety:
    def test_shutdown_is_idempotent(self):
        process = AnalysisProcess()
        process.shutdown()
        process.shutdown()
