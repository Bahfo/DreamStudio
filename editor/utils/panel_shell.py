"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Generic shell for sidebar-style panels with float/dock capability.
"""

from editor import *


class PanelShell(QWidget):
    """Generic shell for sidebar-style panels with float/dock capability.

    The shell owns a header row (title, float toggle, close) plus a body
    supplied by subclasses. A panel can be floated into a standalone
    top-level window; toggling the float button again docks the panel back
    into the exact slot it was registered in.

    Attributes:
        title: Header label holding the panel title.
        undock_btn: Header button that toggles the float/dock state.
        close_btn: Header button that requests panel closure.
    """

    close_requested = pyqtSignal()
    float_requested = pyqtSignal(bool)

    PANEL_OBJECT_NAME = "Panel"
    FRAME_OBJECT_NAME = "PanelFrame"
    TITLE_OBJECT_NAME = "PanelTitle"
    DIRECTORY_LABEL_OBJECT_NAME = "PanelDirectoryLabel"
    SEARCH_BAR_OBJECT_NAME = "PanelSearchBar"
    TREE_VIEW_OBJECT_NAME = "PanelTreeView"
    RENAME_EDITOR_OBJECT_NAME = "PanelRenameEditor"
    TITLE_TEXT = "Panel"
    CONTENT_MARGINS: tuple[int, int, int, int] = (10, 10, 10, 10)
    CONTENT_SPACING: int = 8

    FLOAT_ICON = "🗖"
    DOCK_ICON = "🗗"
    FLOAT_TOOLTIP = "Float Tool Window"
    DOCK_TOOLTIP = "Dock Tool Window"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_path = ""
        self.setObjectName(self.PANEL_OBJECT_NAME)

        self._panel_id: str = ""
        self._tab_manager: Optional[QWidget] = None
        self._side: str = ""
        self._splitter: Optional[QSplitter] = None
        self._splitter_index: int = 0
        self._default_width: int = 220
        self._vertical_menus_api: Optional[QObject] = None

        self._is_floating: bool = False
        self._float_window: Optional[QWidget] = None
        self._float_size: Optional[tuple[int, int]] = None
        self._dock_index: int = -1

        self._build_shell()

    def set_registration_info(
        self,
        panel_id: str,
        tab_manager: QWidget,
        side: str,
        splitter: QSplitter,
        splitter_index: int,
        default_width: int,
        vertical_menus_api: Optional[QObject] = None,
    ) -> None:
        """Bind the panel to the slot it was registered in.

        Args:
            panel_id: Unique identifier of the panel.
            tab_manager: Side stack that hosts the panel's tab.
            side: ``"left"`` or ``"right"``; drives the float window origin.
            splitter: Horizontal splitter that owns the side stack.
            splitter_index: Index of the side stack inside the splitter.
            default_width: Width used for the floating window.
            vertical_menus_api: Panel activation controller (optional).
        """
        self._panel_id = panel_id
        self._tab_manager = tab_manager
        self._side = side
        self._splitter = splitter
        self._splitter_index = splitter_index
        self._default_width = default_width
        self._vertical_menus_api = vertical_menus_api

    @classmethod
    def make_overflow_button(cls, parent=None):
        """Shared overflow/dropdown button for panel headers."""
        from editor.utils.resource_path import resource_path
        from editor.widgets.QToolButton import ToolbarButton

        return ToolbarButton(
            icon_path=resource_path("assets/menus/dropdown.png"),
            tooltip="More actions",
            fixed_size=(24, 24),
            icon_size=(16, 16),
        )

    def _build_shell(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._frame = QFrame(self)
        self._frame.setObjectName(self.FRAME_OBJECT_NAME)
        self._frame.setFrameShape(QFrame.Shape.NoFrame)
        self._frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(*self.CONTENT_MARGINS)
        self._frame_layout.setSpacing(self.CONTENT_SPACING)

        self._main_layout.addWidget(self._frame)

        self._build_header_row()
        for row in self._extra_header_rows():
            self._frame_layout.addLayout(row)
        self._build_body()

    def _extra_header_rows(self) -> list:
        """Optional extra header rows below the title bar."""
        return []

    def _build_body(self) -> None:
        """Override in subclasses."""
        raise NotImplementedError

    def _header_right_widgets(self) -> list[QWidget]:
        """Override in subclasses."""
        return []

    def _build_header_row(self) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.title = QLabel(self.TITLE_TEXT)
        self.title.setObjectName(self.TITLE_OBJECT_NAME)

        row.addWidget(self.title)
        row.addStretch(1)

        self.undock_btn = QToolButton(self)
        self.undock_btn.setObjectName("PanelUndockButton")
        self.undock_btn.setToolTip(self.FLOAT_TOOLTIP)
        self.undock_btn.setText(self.FLOAT_ICON)
        self.undock_btn.clicked.connect(self.toggle_float)
        row.addWidget(self.undock_btn)

        self.close_btn = QToolButton(self)
        self.close_btn.setObjectName("PanelCloseButton")
        self.close_btn.setToolTip("Close Panel")
        self.close_btn.setText("✕")
        self.close_btn.clicked.connect(self._on_close_clicked)
        row.addWidget(self.close_btn)

        for widget in self._header_right_widgets():
            row.addWidget(widget)

        self._frame_layout.addLayout(row)

    # ------------------------------------------------------------------
    # Float / dock
    # ------------------------------------------------------------------

    @property
    def is_floating(self) -> bool:
        """Return ``True`` when the panel currently lives in a floating window."""
        return self._is_floating

    def toggle_float(self) -> None:
        """Toggle the panel between its docked slot and a floating window."""
        if self._is_floating:
            self._dock_panel()
        else:
            self._float_panel()

    def _float_panel(self) -> None:
        """Move the panel into a standalone top-level window.

        The window is parented to the IDE's top-level widget so the global
        QSS keeps cascading into it; the ``Qt.Window`` flag still makes it an
        independently movable window.
        """
        if self._is_floating or self._tab_manager is None:
            return

        self._dock_index = self._manager_index()

        host = self.window()
        if host is self:
            host = None
        window = QFrame(host, Qt.WindowType.Window)
        window.setWindowTitle(self.TITLE_TEXT)
        window.setObjectName("FloatingPanelFrame")
        window.setFrameShape(QFrame.Shape.NoFrame)
        window.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        float_layout = QVBoxLayout(window)
        float_layout.setContentsMargins(0, 0, 0, 0)
        float_layout.setSpacing(0)

        self._main_layout.removeWidget(self._frame)
        self._frame.setParent(None)
        float_layout.addWidget(self._frame)

        self._float_window = window
        self._is_floating = True
        self._float_size = (
            max(self.width(), self._default_width),
            max(self.height(), 200),
        )

        self._set_tab_visible(False)
        self._update_float_button(True)

        self._position_floating_window()

        window.installEventFilter(self)
        window.destroyed.connect(self._on_float_window_destroyed)
        window.show()

        self.float_requested.emit(True)

    def _dock_panel(self) -> None:
        """Return the panel to the exact slot it was registered in."""
        if not self._is_floating:
            return

        window = self._float_window
        self._float_window = None
        self._is_floating = False

        if window is not None and not self._is_deleted(window):
            try:
                float_layout = window.layout()
                if float_layout is not None:
                    float_layout.removeWidget(self._frame)
                window.removeEventFilter(self)
                try:
                    window.destroyed.disconnect(self._on_float_window_destroyed)
                except (TypeError, RuntimeError):
                    pass
                self._frame.setParent(None)
                self._main_layout.addWidget(self._frame)
                window.hide()
                window.deleteLater()
            except RuntimeError:
                pass

        self._set_tab_visible(True)
        self._restore_splitter_width()
        self._update_float_button(False)

        self.float_requested.emit(False)

    def _restore_splitter_width(self) -> None:
        """Give the side stack back the width it had before floating."""
        manager = self._tab_manager
        if manager is None or self._is_deleted(manager):
            return
        try:
            manager.setVisible(True)
        except RuntimeError:
            return
        splitter = self._splitter
        if splitter is None or self._is_deleted(splitter):
            return
        try:
            sizes = splitter.sizes()
            if self._splitter_index >= len(sizes) or len(sizes) < 2:
                return
            target = max(self._default_width, self.minimumWidth())
            if sizes[self._splitter_index] < target:
                delta = max(0, min(target - sizes[self._splitter_index], sizes[1]))
                if delta > 0:
                    sizes[1] -= delta
                    sizes[self._splitter_index] += delta
                    splitter.setSizes(sizes)
        except RuntimeError:
            pass

    def _position_floating_window(self) -> None:
        """Place the floating window next to the side stack it came from."""
        window = self._float_window
        if window is None or self._splitter is None or self._is_deleted(window):
            return

        width = self._float_size[0] if self._float_size else self._default_width
        height = self._float_size[1] if self._float_size else 400
        window.resize(width, height)

        origin = self._splitter.mapToGlobal(QPoint(0, 0))
        sizes = self._splitter.sizes()
        if self._side == "left":
            x = origin.x() + sum(sizes[: self._splitter_index + 1]) - width
        else:
            x = origin.x() + sum(sizes[: self._splitter_index])
        y = origin.y() + 50

        screen = QApplication.screenAt(QPoint(x, y)) or QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            x = max(geo.left(), min(x, geo.right() - window.width()))
            y = max(geo.top(), min(y, geo.bottom() - window.height()))

        window.move(x, y)

    def _manager_index(self) -> int:
        """Return the panel's index inside the side stack, or ``-1``."""
        manager = self._tab_manager
        if manager is None or not hasattr(manager, "_panel_ids"):
            return -1
        if self._panel_id not in manager._panel_ids:
            return -1
        return manager._panel_ids.index(self._panel_id)

    def _set_tab_visible(self, visible: bool) -> None:
        """Show or hide the panel's tab inside the side stack."""
        manager = self._tab_manager
        if manager is None or not hasattr(manager, "_tab_bar"):
            return
        idx = self._manager_index()
        if idx < 0:
            return
        try:
            manager._tab_bar.setTabVisible(idx, visible)
            if visible:
                manager._tab_bar.setCurrentIndex(idx)
        except RuntimeError:
            pass

    def _update_float_button(self, floating: bool) -> None:
        """Refresh the float button icon and tooltip for the current state."""
        self.undock_btn.setText(self.DOCK_ICON if floating else self.FLOAT_ICON)
        self.undock_btn.setToolTip(self.DOCK_TOOLTIP if floating else self.FLOAT_TOOLTIP)

    def _on_close_clicked(self) -> None:
        """Handle the header close button.

        A floating panel is docked back into its original slot first so the
        panel is never left orphaned in a floating window.
        """
        if self._is_floating:
            self._dock_panel()
        self.close_requested.emit()

    def _on_float_window_destroyed(self) -> None:
        """Handle the floating window being destroyed by the window manager."""
        self._float_window = None
        if not self._is_floating:
            return
        self._is_floating = False
        self._set_tab_visible(True)
        self._restore_splitter_width()
        self._update_float_button(False)
        self.float_requested.emit(False)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Catch close requests on the floating window and dock the panel."""
        if obj is self._float_window and event.type() == QEvent.Type.Close and self._is_floating:
            self._dock_panel()
            return True
        return super().eventFilter(obj, event)

    @staticmethod
    def _is_deleted(widget: Optional[QWidget]) -> bool:
        """Return ``True`` when the C++ side of *widget* is already gone.

        Args:
            widget: Widget to probe; ``None`` counts as deleted.

        Returns:
            True when the widget can no longer be used.
        """
        if widget is None:
            return True
        try:
            widget.objectName()
        except RuntimeError:
            return True
        return False

    def closeEvent(self, event) -> None:
        """Tear the floating window down together with the panel."""
        if self._is_floating:
            self._dock_panel()
        super().closeEvent(event)
