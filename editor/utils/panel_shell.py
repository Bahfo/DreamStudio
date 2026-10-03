from editor import *


class PanelShell(QWidget):
    """
    Generic shell for sidebar-style panels.

    Subclasses override ``_build_body`` and optionally ``_header_right_widgets``.
    """

    close_requested = pyqtSignal()

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_path = ""
        self.setObjectName(self.PANEL_OBJECT_NAME)

        self._build_shell()

    @classmethod
    def make_overflow_button(cls, parent=None):
        """Shared overflow/dropdown button for panel headers."""
        from editor.widgets.QToolButton import ToolbarButton
        from editor.utils.resource_path import resource_path

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
        self.undock_btn.setToolTip("Float Tool Window")
        self.undock_btn.setText("🗖")
        row.addWidget(self.undock_btn)

        self.close_btn = QToolButton(self)
        self.close_btn.setObjectName("PanelCloseButton")
        self.close_btn.setToolTip("Close Panel")
        self.close_btn.setText("✕")
        self.close_btn.clicked.connect(self.close_requested.emit)
        row.addWidget(self.close_btn)

        for widget in self._header_right_widgets():
            row.addWidget(widget)

        self._frame_layout.addLayout(row)
