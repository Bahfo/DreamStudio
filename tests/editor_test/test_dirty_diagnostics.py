"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the dirty flag driving the diagnostic store merge policy.
"""

import pytest


class TestDirtyDrivesDiagnostics:
    """Tests for the dirty flag driving the diagnostic store merge policy."""

    @staticmethod
    def _problem(message, code="E101", severity="error", path="test.py", line=1):
        from editor.analysis.types import Problem

        return Problem(
            file_path=path,
            severity=severity,
            message=message,
            line=line,
            column=0,
            source="test",
            code=code,
            end_line=line,
            end_column=10,
        )

    def test_dirty_buffer_shows_live_only(self, qapp):
        """A dirty buffer hides stale on-disk diagnostics (invariant D3)."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        store.set_disk_results(
            [("test.py", [self._problem("Disk error", "E101", line=1)])],
            "disk_builtin",
        )
        store.set_disk_results(
            [("test.py", [self._problem("Ruff error", "RUF001", line=2)])],
            "disk_external:ruff",
        )
        store.set_live_results("test.py", 1, [self._problem("Live error", "L101", line=3)])

        store.mark_dirty("test.py")
        problems = store.problems_for("test.py")

        assert [p.code for p in problems] == ["L101"]

    def test_clean_buffer_shows_merged_results(self, qapp):
        """A clean buffer merges live, builtin, and external buckets (D4)."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        store.set_disk_results(
            [("test.py", [self._problem("Disk error", "E101", line=1)])],
            "disk_builtin",
        )
        store.set_disk_results(
            [("test.py", [self._problem("Ruff error", "RUF001", line=2)])],
            "disk_external:ruff",
        )
        store.set_live_results("test.py", 1, [self._problem("Live error", "L101", line=3)])

        problems = store.problems_for("test.py")

        assert {p.code for p in problems} == {"E101", "RUF001", "L101"}

    def test_stale_revision_is_discarded(self, qapp):
        """Older buffer revisions never overwrite newer ones (invariant D5)."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        revision_one = store.note_buffer_change("test.py")
        store.set_live_results("test.py", revision_one, [self._problem("Old", "L101")])

        revision_two = store.note_buffer_change("test.py")
        store.set_live_results("test.py", revision_two, [self._problem("New", "L102")])

        # A delayed result from the older buffer revision must be ignored.
        store.set_live_results("test.py", revision_one, [self._problem("Stale", "L100")])

        problems = store.problems_for("test.py")

        assert [p.code for p in problems] == ["L102"]

    def test_mark_clean_reports_state_change(self, qapp):
        """mark_clean reports whether the path was dirty."""
        from editor.analysis.diagnostic_store import DiagnosticStore

        store = DiagnosticStore()
        store.mark_dirty("test.py")

        assert store.is_dirty("test.py") is True
        assert store.mark_clean("test.py") is True
        assert store.is_dirty("test.py") is False
        assert store.mark_clean("test.py") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])