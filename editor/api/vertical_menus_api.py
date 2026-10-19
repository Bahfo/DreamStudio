"""Vertical Menus API — panel activation manager for DreamStudio."""

from __future__ import annotations

from editor import *

class VerticalMenusAPI(QObject):
    """Panel activation/deactivation controller."""

    panel_visibility_changed = pyqtSignal(str, bool)

    _TITLES = {
        "solution_explorer": "Solution Explorer",
        "source_control": "Source Control",
        "properties": "Properties",
        "todo_search": "TODO Search",
        "server_explorer": "Server Explorer",
        "notifications": "Notifications",
        "ether_ai": "Ether AI",
    }

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._widgets: dict[str, QWidget] = {}
        self._tab_managers: dict[str, QWidget] = {}
        self._splitters: dict[str, tuple] = {}


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
        """Register a panel for dynamic lifecycle management."""
        self._widgets[panel_id] = widget
        self._tab_managers[panel_id] = tab_manager
        self._splitters[panel_id] = (splitter, splitter_index, default_width, side)


    def activate_panel(self, panel_id: str) -> None:
        """Show the panel:"""
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
            if sidx < len(sizes):
                target = max(default_width, self._widgets[panel_id].minimumWidth())
                if sizes[sidx] < target:
                    delta = max(0, min(target - sizes[sidx], sizes[1]))
                    if delta > 0:
                        sizes[1] -= delta
                        sizes[sidx] += delta
                        splitter.setSizes(sizes)

        self.panel_visibility_changed.emit(panel_id, True)

    def deactivate_panel(self, panel_id: str) -> None:
        """Hide the panel tab."""
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
            splitter, sidx, _, _ = self._splitters.get(
                panel_id, (None, 0, 250, "")
            )
            if splitter is not None and sidx < len(splitter.sizes()):
                sizes = splitter.sizes()
                tm.setVisible(False)
                sizes[1] += sizes[sidx]
                sizes[sidx] = 0
                splitter.setSizes(sizes)
            else:
                tm.setVisible(False)

        self.panel_visibility_changed.emit(panel_id, False)

    def is_visible(self, panel_id: str) -> bool:
        """Return ``True`` if *panel_id*'s tab is currently visible."""
        tm = self._tab_managers.get(panel_id)
        if tm is None or panel_id not in tm._panel_ids:
            return False
        idx = tm._panel_ids.index(panel_id)
        return tm._tab_bar.isTabVisible(idx)
