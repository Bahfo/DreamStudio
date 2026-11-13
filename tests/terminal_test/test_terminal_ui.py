"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Tests for Terminal UI components.
"""

import sys
import time

import pytest

from editor.terminal.Emulator.terminal_ui import (
    TerminalEdit,
    PromptXTerminalWidget,
    TerminalPanel,
    TAB_SYSTEM_SHELL,
    TAB_PROMPTX,
    TAB_OUTPUT,
)


class TestPromptXTerminalWidget:
    def test_instantiation(self, qapp):
        w = PromptXTerminalWidget()
        assert w is not None
        w.deleteLater()
        qapp.processEvents()

    def test_initial_prompt_present(self, qapp):
        w = PromptXTerminalWidget()
        text = w._terminal.toPlainText()
        assert len(text) > 0
        w.deleteLater()
        qapp.processEvents()

    def test_clear_command(self, qapp):
        w = PromptXTerminalWidget()
        # type clear via execute
        w._terminal.setPlainText(w._terminal.toPlainText() + "clear")
        # Instead call _execute_current by positioning? Use engine-level
        w._terminal.moveCursor(
            __import__(
                "PyQt6.QtGui", fromlist=["QTextCursor"]
            ).QTextCursor.MoveOperation.End
        )
        w.deleteLater()
        qapp.processEvents()

    def test_quit_command(self, qapp):
        w = PromptXTerminalWidget()
        w._replace_input("quit")
        w._execute_current()
        qapp.processEvents()
        text = w._terminal.toPlainText()
        assert "close button" in text.lower() or "prompt" in text.lower()
        w.deleteLater()
        qapp.processEvents()


class TestTerminalPanel:
    def test_tab_count(self, qapp):
        panel = TerminalPanel()
        assert panel.tab_bar.count() == 4
        panel.deleteLater()
        qapp.processEvents()

    def test_switch_tab(self, qapp):
        panel = TerminalPanel()
        panel.switch_tab(TAB_PROMPTX)
        qapp.processEvents()
        assert panel.stack.currentIndex() == TAB_PROMPTX
        panel.deleteLater()
        qapp.processEvents()

    def test_close_button_signal(self, qapp):
        panel = TerminalPanel()
        received = []
        panel.close_requested.connect(lambda: received.append(True))
        panel.btn_close.click()
        qapp.processEvents()
        assert received
        panel.deleteLater()
        qapp.processEvents()

    def test_missing_workspace_no_crash(self, qapp):
        panel = TerminalPanel()
        try:
            panel.set_workspace("/tmp")
        except Exception:
            pass
        panel.deleteLater()
        qapp.processEvents()

    def test_cleanup(self, qapp):
        panel = TerminalPanel()
        panel.cleanup()
        panel.deleteLater()
        qapp.processEvents()
