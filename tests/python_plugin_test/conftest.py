"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared fixtures and reporting hooks for the Python-language-plugin test suite.

Performance tests record wall-clock samples through the ``timing_recorder``
fixture. The samples are aggregated and printed in pytest's terminal summary;
they are never converted into pass/fail assertions.
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict

import pytest
from PyQt6.QtCore import QObject, pyqtSignal


class FakeEditor(QObject):
    """Minimal editor double exposing the surface the plugin managers use."""

    textChanged = pyqtSignal()

    def __init__(self, source: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source = source
        self._autocompletion_widget = None
        self.diagnostic_ranges: list = []
        self.diagnostic_underlines: list = []
        self.clear_calls = 0
        self.range_setter_calls = 0
        self.range_setter_error: Exception | None = None

    def text(self) -> str:
        """Return the current buffer contents."""
        return self._source

    def set_source(self, source: str) -> None:
        """Replace the buffer and emit ``textChanged`` once."""
        self._source = source
        self.textChanged.emit()

    def set_diagnostic_ranges(self, ranges) -> None:
        """Record batched diagnostic ranges (new-style editor surface)."""
        if self.range_setter_error is not None:
            raise self.range_setter_error
        self.range_setter_calls += 1
        self.diagnostic_ranges = list(ranges)

    def clear_diagnostic_underlines(self) -> None:
        """Record legacy underline clearing."""
        self.clear_calls += 1
        self.diagnostic_underlines = []

    def add_diagnostic_underline(self, line, start_col, end_col, color_hex) -> None:
        """Record a legacy per-diagnostic underline."""
        self.diagnostic_underlines.append((line, start_col, end_col, color_hex))


class LegacyFakeEditor(FakeEditor):
    """Editor double without the batched diagnostic setter."""

    set_diagnostic_ranges = None


class TimingRecorder:
    """Collects wall-clock samples for the terminal summary."""

    def __init__(self) -> None:
        self._samples: list[tuple[str, str, float, str]] = []

    def record(
        self, service: str, phase: str, seconds: float, detail: str = ""
    ) -> None:
        """Record one measured sample in seconds."""
        self._samples.append((service, phase, seconds, detail))

    def time_call(
        self,
        service: str,
        phase: str,
        func,
        repeats: int = 1,
        detail: str = "",
    ):
        """Run *func* *repeats* times, record each sample, and return its result."""
        result = None
        for _ in range(repeats):
            started = time.perf_counter()
            result = func()
            self.record(service, phase, time.perf_counter() - started, detail)
        return result

    def groups(self) -> dict[tuple[str, str], list[float]]:
        """Group recorded seconds by ``(service, phase)``."""
        grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
        for service, phase, seconds, _detail in self._samples:
            grouped[(service, phase)].append(seconds)
        return grouped

    def __len__(self) -> int:
        return len(self._samples)


_RECORDER = TimingRecorder()


@pytest.fixture(scope="session")
def timing_recorder() -> TimingRecorder:
    """Return the session-wide performance timing recorder."""
    return _RECORDER


@pytest.fixture
def fake_editor() -> FakeEditor:
    """Provide a minimal editor double for diagnostic/completion managers."""
    editor = FakeEditor()
    yield editor
    editor.deleteLater()


@pytest.fixture
def legacy_fake_editor() -> FakeEditor:
    """Provide an editor double without the batched diagnostic setter."""
    editor = LegacyFakeEditor()
    yield editor
    editor.deleteLater()


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Print recorded performance samples without judging them."""
    if not _RECORDER:
        return

    groups = _RECORDER.groups()
    terminalreporter.write_sep(
        "=", "Python plugin performance timings (wall clock; no pass/fail thresholds)"
    )
    header = (
        f"{'service':<28} {'phase':<24} {'runs':>4} "
        f"{'median ms':>10} {'min ms':>10} {'max ms':>10}"
    )
    terminalreporter.write_line(header)
    terminalreporter.write_line("-" * len(header))
    for (service, phase), samples in sorted(groups.items()):
        milliseconds = [value * 1000.0 for value in samples]
        terminalreporter.write_line(
            f"{service:<28} {phase:<24} {len(milliseconds):>4} "
            f"{statistics.median(milliseconds):>10.1f} "
            f"{min(milliseconds):>10.1f} "
            f"{max(milliseconds):>10.1f}"
        )
    terminalreporter.write_line("")
