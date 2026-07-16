"""
Vertical Menus API — panel activation manager for DreamStudio.

Panels are created once and kept alive in the QStackedWidget; their tab-bar
entries are shown/hidden on demand via QTabBar.setTabVisible().
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QSplitter, QWidget


class VerticalMenusAPI(QObject):
    """
    Panel activation/deactivation controller.

    Register each panel once with :meth:`register_panel`, then use
    :meth:`activate_panel` / :meth:`deactivate_panel` to show/hide tabs.

    Signals
    -------
    panel_visibility_changed(panel_id: str, visible: bool)
        Emitted whenever a panel tab is shown or hidden.
    """

    panel_visibility_changed = pyqtSignal(str, bool)

    _TITLES = {
        "solution_explorer": "Solution Explorer",
        "source_control": "Source Control",
        "properties": "Properties",
        "todo_search": "TODO Search",
    }

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._widgets: dict[str, QWidget] = {}
        self._tab_managers: dict[str, QWidget] = {}
        self._splitters: dict[str, tuple] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_panel(
        self,
        panel_id: str,
        widget: QWidget,
        tab_manager: QWidget,
        side: str,
        *,
        splitter: QSplitter | None = None,
        splitter_index: int = 0,
        default_width: int = 250,
    ) -> None:
        """
        Register a panel for dynamic lifecycle management.

        Parameters
        ----------
        panel_id:
            Unique string key (e.g. ``"solution_explorer"``).
        widget:
            The panel content widget.
        tab_manager:
            The UtilityTabManager that will host the panel's tab.
        side:
            ``"left"`` or ``"right"`` — used for splitter targeting.
        splitter:
            The QSplitter the panel's tab manager lives in.
        splitter_index:
            The tab manager's index inside *splitter*.
        default_width:
            Width in pixels to restore when activating a collapsed container.
        """
        self._widgets[panel_id] = widget
        self._tab_managers[panel_id] = tab_manager
        self._splitters[panel_id] = (splitter, splitter_index, default_width, side)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def activate_panel(self, panel_id: str) -> None:
        """Show the panel: add its tab if needed, switch to it, ensure container visible."""
        tm = self._tab_managers.get(panel_id)
        if tm is None:
            return

        if panel_id not in tm._panel_ids:
            title = self._TITLES.get(panel_id, panel_id)
            tm.add_panel(panel_id, title, self._widgets[panel_id])
        else:
            idx = tm._panel_ids.index(panel_id)
            tm._tab_bar.setTabVisible(idx, True)

        tm.set_current_panel(panel_id)
        tm.setVisible(True)

        splitter, sidx, default_width, _ = self._splitters.get(
            panel_id, (None, 0, 250, "")
        )
        if splitter is not None:
            sizes = splitter.sizes()
            if sidx < len(sizes) and sizes[sidx] < 50:
                sizes[sidx] = default_width
                splitter.setSizes(sizes)

        self.panel_visibility_changed.emit(panel_id, True)

    def deactivate_panel(self, panel_id: str) -> None:
        """Hide the panel tab.  If no tabs remain in the container, collapse it."""
        tm = self._tab_managers.get(panel_id)
        if tm is None or panel_id not in tm._panel_ids:
            return

        idx = tm._panel_ids.index(panel_id)
        tm._tab_bar.setTabVisible(idx, False)

        if tm._tab_bar.currentIndex() == idx:
            for i in range(tm._tab_bar.count()):
                if tm._tab_bar.isTabVisible(i):
                    tm._tab_bar.setCurrentIndex(i)
                    break

        visible_tabs = sum(
            1 for i in range(tm._tab_bar.count()) if tm._tab_bar.isTabVisible(i)
        )
        if visible_tabs == 0:
            tm.setVisible(False)
            splitter, sidx, _, _ = self._splitters.get(
                panel_id, (None, 0, 250, "")
            )
            if splitter is not None:
                sizes = splitter.sizes()
                if sidx < len(sizes):
                    sizes[sidx] = 0
                    splitter.setSizes(sizes)

        self.panel_visibility_changed.emit(panel_id, False)

    def is_visible(self, panel_id: str) -> bool:
        """Return ``True`` if *panel_id*'s tab is currently visible."""
        tm = self._tab_managers.get(panel_id)
        if tm is None or panel_id not in tm._panel_ids:
            return False
        idx = tm._panel_ids.index(panel_id)
        return tm._tab_bar.isTabVisible(idx)
