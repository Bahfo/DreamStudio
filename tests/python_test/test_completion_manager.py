"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the debounced background completion manager and its worker plumbing.
"""

from __future__ import annotations

import dataclasses

import pytest

from editor.Ironica.analysis_bridge import AnalysisProcessError
from editor.Ironica.plugins.python.jedi_worker import (
    _MAX_COMPLETION_ITEMS,
    COMPLETION_DEBOUNCE_MS,
    CompletionManager,
    _CompletionRequest,
    _CompletionWorker,
)


class _RecordingWorker:
    """Stand-in completion worker that records submissions."""

    def __init__(self, error: Exception | None = None) -> None:
        self.requests: list[dict] = []
        self.shutdown_calls = 0
        self.error = error

    def process(self, request_id, source, line, col, file_path, warmup=False):
        if self.error is not None:
            raise self.error
        self.requests.append(
            {
                "request_id": request_id,
                "source": source,
                "line": line,
                "col": col,
                "file_path": file_path,
                "warmup": warmup,
            }
        )

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class _FakeProcess:
    """Stand-in for the completion subprocess bridge."""

    def __init__(self, response=None) -> None:
        self.response = response
        self.payloads: list[object] = []
        self.shutdown_calls = 0

    def request(self, payload):
        self.payloads.append(payload)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class _FakeTimer:
    """Minimal QTimer replacement for error-path tests."""

    def __init__(self, start_error=None, interval_error=None) -> None:
        self.start_error = start_error
        self.interval_error = interval_error
        self.active = False
        self.interval_value = None
        self.stop_calls = 0

    def setInterval(self, value):
        if self.interval_error is not None:
            raise self.interval_error
        self.interval_value = value

    def start(self):
        if self.start_error is not None:
            raise self.start_error
        self.active = True

    def stop(self):
        self.stop_calls += 1
        self.active = False

    def isActive(self):
        return self.active


class _Owner:
    """Minimal owner for direct worker construction."""

    def __init__(self, process=None) -> None:
        self._editor = object()
        self._request_counter = 0
        self._process = process or _FakeProcess()
        self.completions_ready = _SignalRecorder()


class _SignalRecorder:
    """Records signal emissions without requiring a Qt signal."""

    def __init__(self) -> None:
        self.emitted: list[tuple] = []

    def emit(self, *args) -> None:
        self.emitted.append(args)


@pytest.fixture
def completion_factory(fake_editor):
    """Create completion managers with isolated workers and processes."""
    created: list[CompletionManager] = []

    def make(
        file_path="/tmp/module.py", error=None, worker=None
    ) -> tuple[CompletionManager, _RecordingWorker]:
        manager = CompletionManager(editor=fake_editor, file_path=file_path)
        fake_worker = worker if worker is not None else _RecordingWorker(error)
        manager._worker = fake_worker
        manager._process = _FakeProcess()
        created.append(manager)
        return manager, fake_worker

    yield make

    for manager in created:
        manager.shutdown()


class TestCompletionManagerConstruction:
    """Tests for manager wiring and public constants."""

    def test_constants(self):
        """The documented debounce and result cap are stable."""
        assert COMPLETION_DEBOUNCE_MS == 30
        assert _MAX_COMPLETION_ITEMS == 50

    def test_owner_and_defaults(self, completion_factory):
        """The manager starts enabled with its path and timer configured."""
        make = completion_factory
        manager, _worker = make(file_path="/tmp/a.py")

        assert manager.owner_id == id(manager._editor)
        assert manager._file_path == "/tmp/a.py"
        assert manager._enabled is True
        assert manager._dead is False
        assert manager._debounce_timer.interval() == COMPLETION_DEBOUNCE_MS

    def test_setting_file_path(self, completion_factory):
        """Save-as/rename repoints completion requests."""
        make = completion_factory
        manager, _worker = make()

        manager.set_file_path("/tmp/new.py")

        assert manager._file_path == "/tmp/new.py"


class TestCompletionRequests:
    """Tests for debounce request submission."""

    def test_request_records_pending_state(self, qapp, completion_factory):
        """A request stores its caret, source, and path."""
        make = completion_factory
        manager, _worker = make()

        assert manager.request("value = 1", 2, 4, "/tmp/a.py", "val") is True
        assert manager._pending_source == "value = 1"
        assert manager._pending_line == 2
        assert manager._pending_col == 4
        assert manager._pending_file_path == "/tmp/a.py"
        assert manager._request_counter == 1
        assert manager._debounce_timer.isActive()

    def test_request_falls_back_to_the_manager_path(self, qapp, completion_factory):
        """An omitted path uses the manager's configured file."""
        make = completion_factory
        manager, _worker = make(file_path="/tmp/default.py")

        manager.request("value", 0, 0, None)

        assert manager._pending_file_path == "/tmp/default.py"

    def test_explicit_path_overrides_the_manager_path(self, qapp, completion_factory):
        """A per-request path wins over the default."""
        make = completion_factory
        manager, _worker = make(file_path="/tmp/default.py")

        manager.request("value", 0, 0, "/tmp/explicit.py")

        assert manager._pending_file_path == "/tmp/explicit.py"

    def test_each_request_increments_the_counter(self, qapp, completion_factory):
        """Request ids advance monotonically."""
        make = completion_factory
        manager, _worker = make()

        manager.request("a", 0, 0, None)
        manager.request("b", 0, 0, None)

        assert manager._request_counter == 2

    def test_dead_manager_rejects_requests(self, completion_factory):
        """Once the editor is gone no new request is accepted."""
        make = completion_factory
        manager, _worker = make()
        manager._dead = True

        assert manager.request("value", 0, 0, None) is False
        assert manager._request_counter == 0

    def test_timer_start_failure_marks_the_manager_dead(self, completion_factory):
        """A deleted C++ timer degrades to a dead manager."""
        make = completion_factory
        manager, _worker = make()
        manager._debounce_timer = _FakeTimer(start_error=RuntimeError("gone"))

        assert manager.request("value", 0, 0, None) is False
        assert manager._dead is True

    def test_timer_interval_failure_is_tolerated(self, completion_factory):
        """Adaptive delay failures do not block the request."""
        make = completion_factory
        manager, _worker = make()
        manager._debounce_timer = _FakeTimer(
            interval_error=RuntimeError("adaptive failed")
        )

        assert manager.request("value", 0, 0, None) is True
        assert manager._debounce_timer.isActive()


class TestCompletionDebounceFire:
    """Tests for turning a pending request into worker work."""

    def test_pending_state_is_forwarded_to_the_worker(self, qapp, completion_factory):
        """The worker receives the stored request verbatim."""
        make = completion_factory
        manager, worker = make(file_path="/tmp/default.py")
        manager.request("value = 1", 2, 3, "/tmp/a.py")

        manager._on_debounce_fired()

        assert worker.requests == [
            {
                "request_id": 1,
                "source": "value = 1",
                "line": 2,
                "col": 3,
                "file_path": "/tmp/a.py",
                "warmup": False,
            }
        ]

    def test_disabled_manager_does_not_submit(self, qapp, completion_factory):
        """A background tab never asks for completions."""
        make = completion_factory
        manager, worker = make()
        manager.request("value", 0, 0, None)
        manager.set_enabled(False)

        manager._on_debounce_fired()

        assert worker.requests == []

    def test_disabling_stops_the_timer(self, qapp, completion_factory):
        """Losing focus cancels an armed request."""
        make = completion_factory
        manager, _worker = make()
        manager.request("value", 0, 0, None)

        manager.set_enabled(False)

        assert manager._debounce_timer.isActive() is False

    def test_worker_failure_is_swallowed(self, qapp, completion_factory):
        """A submission error never escapes the timer slot."""
        make = completion_factory
        manager, _worker = make(error=RuntimeError("worker gone"))
        manager.request("value", 0, 0, None)

        manager._on_debounce_fired()

    def test_invalidate_clears_pending_state(self, qapp, completion_factory):
        """Invalidation retires in-flight and armed requests."""
        make = completion_factory
        manager, _worker = make()
        manager.request("value", 1, 2, "/tmp/a.py")
        before = manager._request_counter

        manager.invalidate()

        assert manager._request_counter == before + 1
        assert manager._pending_source == ""
        assert manager._pending_file_path is None
        assert manager._debounce_timer.isActive() is False

    def test_invalidate_on_a_dead_manager_is_safe(self, completion_factory):
        """A dead manager can still be invalidated."""
        make = completion_factory
        manager, _worker = make()
        manager._dead = True

        manager.invalidate()

        assert manager._pending_source == ""


class TestCompletionWarmup:
    """Tests for cache-priming warmup requests."""

    def test_warmup_submits_with_the_warmup_flag(self, completion_factory):
        """Warmup work is marked so its results are discarded."""
        make = completion_factory
        manager, worker = make(file_path="/tmp/a.py")

        manager.warmup("value", 1, 2)

        assert worker.requests == [
            {
                "request_id": 0,
                "source": "value",
                "line": 1,
                "col": 2,
                "file_path": "/tmp/a.py",
                "warmup": True,
            }
        ]

    def test_warmup_uses_an_explicit_path(self, completion_factory):
        """A per-call path overrides the manager path."""
        make = completion_factory
        manager, worker = make(file_path="/tmp/default.py")

        manager.warmup("value", 0, 0, file_path="/tmp/explicit.py")

        assert worker.requests[0]["file_path"] == "/tmp/explicit.py"

    def test_empty_source_is_not_warmed(self, completion_factory):
        """There is nothing to prime for an empty buffer."""
        make = completion_factory
        manager, worker = make()

        manager.warmup("", 0, 0)

        assert worker.requests == []

    def test_whitespace_only_source_is_forwarded(self, completion_factory):
        """Current contract: only a truly empty string is skipped."""
        make = completion_factory
        manager, worker = make()

        manager.warmup("   ", 0, 0)

        assert worker.requests[0]["source"] == "   "

    def test_disabled_manager_does_not_warm(self, completion_factory):
        """Warmup respects the focus gate."""
        make = completion_factory
        manager, worker = make()
        manager.set_enabled(False)

        manager.warmup("value", 0, 0)

        assert worker.requests == []

    def test_dead_manager_does_not_warm(self, completion_factory):
        """A dead manager never touches the worker."""
        make = completion_factory
        manager, worker = make()
        manager._dead = True

        manager.warmup("value", 0, 0)

        assert worker.requests == []


class TestCompletionShutdown:
    """Tests for editor destruction and process cleanup."""

    def test_editor_destruction_marks_the_manager_dead(self, completion_factory):
        """Losing the editor shuts the manager down exactly once."""
        make = completion_factory
        manager, worker = make()

        manager._on_editor_destroyed()

        assert manager._dead is True
        assert manager._enabled is False
        assert worker.shutdown_calls == 1
        assert manager._process.shutdown_calls == 1

    def test_shutdown_stops_timer_and_worker(self, qapp, completion_factory):
        """Shutdown disables the manager and releases resources."""
        make = completion_factory
        manager, worker = make()
        manager.request("value", 0, 0, None)

        manager.shutdown()

        assert manager._enabled is False
        assert manager._debounce_timer.isActive() is False
        assert worker.shutdown_calls == 1
        assert manager._process.shutdown_calls == 1

    def test_shutdown_is_safe_to_repeat(self, completion_factory):
        """A second shutdown does not raise."""
        make = completion_factory
        manager, _worker = make()

        manager.shutdown()
        manager.shutdown()


class TestCompletionWorkerRequests:
    """Tests for the worker's subprocess request protocol."""

    @staticmethod
    def _worker(process) -> _CompletionWorker:
        return _CompletionWorker(_Owner(process))

    def test_successful_remote_response(self):
        """A well-formed response returns the completion payload."""
        process = _FakeProcess(("completions", 1, [{"text": "value"}]))
        worker = self._worker(process)
        request = _CompletionRequest(1, "value", 0, 0, "/tmp/a.py")

        assert worker._remote_completions(request) == [{"text": "value"}]
        assert process.payloads == [("completions", 1, "value", 0, 0, "/tmp/a.py")]

    def test_none_response_means_superseded(self):
        """A ``None`` response is not an error."""
        worker = self._worker(_FakeProcess(None))
        request = _CompletionRequest(1, "value", 0, 0, None)

        assert worker._remote_completions(request) is None

    def test_wrong_response_kind_raises(self):
        """A response for another service is rejected."""
        worker = self._worker(_FakeProcess(("diagnostics", 1, [])))
        request = _CompletionRequest(1, "value", 0, 0, None)

        with pytest.raises(AnalysisProcessError, match="server error"):
            worker._remote_completions(request)

    @pytest.mark.parametrize("response", [[], "text", 42])
    def test_malformed_response_raises(self, response):
        """Non-tuple or empty responses are protocol errors."""
        worker = self._worker(_FakeProcess(response))
        request = _CompletionRequest(1, "value", 0, 0, None)

        with pytest.raises(AnalysisProcessError, match="malformed"):
            worker._remote_completions(request)

    def test_process_exception_propagates(self):
        """Transport failures reach the worker's retry boundary."""
        worker = self._worker(_FakeProcess(RuntimeError("pipe broken")))
        request = _CompletionRequest(1, "value", 0, 0, None)

        with pytest.raises(RuntimeError, match="pipe broken"):
            worker._remote_completions(request)


class TestCompletionWorkerQueue:
    """Tests for the worker's latest-wins queue."""

    def test_process_stores_the_request_without_starting_again(self):
        """An already-started worker just replaces the pending request."""
        worker = _CompletionWorker(_Owner())
        worker._started_once = True

        worker.process(4, "value", 1, 2, "/tmp/a.py", warmup=True)

        assert worker._current_request == _CompletionRequest(
            4, "value", 1, 2, "/tmp/a.py", warmup=True
        )
        assert worker._wake.is_set()

    def test_process_after_shutdown_is_ignored(self):
        """A shutdown worker refuses new work."""
        worker = _CompletionWorker(_Owner())
        worker._started_once = True
        worker.shutdown()

        worker.process(1, "value", 0, 0, None)

        assert worker._current_request is None

    def test_shutdown_clears_pending_work(self):
        """Shutdown drops the queued request and wakes the thread."""
        worker = _CompletionWorker(_Owner())
        worker._started_once = True
        worker.process(1, "value", 0, 0, None)

        worker.shutdown()

        assert worker._is_shutting_down is True
        assert worker._current_request is None
        assert worker._wake.is_set()

    def test_completion_request_is_frozen(self):
        """Queued requests cannot be mutated after submission."""
        request = _CompletionRequest(1, "value", 0, 0, None)

        with pytest.raises(dataclasses.FrozenInstanceError):
            request.source = "other"


class TestCompletionFallback:
    """Tests for the in-process Jedi fallback."""

    @staticmethod
    def _worker() -> _CompletionWorker:
        return _CompletionWorker(_Owner())

    def test_real_jedi_completion_is_returned(self):
        """The fallback still produces useful completions."""
        worker = self._worker()
        request = _CompletionRequest(1, "import os\nos.pa\n", 1, 5, "/tmp/a.py")

        results = worker._fallback_completions(request)

        assert any(item["text"] == "path" for item in results)
        assert all(
            set(item) == {"text", "insert_text", "kind", "signature"}
            for item in results
        )

    def test_results_are_capped(self):
        """The fallback never returns more than the documented limit."""
        worker = self._worker()
        request = _CompletionRequest(1, "", 0, 0, None)

        results = worker._fallback_completions(request)

        assert len(results) == _MAX_COMPLETION_ITEMS

    def test_out_of_range_caret_is_clamped(self):
        """A caret column past the line end is clamped."""
        worker = self._worker()
        request = _CompletionRequest(1, "import os\nos.pa", 1, 500, "/tmp/a.py")

        results = worker._fallback_completions(request)

        assert any(item["text"] == "path" for item in results)

    def test_caret_line_is_clamped_to_the_buffer(self):
        """A caret row past the buffer is clamped to the last line."""
        worker = self._worker()
        request = _CompletionRequest(1, "value = 1\n", 99, 0, None)

        assert isinstance(worker._fallback_completions(request), list)

    def test_jedi_failure_returns_empty_list(self, monkeypatch):
        """A fallback failure never propagates."""
        import jedi

        monkeypatch.setattr(
            jedi,
            "Script",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("jedi failed")),
        )
        worker = self._worker()
        request = _CompletionRequest(1, "value", 0, 0, None)

        assert worker._fallback_completions(request) == []
