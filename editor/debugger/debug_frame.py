"""
(C) COPYRIGHT 2026 - EXcellent TechStacks, All Rights Reserved.

Debug Control Frame: Inline toolbar widget with debugging action buttons
(Stop, Continue, Restart, Step Over, Step Into, Step Out) displayed
inside the options bar during an active debug session.
"""

import os

from PyQt6.QtWidgets import QFrame, QHBoxLayout

from editor.widgets.QToolButton import ToolbarButton


class DebugControlFrame(QFrame):
    """A compact horizontal frame containing debug action buttons.

    Hidden by default. Shown only when a debug session is active.
    Each button delegates its action to the attached ``DebugSession``.
    """

    _ASSET_BASE = os.path.join(
        os.path.dirname(__file__), "..", "..", "assets", "system"
    )

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("DebugControlFrame")
        self.setStyleSheet("""
            DebugControlFrame {
                background-color: rgba(255, 152, 0, 0.08);
                border: 1px solid rgba(255, 152, 0, 0.25);
                border-radius: 4px;
            }
        """)
        self.setFixedHeight(30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        self._session = None

        self.btn_continue = self._make_btn(
            "step_forward.png", "Continue (F5)", "_on_continue"
        )
        self.btn_step_over = self._make_btn(
            "step_forward.png", "Step Over (F10)", "_on_step_over"
        )
        self.btn_step_into = self._make_btn(
            "run.png", "Step Into (F11)", "_on_step_into"
        )
        self.btn_step_out = self._make_btn(
            "step_back.png", "Step Out (Shift+F11)", "_on_step_out"
        )
        self.btn_restart = self._make_btn(
            "replay.png", "Restart (Ctrl+Shift+F5)", "_on_restart"
        )
        self.btn_stop = self._make_btn(
            "stop.png", "Stop (Shift+F5)", "_on_stop"
        )

        for btn in (
            self.btn_continue,
            self.btn_step_over,
            self.btn_step_into,
            self.btn_step_out,
            self.btn_restart,
            self.btn_stop,
        ):
            layout.addWidget(btn)

        self.disable_controls()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    def _make_btn(self, icon_name, tooltip, handler_name):
        icon_path = os.path.join(self._ASSET_BASE, icon_name)
        btn = ToolbarButton(
            icon_path=icon_path,
            tooltip=tooltip,
            fixed_size=(28, 26),
            icon_size=(16, 16),
        )
        btn.clicked.connect(getattr(self, handler_name))
        return btn

    # ------------------------------------------------------------------
    # Session binding
    # ------------------------------------------------------------------

    def set_session(self, session):
        self._session = session

    # ------------------------------------------------------------------
    # Button state management
    # ------------------------------------------------------------------

    def enable_controls(self):
        for btn in (
            self.btn_continue,
            self.btn_step_over,
            self.btn_step_into,
            self.btn_step_out,
            self.btn_restart,
            self.btn_stop,
        ):
            btn.setEnabled(True)

    def disable_controls(self):
        for btn in (
            self.btn_continue,
            self.btn_step_over,
            self.btn_step_into,
            self.btn_step_out,
            self.btn_restart,
            self.btn_stop,
        ):
            btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Button handlers (delegate to session)
    # ------------------------------------------------------------------

    def _on_continue(self):
        if self._session:
            self._session.continue_execution()

    def _on_step_over(self):
        if self._session:
            self._session.step_over()

    def _on_step_into(self):
        if self._session:
            self._session.step_into()

    def _on_step_out(self):
        if self._session:
            self._session.step_out()

    def _on_restart(self):
        if self._session:
            self._session.restart()

    def _on_stop(self):
        if self._session:
            self._session.stop()
