from PyQt6.QtCore import QDir, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QToolButton,
    QWidget,
    QFrame,
    QLabel,
)


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_path = QDir.currentPath()
        self.setObjectName(self.PANEL_OBJECT_NAME)

        self._build_shell()

    def _build_shell(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._frame = QFrame(self)
        self._frame.setObjectName(self.FRAME_OBJECT_NAME)
        self._frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(10, 10, 10, 10)
        self._frame_layout.setSpacing(8)

        self._main_layout.addWidget(self._frame)

        self._build_header_row()
        self._build_body()

    def _build_header_row(self) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.title = QLabel(self.TITLE_TEXT)
        self.title.setObjectName(self.TITLE_OBJECT_NAME)

        row.addWidget(self.title)
        row.addStretch(1)

        for widget in self._header_right_widgets():
            row.addWidget(widget)

        self._frame_layout.addLayout(row)

    def _build_body(self) -> None:
        """Override in subclasses."""
        raise NotImplementedError

    def _header_right_widgets(self) -> list[QWidget]:
        """Override in subclasses."""
        return []

    def _build_header_row(self) -> None:
        """
        A helper function to set a window utility undockable, by building a top
        header row that contains a docking options.
        """
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
