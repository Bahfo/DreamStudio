"""Tests for the threaded file-analysis pipeline and status-bar spinner.

Covers:
- ``CircularProgressBar`` spin start/stop behaviour
- ``StatusBar`` analysis-spinner visibility and reference counting
- ``_AnalysisWorker`` off-thread computation of highlights + folds
- ``AnalysisManager`` stale-result dropping and signal emission
- ``CodeEditor`` emitting ``analysis_started`` / ``analysis_finished``
- ``DreamTabbedEditor`` wiring the spinner into the status bar
"""

import time
import types

import pytest
from PyQt6.QtGui import QColor
from PyQt6.QtTest import QSignalSpy, QTest

from editor.Ironica.language_engine import BaseLanguageProvider


def _wait_for(predicate, timeout_ms=5000):
    """Poll *predicate* while spinning the Qt event loop."""
    deadline = time.monotonic() + timeout_ms / 1000
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(50)
    return predicate()


class _AnalysisProvider(BaseLanguageProvider):
    """Dummy provider returning a fixed highlight + fold region."""

    def get_hover_hint(self, text, line, col):
        return None

    def get_definition_location(self, text, line, col):
        return None

    def format_source(self, source_code):
        return source_code

    def get_semantic_highlights(self, text):
        return [(0, 4, "#FF0000")]

    def has_folding(self):
        return True

    def get_fold_regions(self, text):
        from editor.Ironica.utils.folding import FoldRegion

        return [FoldRegion(start_line=0, end_line=2, kind="function")]


class _NoAnalysisProvider(BaseLanguageProvider):
    """Provider that supports neither overlays nor folding."""

    def get_hover_hint(self, text, line, col):
        return None

    def get_definition_location(self, text, line, col):
        return None

    def format_source(self, source_code):
        return source_code


def _register_provider(language_registry, provider):
    """Register *provider* under a fixed test language config."""
    language_registry.register_language_dict(
        {
            "lang": "test_lang",
            "extensions": ["tl"],
            "styles": {"keyword": "#FF0000"},
            "keywords": {"keyword": ["def"]},
        },
        provider_instance=provider,
    )


class TestCircularProgressBar:
    """Spin-mode behaviour of the circular progress widget."""

    def test_starts_and_stops_spinning(self, qapp_instance):
        from editor.widgets.QCircularProgressBar import CircularProgressBar

        bar = CircularProgressBar(
            bg_color=QColor("#333333"), fg_color=QColor("#FFFFFF"), diameter=16
        )
        try:
            assert not bar.is_spinning()
            assert not bar._spin_timer.isActive()

            bar.start()
            assert bar.is_spinning()
            assert bar._spin_timer.isActive()

            bar.start()  # idempotent
            assert bar.is_spinning()

            bar.stop()
            assert not bar.is_spinning()
            assert not bar._spin_timer.isActive()
        finally:
            bar.deleteLater()

    def test_fixed_size_follows_diameter(self, qapp_instance):
        from editor.widgets.QCircularProgressBar import CircularProgressBar

        bar = CircularProgressBar(
            bg_color=QColor("#333333"),
            fg_color=QColor("#FFFFFF"),
            diameter=18,
        )
        try:
            assert bar.width() == 18
            assert bar.height() == 18
        finally:
            bar.deleteLater()


class TestStatusBarSpinner:
    """Status-bar analysis spinner visibility and ref counting."""

    def test_spinner_show_hide_and_refcount(self, qapp_instance, monkeypatch):
        import editor.base.statusBar as statusbar_module

        fake_repo = types.SimpleNamespace(
            working_tree_dir="/tmp",
            active_branch=types.SimpleNamespace(name="main"),
        )
        monkeypatch.setattr(
            statusbar_module, "return_repository", lambda path: fake_repo
        )

        status = statusbar_module.StatusBar(None, "/tmp")
        try:
            assert status.analysis_progress_container.isHidden()

            status.start_analysis_spinner()
            assert not status.analysis_progress_container.isHidden()
            assert status.analysis_spinner.is_spinning()
            assert status.analysis_label.text() == "Analyzing file contents"

            status.start_analysis_spinner("Analyzing x")  # second editor
            status.stop_analysis_spinner()
            assert not status.analysis_progress_container.isHidden()
            assert status.analysis_label.text() == "Analyzing x"

            status.stop_analysis_spinner()
            assert status.analysis_progress_container.isHidden()
            assert not status.analysis_spinner.is_spinning()
        finally:
            status.deleteLater()


class TestAnalysisWorker:
    """Direct computation of highlights + folds off the main thread."""

    def test_analyze_computes_both(self, qapp_instance):
        from editor.Ironica.analysis_worker import _AnalysisWorker

        highlights, fold_regions = _AnalysisWorker._analyze(
            _AnalysisProvider(), "def foo():\n    pass\n"
        )
        assert highlights == [(0, 4, "#FF0000")]
        assert len(fold_regions) == 1
        assert fold_regions[0].start_line == 0

    def test_analyze_skips_unsupported_provider(self, qapp_instance):
        from editor.Ironica.analysis_worker import _AnalysisWorker

        highlights, fold_regions = _AnalysisWorker._analyze(
            _NoAnalysisProvider(), "plain text\n"
        )
        assert highlights is None
        assert fold_regions is None


class TestAnalysisManager:
    """Stale-result dropping and finished signalling."""

    def test_stale_results_are_dropped(self, qapp_instance, language_registry):
        from editor.Ironica.code_editor import CodeEditor

        _register_provider(language_registry, _AnalysisProvider())
        editor = CodeEditor(language="test_lang")
        try:
            manager = editor._analysis_manager
            editor._analysis_active = True

            manager._request_counter = 5
            manager._apply_results(4, [(0, 1, "#FF0000")], None)
            assert editor._analysis_active is True  # stale — no finish

            manager._apply_results(5, [(0, 1, "#FF0000")], [])
            assert editor._analysis_active is False  # current — finished
        finally:
            editor.deleteLater()


class TestAnalysisWorkerRemote:
    """Subprocess (remote) path of ``_AnalysisWorker`` and the
    in-process fallback when the server is unavailable."""

    def _make_manager(self, editor):
        from editor.Ironica.analysis_worker import AnalysisManager

        return AnalysisManager(editor)

    def test_remote_payload_and_results(self, qapp_instance, monkeypatch):
        from PyQt6.QtTest import QSignalSpy

        from editor.Ironica import analysis_worker as aw

        received = {}

        class _FakeProcess:
            def request(self, payload):
                received["payload"] = payload
                return ("analysis", payload[1], [(0, 4, "#FF0000")], [])

            def shutdown(self):
                pass

        monkeypatch.setattr(aw, "AnalysisProcess", lambda: _FakeProcess())

        provider = _AnalysisProvider()
        provider.remote_analysis = True
        editor = _FakeEditor()
        manager = self._make_manager(editor)
        try:
            spy = QSignalSpy(manager._results_ready)
            manager._worker.process(
                7,
                "def foo():\n    pass\n",
                provider,
                {"lang": "test_lang"},
                "dark",
            )

            assert _wait_for(lambda: len(spy) > 0), "remote analysis result was not emitted"
            assert received["payload"][0] == "analysis"
            assert received["payload"][1] == 7
            assert received["payload"][2] == "def foo():\n    pass\n"
            assert received["payload"][3] == {"lang": "test_lang"}
            assert received["payload"][4] == "dark"

            rid, highlights, folds = spy[0]
            assert rid == 7
            assert highlights == [(0, 4, "#FF0000")]
            assert folds == []
        finally:
            manager.shutdown()

    def test_in_process_fallback_on_server_failure(
        self, qapp_instance, monkeypatch
    ):
        from PyQt6.QtTest import QSignalSpy

        from editor.Ironica import analysis_worker as aw

        class _BrokenProcess:
            def request(self, payload):
                raise aw.AnalysisProcessError("boom")

            def shutdown(self):
                pass

        monkeypatch.setattr(aw, "AnalysisProcess", lambda: _BrokenProcess())

        provider = _AnalysisProvider()
        provider.remote_analysis = True
        manager = self._make_manager(_FakeEditor())
        try:
            spy = QSignalSpy(manager._results_ready)
            manager._worker.process(3, "def foo():\n    pass\n", provider, None, None)

            assert _wait_for(lambda: len(spy) > 0), "fallback analysis result was not emitted"
            rid, highlights, folds = spy[0]
            assert highlights == [(0, 4, "#FF0000")]  # provider's own result
            assert len(folds) == 1
        finally:
            manager.shutdown()

    def test_latest_request_wins(self, qapp_instance, monkeypatch, language_registry):
        from PyQt6.QtTest import QSignalSpy

        from editor.Ironica import analysis_worker as aw
        from editor.Ironica.code_editor import CodeEditor

        class _SlowProcess:
            def request(self, payload):
                rid, source = payload[1], payload[2]
                if rid == 1:
                    time.sleep(0.3)
                colour = "#FF0000" if source == "A" else "#00FF00"
                return ("analysis", rid, [(0, 1, colour)], [])

            def shutdown(self):
                pass

        monkeypatch.setattr(aw, "AnalysisProcess", lambda: _SlowProcess())

        provider = _AnalysisProvider()
        provider.remote_analysis = True
        _register_provider(language_registry, provider)
        editor = CodeEditor(language="test_lang")
        try:
            applied = []
            editor._apply_semantic_overlays = lambda h: applied.append(list(h))

            manager = editor._analysis_manager
            manager.request_analysis("A")  # request id 1 — slow
            manager.request_analysis("B")  # request id 2 — supersedes id 1

            deadline = time.monotonic() + 5
            while not applied and time.monotonic() < deadline:
                QTest.qWait(50)
            QTest.qWait(100)  # give any late stale result a chance to land

            # Only the newest buffer (B) may ever reach the editor.
            assert applied == [[(0, 1, "#00FF00")]]
        finally:
            editor.deleteLater()

    def test_request_analysis_resolves_config_and_theme(
        self, qapp_instance, language_registry
    ):
        from editor.Ironica.code_editor import CodeEditor

        _register_provider(language_registry, _AnalysisProvider())
        editor = CodeEditor(language="test_lang")
        try:
            manager = editor._analysis_manager
            captured = {}

            def fake_process(rid, source, provider, config, theme_name):
                captured["rid"] = rid
                captured["source"] = source
                captured["config"] = config
                captured["theme_name"] = theme_name

            manager._worker.process = fake_process

            manager.request_analysis("def foo():\n    pass\n")
            assert captured["config"]["lang"] == "test_lang"
            assert captured["theme_name"] == "dark"
            assert captured["source"] == "def foo():\n    pass\n"

            first_rid = captured["rid"]
            manager.request_analysis("x = 1\n")
            assert captured["rid"] == first_rid + 1  # counter bumped per submit

            manager.invalidate()
            manager.request_analysis("y = 2\n")
            assert captured["rid"] > first_rid + 1
        finally:
            editor.deleteLater()


class _FakeEditor:
    """Minimal editor surface used by ``AnalysisManager._apply_results``."""

    def _apply_semantic_overlays(self, highlights):
        pass

    def _apply_fold_regions(self, fold_regions):
        pass

    def _on_analysis_finished(self):
        pass


class TestCodeEditorAnalysisSignals:
    """End-to-end threaded analysis through a ``CodeEditor``."""

    def test_emits_started_and_finished(self, qapp_instance, language_registry):
        from editor.Ironica.code_editor import CodeEditor

        _register_provider(language_registry, _AnalysisProvider())
        editor = CodeEditor(language="test_lang")
        try:
            started = QSignalSpy(editor.analysis_started)
            finished = QSignalSpy(editor.analysis_finished)

            applied = []
            editor._apply_semantic_overlays = lambda highlights: applied.append(
                list(highlights)
            )

            editor.setText("def foo():\n    pass\n")
            editor._import_highlight_timer.stop()
            editor._fold_recompute_timer.stop()

            editor._apply_semantic_indicators()

            assert editor._analysis_active is True
            assert len(started) >= 1
            assert finished.wait(5000), "analysis_finished was not emitted"
            assert editor._analysis_active is False

            assert applied == [[(0, 4, "#FF0000")]]

            folds = editor._fold_manager.get_fold_regions()
            assert len(folds) == 1
            assert folds[0].start_line == 0
        finally:
            editor.deleteLater()

    def test_emits_started_and_finished_for_folds(self, qapp_instance, language_registry):
        from editor.Ironica.code_editor import CodeEditor

        _register_provider(language_registry, _AnalysisProvider())
        editor = CodeEditor(language="test_lang")
        try:
            started = QSignalSpy(editor.analysis_started)
            finished = QSignalSpy(editor.analysis_finished)

            editor.setText("def foo():\n    pass\n")
            editor._import_highlight_timer.stop()
            editor._fold_recompute_timer.stop()

            editor._recompute_folds()

            assert editor._analysis_active is True
            assert len(started) >= 1
            assert finished.wait(5000), "analysis_finished was not emitted"
            assert editor._analysis_active is False

            folds = editor._fold_manager.get_fold_regions()
            assert len(folds) == 1
            assert folds[0].start_line == 0
        finally:
            editor.deleteLater()

    def test_no_analysis_without_provider(self, qapp_instance):
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor()
        try:
            editor.setText("plain text\n")
            editor._recompute_folds()
            editor._apply_semantic_indicators()
            QTest.qWait(100)
            assert editor._analysis_active is False
        finally:
            editor.deleteLater()


class TestFoldDisplayTextCache:
    """The fold-display-text cache prevents the O(n^2) UI freeze.

    Re-sending ``SCI_TOGGLEFOLDSHOWTEXT`` on an active fold header costs
    an O(document) fold recalculation per line; unchanged calls must be
    skipped so repeated analysis applies stay cheap on large files.
    """

    def test_unchanged_calls_are_skipped(self, qapp_instance):
        from editor.Ironica.code_editor import CodeEditor

        editor = CodeEditor()
        try:
            editor.setText("import os\nimport sys\n")
            calls = []

            original = editor.SendScintilla

            def counting(msg, *args, **kwargs):
                calls.append(msg)
                return original(msg, *args, **kwargs)

            editor.SendScintilla = counting

            editor.set_custom_import_fold_text(0, 2)
            first = len(calls)
            assert first > 0

            editor.set_custom_import_fold_text(0, 2)  # unchanged → skip
            assert len(calls) == first

            editor.set_custom_import_fold_text(0, 3)  # changed → applied
            assert len(calls) > first
        finally:
            editor.deleteLater()

    def test_fold_regions_apply_text_before_levels(self, qapp_instance):
        from editor.Ironica.code_editor import CodeEditor

        events = []

        class _OrderProvider:
            def has_folding(self):
                return True

            def post_fold_setup(self, editor, regions):
                events.append("text")

        editor = CodeEditor()
        try:
            editor.current_lang = "test_lang"
            editor.current_provider = _OrderProvider()
            editor._fold_manager.set_fold_regions = (
                lambda regions: events.append("levels")
            )

            editor._apply_fold_regions([object()])
            assert events == ["text", "levels"]
        finally:
            editor.deleteLater()


class _FakeStatusBar:
    """Records start/stop calls for the spinner wiring test."""

    def __init__(self):
        self.started = 0
        self.stopped = 0

    def start_analysis_spinner(self):
        self.started += 1

    def stop_analysis_spinner(self):
        self.stopped += 1


class TestTabEditorWiring:
    """The tab editor forwards analysis signals to the status bar."""

    def test_spinner_wired_on_open(self, qapp_instance, language_registry, tmp_path):
        from PyQt6.QtWidgets import QVBoxLayout, QWidget

        from editor.Ironica.tab_editor import DreamTabbedEditor

        _register_provider(language_registry, _AnalysisProvider())

        parent = QWidget()
        parent.currentDirectory = "/tmp"
        status = _FakeStatusBar()
        parent.status_bar = status

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        p = tmp_path / "a.tl"
        p.write_text("def foo():\n    pass\n", encoding="utf-8")

        tabs.add_new_editor(
            file_name="a.tl", file_path=str(p), language="test_lang"
        )
        QTest.qWait(500)

        assert status.started >= 1
        assert status.stopped >= 1

        parent.deleteLater()

    def test_no_wiring_without_status_bar(self, qapp_instance, language_registry):
        from PyQt6.QtWidgets import QVBoxLayout, QWidget

        from editor.Ironica.tab_editor import DreamTabbedEditor

        _register_provider(language_registry, _AnalysisProvider())

        parent = QWidget()
        parent.currentDirectory = "/tmp"
        parent.status_bar = None

        layout = QVBoxLayout(parent)
        tabs = DreamTabbedEditor(parent)
        layout.addWidget(tabs)

        tabs.add_new_editor(content="def foo():\n    pass\n", language="test_lang")
        QTest.qWait(200)

        parent.deleteLater()
