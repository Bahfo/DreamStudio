"""Tests for the background diagnostics worker (jedi_worker.py).

Covers the subprocess (remote) round-trip, the in-process fallback when
the server is unavailable, debounced re-triggering, and shutdown hygiene.
"""

import time

import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtTest import QSignalSpy, QTest


def _wait_for(predicate, timeout_ms=5000):
    """Poll *predicate* while spinning the Qt event loop."""
    deadline = time.monotonic() + timeout_ms / 1000
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(50)
    return predicate()


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeEditor(QObject):
    """Minimal editor exposing the signals/methods ``DiagnosticManager``
    connects to."""

    textChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.underlines = []
        self._text = ""

    def text(self):
        return self._text

    def clear_diagnostic_underlines(self):
        self.underlines = []

    def add_diagnostic_underline(self, line, start_col, end_col, color_hex):
        self.underlines.append((line, start_col, end_col, color_hex))


def _make_manager(editor, **kwargs):
    from editor.Ironica.plugins.python.jedi_worker import DiagnosticManager

    return DiagnosticManager(editor=editor, debounce_ms=10, **kwargs)


class TestDiagnosticWorker:
    def test_remote_diagnostics_returns_server_result(self, qapp, monkeypatch):
        import editor.Ironica.plugins.python.jedi_worker as jw

        received = {}

        class _FakeProcess:
            def request(self, payload):
                received["payload"] = payload
                return ("diagnostics", payload[1], [])

            def shutdown(self):
                pass

        monkeypatch.setattr(jw, "AnalysisProcess", lambda: _FakeProcess())

        editor = _FakeEditor()
        manager = _make_manager(editor)
        try:
            spy = QSignalSpy(manager._results_ready)
            manager.trigger_analysis()
            assert _wait_for(lambda: len(spy) > 0), "diagnostics result was not emitted"

            assert received["payload"][0] == "diagnostics"
            assert received["payload"][2] == ""
            rid, diagnostics = spy[0]
            assert isinstance(diagnostics, list)
            assert diagnostics == []
        finally:
            manager.shutdown()

    def test_in_process_fallback_on_server_failure(self, qapp, monkeypatch):
        import editor.Ironica.plugins.python.jedi_worker as jw
        from editor.Ironica.plugins.python.detect_problems import detect_problems

        class _BrokenProcess:
            def request(self, payload):
                raise jw.AnalysisProcessError("boom")

            def shutdown(self):
                pass

        monkeypatch.setattr(jw, "AnalysisProcess", lambda: _BrokenProcess())

        source = "def broken(:\n"
        editor = _FakeEditor()
        manager = _make_manager(editor)
        try:
            spy = QSignalSpy(manager._results_ready)
            manager._worker.process(1, source, None)
            assert _wait_for(lambda: len(spy) > 0), "fallback diagnostics were not emitted"

            rid, diagnostics = spy[0]
            expected = detect_problems(source, None)
            assert [d.line for d in diagnostics] == [d.line for d in expected]
        finally:
            manager.shutdown()

    def test_stale_diagnostics_are_dropped(self, qapp, monkeypatch):
        import editor.Ironica.plugins.python.jedi_worker as jw

        class _FakeProcess:
            def request(self, payload):
                return ("diagnostics", payload[1], [])

            def shutdown(self):
                pass

        monkeypatch.setattr(jw, "AnalysisProcess", lambda: _FakeProcess())

        editor = _FakeEditor()
        manager = _make_manager(editor)
        try:
            manager._request_counter = 9
            manager._apply_results(8, [])
            assert editor.underlines == []  # stale — nothing rendered

            manager._apply_results(9, [])
            assert editor.underlines == []
        finally:
            manager.shutdown()

    def test_debounce_coalesces_rapid_edits(self, qapp, monkeypatch):
        import editor.Ironica.plugins.python.jedi_worker as jw

        calls = []

        class _FakeProcess:
            def request(self, payload):
                calls.append(payload[2])
                return ("diagnostics", payload[1], [])

            def shutdown(self):
                pass

        monkeypatch.setattr(jw, "AnalysisProcess", lambda: _FakeProcess())

        editor = _FakeEditor()
        manager = _make_manager(editor)
        try:
            spy = QSignalSpy(manager._results_ready)
            editor.textChanged.emit()
            editor.textChanged.emit()
            editor.textChanged.emit()
            assert _wait_for(lambda: len(spy) > 0), "coalesced diagnostics were not emitted"
            # The server should have seen the latest buffer only.
            assert calls == [""]
        finally:
            manager.shutdown()

    def test_shutdown_is_idempotent(self, qapp):
        editor = _FakeEditor()
        manager = _make_manager(editor)
        manager.shutdown()
        manager.shutdown()  # must not raise
        manager.trigger_analysis()  # must be a no-op after shutdown
