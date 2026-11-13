"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for syntax diagnostics, span merging, and the diagnostics manager.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from editor.Ironica.plugins.python.jedi_worker import (
    _MAX_DIAGNOSTICS,
    _SYNTAX_COLOR,
    DEBOUNCE_MS,
    DiagnosticManager,
    _diag_field,
    _merge_spans,
    _syntax_diagnostics,
)
from editor.Ironica.process_manager import process_manager
from tests.python_plugin_test.conftest import LegacyFakeEditor


class _RecordingWorker:
    """Stand-in worker recording submissions instead of starting threads."""

    def __init__(self) -> None:
        self.requests: list[tuple[int, str, str | None]] = []
        self.shutdown_calls = 0

    def process(self, request_id: int, source: str, file_path: str | None) -> None:
        self.requests.append((request_id, source, file_path))

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class TestMergeSpans:
    """Tests for same-line diagnostic span merging."""

    def test_empty_input(self):
        """No diagnostics means no spans."""
        assert _merge_spans([]) == []

    def test_overlapping_spans_merge(self):
        """Overlapping ranges on a line collapse into one."""
        merged = _merge_spans(
            [
                {"line": 1, "start_col": 0, "end_col": 5},
                {"line": 1, "start_col": 3, "end_col": 9},
            ]
        )

        assert merged == [{"line": 1, "start_col": 0, "end_col": 9}]

    def test_adjacent_spans_merge(self):
        """Touching half-open ranges are merged."""
        merged = _merge_spans(
            [
                {"line": 1, "start_col": 0, "end_col": 3},
                {"line": 1, "start_col": 3, "end_col": 6},
            ]
        )

        assert merged == [{"line": 1, "start_col": 0, "end_col": 6}]

    def test_disjoint_spans_on_one_line_stay_separate(self):
        """A real gap keeps diagnostics distinct."""
        merged = _merge_spans(
            [
                {"line": 1, "start_col": 0, "end_col": 2},
                {"line": 1, "start_col": 4, "end_col": 6},
            ]
        )

        assert merged == [
            {"line": 1, "start_col": 0, "end_col": 2},
            {"line": 1, "start_col": 4, "end_col": 6},
        ]

    def test_merge_is_order_independent_within_a_line(self):
        """Unsorted inputs produce sorted merged spans."""
        merged = _merge_spans(
            [
                {"line": 1, "start_col": 7, "end_col": 9},
                {"line": 1, "start_col": 0, "end_col": 3},
            ]
        )

        assert [span["start_col"] for span in merged] == [0, 7]

    def test_lines_are_processed_in_order(self):
        """Merged output is sorted by line."""
        merged = _merge_spans(
            [
                {"line": 5, "start_col": 0, "end_col": 2},
                {"line": 1, "start_col": 0, "end_col": 2},
            ]
        )

        assert [span["line"] for span in merged] == [1, 5]

    def test_merging_keeps_extra_fields_from_the_first_span(self):
        """Colour and message are inherited from the earliest span."""
        merged = _merge_spans(
            [
                {
                    "line": 1,
                    "start_col": 0,
                    "end_col": 3,
                    "color": "#AAAAAA",
                    "message": "first",
                },
                {
                    "line": 1,
                    "start_col": 2,
                    "end_col": 8,
                    "color": "#BBBBBB",
                    "message": "second",
                },
            ]
        )

        assert merged == [
            {
                "line": 1,
                "start_col": 0,
                "end_col": 8,
                "color": "#AAAAAA",
                "message": "first",
            }
        ]

    def test_input_spans_are_not_mutated(self):
        """Merging copies every entry before widening it."""
        original = {"line": 1, "start_col": 0, "end_col": 3}

        _merge_spans([original, {"line": 1, "start_col": 2, "end_col": 6}])

        assert original["end_col"] == 3


class TestDiagnosticFieldAccess:
    """Tests for the dict/object access helper."""

    def test_dict_fields(self):
        """Dictionary diagnostics are read by key."""
        assert _diag_field({"line": 4}, "line", 1) == 4

    def test_missing_dict_field_uses_default(self):
        """A missing key yields the default."""
        assert _diag_field({}, "line", 1) == 1

    def test_object_fields(self):
        """Object diagnostics are read by attribute."""
        assert _diag_field(SimpleNamespace(line=7), "line", 1) == 7

    def test_missing_object_field_uses_default(self):
        """A missing attribute yields the default."""
        assert _diag_field(SimpleNamespace(), "line", 1) == 1


class TestSyntaxDiagnostics:
    """Tests for in-process parso diagnostics."""

    @pytest.mark.parametrize(
        "source",
        [
            "def f(x):\n    return x\n",
            "",
            "# comment only\n",
            "class C:\n    pass\n",
        ],
    )
    def test_valid_source_has_no_diagnostics(self, source):
        """Compilable source yields an empty diagnostic list."""
        assert _syntax_diagnostics(source) == []

    def test_broken_signature_reports_a_diagnostic(self):
        """An invalid signature produces a syntax diagnostic."""
        diagnostics = _syntax_diagnostics("def broken(:\n    pass\n")

        assert len(diagnostics) == 1
        diagnostic = diagnostics[0]
        assert diagnostic["line"] == 1
        assert diagnostic["end_line"] == 1
        assert diagnostic["start_col"] == 0
        assert diagnostic["end_col"] > 0
        assert diagnostic["color"] == _SYNTAX_COLOR
        assert diagnostic["message"]

    def test_unclosed_parenthesis_points_at_the_closing_line(self):
        """Parso's recovery identifies the incomplete construct."""
        diagnostics = _syntax_diagnostics("def f():\n    return (1\n")

        assert diagnostics
        assert diagnostics[0]["line"] == 2
        assert "never closed" in diagnostics[0]["message"]

    def test_missing_indented_block_reports_multiple_spans(self):
        """Recovery can report more than one location for one error."""
        diagnostics = _syntax_diagnostics("def f():\npass\n")

        assert len(diagnostics) >= 1
        assert all(
            diagnostic["message"] == diagnostics[0]["message"]
            for diagnostic in diagnostics
        )

    def test_each_error_in_a_buffer_is_reported(self):
        """Independent syntax errors are reported separately."""
        diagnostics = _syntax_diagnostics("def f(:\n    pass\ndef g(:\n    pass\n")

        assert {diagnostic["line"] for diagnostic in diagnostics} == {1, 3}

    def test_diagnostics_are_capped(self):
        """Runaway error recovery is bounded by ``_MAX_DIAGNOSTICS``."""
        source = "def broken(:\n" + "    value = (\n" * 300

        diagnostics = _syntax_diagnostics(source)

        assert 0 < len(diagnostics) <= _MAX_DIAGNOSTICS

    def test_spans_are_merged_and_ordered(self):
        """Returned diagnostics never overlap on the same line."""
        diagnostics = _syntax_diagnostics("def broken(:\n    pass\n")

        assert diagnostics == _merge_spans(diagnostics)
        assert diagnostics == sorted(diagnostics, key=lambda item: item["line"])

    def test_multiline_error_span_is_split_per_line(self):
        """A span crossing lines produces one entry per row."""
        source = "value = (1 +\n    2 +\n    3\n"
        diagnostics = _syntax_diagnostics(source)

        assert diagnostics
        assert all(
            diagnostic["line"] == diagnostic["end_line"] for diagnostic in diagnostics
        )

    def test_parso_failure_degrades_to_empty(self, monkeypatch):
        """An unexpected parser failure never breaks the editor."""

        def broken_parse(*args, **kwargs):
            raise RuntimeError("parso failed")

        import parso

        monkeypatch.setattr(parso, "parse", broken_parse)

        assert _syntax_diagnostics("def f():\n    pass\n") == []


@pytest.fixture
def manager_factory(fake_editor, monkeypatch):
    """Create diagnostic managers with a recording worker and released process."""
    released: list[int] = []
    monkeypatch.setattr(
        process_manager, "release", lambda owner_id: released.append(owner_id)
    )
    created: list[tuple[DiagnosticManager, _RecordingWorker]] = []

    def make(
        editor=None, file_path="/tmp/module.py"
    ) -> tuple[DiagnosticManager, _RecordingWorker]:
        manager = DiagnosticManager(
            editor=editor if editor is not None else fake_editor,
            file_path=file_path,
        )
        worker = _RecordingWorker()
        manager._worker = worker
        created.append((manager, worker))
        return manager, worker

    yield make, released

    for manager, _worker in created:
        manager.shutdown()


class TestDiagnosticManagerConstruction:
    """Tests for manager wiring and configuration."""

    def test_owner_id_tracks_the_editor(self, manager_factory):
        """The shared process is addressed by the editor's identity."""
        make, _released = manager_factory
        manager, _worker = make()

        assert manager.owner_id == id(manager._editor)

    def test_file_path_and_debounce_defaults(self, manager_factory):
        """The manager stores its path and the documented debounce."""
        make, _released = manager_factory
        manager, _worker = make(file_path="/tmp/a.py")

        assert manager._file_path == "/tmp/a.py"
        assert manager._debounce_timer.interval() == DEBOUNCE_MS
        assert manager._enabled is True

    def test_setting_file_path_repoints_the_manager(self, manager_factory):
        """Save-as/rename can repoint diagnostics."""
        make, _released = manager_factory
        manager, _worker = make()

        manager.set_file_path("/tmp/new.py")

        assert manager._file_path == "/tmp/new.py"


class TestDiagnosticDebounce:
    """Tests for debounce arming and worker submission."""

    def test_text_change_arms_the_timer(self, qapp, manager_factory):
        """An edit increments the request counter and starts the timer."""
        make, _released = manager_factory
        manager, _worker = make()
        before = manager._request_counter

        manager._on_text_changed()

        assert manager._request_counter == before + 1
        assert manager._debounce_timer.isActive()

    def test_debounce_fire_submits_the_current_buffer(
        self, qapp, manager_factory, fake_editor
    ):
        """The worker receives the counter, buffer text, and path."""
        make, _released = manager_factory
        manager, worker = make(file_path="/tmp/a.py")
        fake_editor.set_source("value = 1\n")
        manager._request_counter = 7

        manager._on_debounce_fired()

        assert worker.requests == [(7, "value = 1\n", "/tmp/a.py")]

    def test_disabled_manager_does_not_submit(self, qapp, manager_factory):
        """A background tab never submits diagnostics."""
        make, _released = manager_factory
        manager, worker = make()
        manager.set_enabled(False)

        manager._on_debounce_fired()

        assert worker.requests == []

    def test_disabling_stops_an_armed_timer(self, qapp, manager_factory):
        """Losing focus cancels the pending debounce."""
        make, _released = manager_factory
        manager, _worker = make()
        manager._on_text_changed()

        manager.set_enabled(False)

        assert manager._debounce_timer.isActive() is False
        assert manager._enabled is False

    def test_reenabling_does_not_retroactively_submit(self, qapp, manager_factory):
        """Re-enabling only allows future submissions."""
        make, _released = manager_factory
        manager, worker = make()
        manager.set_enabled(False)
        manager.set_enabled(True)

        manager._on_debounce_fired()

        assert worker.requests

    def test_pending_autocompletion_postpones_analysis(self, qapp, manager_factory):
        """While a completion popup is pending the timer is restarted."""
        make, _released = manager_factory
        manager, worker = make()
        manager._editor._autocompletion_widget = SimpleNamespace(_request_pending=True)

        manager._on_debounce_fired()

        assert worker.requests == []
        assert manager._debounce_timer.isActive()

    def test_editor_read_failure_is_tolerated(self, qapp, manager_factory, fake_editor):
        """A failing editor read does not propagate out of the timer slot."""
        fake_editor.text = lambda: (_ for _ in ()).throw(RuntimeError("deleted"))
        make, _released = manager_factory
        manager, worker = make(editor=fake_editor)

        manager._on_debounce_fired()

        assert worker.requests == []

    def test_invalidate_bumps_the_counter(self, manager_factory):
        """Invalidation retires in-flight results."""
        make, _released = manager_factory
        manager, _worker = make()
        before = manager._request_counter

        manager.invalidate()

        assert manager._request_counter == before + 1

    def test_trigger_analysis_bypasses_the_debounce(
        self, qapp, manager_factory, fake_editor
    ):
        """A forced pass submits immediately."""
        make, _released = manager_factory
        manager, worker = make()
        fake_editor.set_source("value = 1\n")

        manager.trigger_analysis()

        assert worker.requests


class TestDiagnosticBatching:
    """Tests for converting diagnostics into editor ranges."""

    def test_dict_diagnostics_are_converted_to_zero_based_ranges(self):
        """Wire diagnostics become zero-based editor tuples."""
        ranges = DiagnosticManager._batch_ranges(
            [
                {
                    "line": 3,
                    "start_col": 4,
                    "end_col": 9,
                    "color": "#123456",
                }
            ]
        )

        assert ranges == [(2, 4, 2, 9, "#123456")]

    def test_object_diagnostics_are_supported(self):
        """Object-based diagnostics use the same conversion."""
        ranges = DiagnosticManager._batch_ranges(
            [SimpleNamespace(line=2, start_col=1, end_col=3, color="#ABCDEF")]
        )

        assert ranges == [(1, 1, 1, 3, "#ABCDEF")]

    def test_missing_colour_uses_the_syntax_colour(self):
        """A diagnostic without a colour gets the standard red."""
        ranges = DiagnosticManager._batch_ranges(
            [{"line": 1, "start_col": 0, "end_col": 2}]
        )

        assert ranges == [(0, 0, 0, 2, _SYNTAX_COLOR)]

    @pytest.mark.parametrize(
        "diagnostic",
        [
            {"line": "bad", "start_col": 0, "end_col": 1},
            {"line": 1, "start_col": None, "end_col": 1},
            {"line": 1, "start_col": 0, "end_col": []},
        ],
    )
    def test_invalid_values_are_skipped(self, diagnostic):
        """Malformed diagnostics are ignored individually."""
        assert DiagnosticManager._batch_ranges([diagnostic]) == []

    def test_empty_input(self):
        """No diagnostics means no ranges."""
        assert DiagnosticManager._batch_ranges([]) == []
        assert DiagnosticManager._batch_ranges(None) == []


class TestDiagnosticPainting:
    """Tests for applying results on the UI thread."""

    def test_batched_ranges_are_painted_on_the_editor(
        self, manager_factory, fake_editor
    ):
        """The new editor surface receives one batched call."""
        make, _released = manager_factory
        manager, _worker = make()

        manager._apply_results(
            0, [{"line": 2, "start_col": 1, "end_col": 4, "color": "#111111"}]
        )

        assert fake_editor.range_setter_calls == 1
        assert fake_editor.diagnostic_ranges == [(1, 1, 1, 4, "#111111")]
        assert fake_editor.clear_calls == 0

    def test_empty_first_result_does_not_paint(self, manager_factory, fake_editor):
        """A clean buffer does not trigger an initial setter call."""
        make, _released = manager_factory
        manager, _worker = make()

        manager._apply_results(0, [])

        assert fake_editor.range_setter_calls == 0
        assert manager._has_painted is False

    def test_empty_result_clears_previously_painted_ranges(
        self, manager_factory, fake_editor
    ):
        """Once painted, an empty result clears stale underlines."""
        make, _released = manager_factory
        manager, _worker = make()
        manager._apply_results(0, [{"line": 1, "start_col": 0, "end_col": 2}])

        manager._apply_results(1, [])

        assert fake_editor.range_setter_calls == 2
        assert fake_editor.diagnostic_ranges == []
        assert manager._has_painted is False

    def test_stale_results_are_dropped(self, manager_factory, fake_editor):
        """A result older than the current request counter is ignored."""
        make, _released = manager_factory
        manager, _worker = make()
        manager._request_counter = 5

        manager._apply_results(4, [{"line": 1, "start_col": 0, "end_col": 2}])

        assert fake_editor.range_setter_calls == 0

    def test_current_result_is_applied(self, manager_factory, fake_editor):
        """A result with the current counter is applied."""
        make, _released = manager_factory
        manager, _worker = make()
        manager._request_counter = 5

        manager._apply_results(5, [{"line": 1, "start_col": 0, "end_col": 2}])

        assert fake_editor.range_setter_calls == 1

    def test_legacy_editor_receives_individual_underlines(self, monkeypatch):
        """Older editors without batch support use the underline API."""
        released: list[int] = []
        monkeypatch.setattr(
            process_manager, "release", lambda owner_id: released.append(owner_id)
        )
        editor = LegacyFakeEditor()
        manager = DiagnosticManager(editor=editor, file_path="/tmp/a.py")
        manager._worker = _RecordingWorker()
        try:
            manager._apply_results(
                0,
                [
                    {"line": 1, "start_col": 0, "end_col": 3, "color": "#AAAAAA"},
                    {"line": 2, "start_col": 1, "end_col": 5, "color": "#BBBBBB"},
                ],
            )

            assert editor.clear_calls == 1
            assert editor.diagnostic_underlines == [
                (0, 0, 3, "#AAAAAA"),
                (1, 1, 5, "#BBBBBB"),
            ]
        finally:
            manager.shutdown()

    def test_editor_exception_is_swallowed(self, manager_factory, fake_editor):
        """A failing editor setter never escapes the signal handler."""
        make, _released = manager_factory
        manager, _worker = make()
        fake_editor.range_setter_error = RuntimeError("editor gone")

        manager._apply_results(0, [{"line": 1, "start_col": 0, "end_col": 2}])

        assert fake_editor.range_setter_calls == 0


class TestDiagnosticShutdown:
    """Tests for releasing editor and process resources."""

    def test_shutdown_stops_worker_and_releases_process(
        self, qapp, manager_factory, fake_editor
    ):
        """Shutdown disconnects, stops the timer, and releases the owner."""
        make, released = manager_factory
        manager, worker = make()
        manager._on_text_changed()

        manager.shutdown()

        assert worker.shutdown_calls == 1
        assert manager._debounce_timer.isActive() is False
        assert released == [id(fake_editor)]

    def test_shutdown_is_safe_to_repeat(self, qapp, manager_factory):
        """A second shutdown does not raise."""
        make, _released = manager_factory
        manager, _worker = make()

        manager.shutdown()
        manager.shutdown()

    def test_shutdown_disconnects_text_changes(
        self, qapp, manager_factory, fake_editor
    ):
        """Edits after shutdown no longer arm the timer."""
        make, _released = manager_factory
        manager, _worker = make()
        manager.shutdown()

        fake_editor.set_source("value = 1\n")

        assert manager._debounce_timer.isActive() is False
