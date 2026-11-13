"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Tests for OutputsWidget.
"""

import sys

import pytest

from editor.terminal.OutputsWidget.output_widget import OutputWidget


class TestOutputWidget:
    def test_append_and_clear(self, qapp):
        w = OutputWidget()
        w.append_text("Hello")
        w.append_text(" World")
        assert "Hello World" in w._text.toPlainText()
        w.clear()
        assert w._text.toPlainText() == ""
        w.deleteLater()
        qapp.processEvents()

    def test_large_output(self, qapp):
        w = OutputWidget()
        for _ in range(1000):
            w.append_text("line\n")
        assert w._text.toPlainText().count("line") == 1000
        w.deleteLater()
        qapp.processEvents()

    def test_unicode(self, qapp):
        w = OutputWidget()
        w.append_text("héllo 🎉")
        assert "héllo" in w._text.toPlainText()
        w.deleteLater()
        qapp.processEvents()
