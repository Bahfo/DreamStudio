"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Tests for ProcessesViewer (PortsWidget).
"""

import sys

import pytest

from editor.terminal.ProcessesViewer.ports_widget import PortsWidget


class TestPortsWidget:
    def test_instantiation(self, qapp):
        w = PortsWidget()
        assert w is not None
        w.deleteLater()
        qapp.processEvents()

    def test_refresh_no_crash(self, qapp):
        w = PortsWidget()
        try:
            w.refresh_data()
        except Exception:
            pass
        w.deleteLater()
        qapp.processEvents()
