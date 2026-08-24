"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Server Explorer panel for DreamStudio.

Provides a sidebar panel for browsing and managing remote server
connections. This is a placeholder implementation that will be
extended with full remote file browsing, editing, and management
capabilities.
"""

from editor import *

from editor.utils.panel_shell import PanelShell


class ServerExplorer(PanelShell):
    """
    IDE sidebar panel for remote server exploration and management.

    Provides a tabbed interface for managing server connections and
    browsing remote file systems. Currently a placeholder that will
    be extended with full functionality.
    """

    PANEL_OBJECT_NAME = "ServerExplorer"
    FRAME_OBJECT_NAME = "ServerExplorerFrame"
    TITLE_OBJECT_NAME = "ServerExplorerTitle"
    TITLE_TEXT = "Server Explorer"

    def __init__(self, parent=None):
        """Initialize the Server Explorer panel."""
        self._current_connection = None
        super().__init__(parent)
        self.setMinimumWidth(350)

    def _build_body(self) -> None:
        """Construct the main panel body with placeholder content."""
        self.view_stack = QStackedWidget(self)

        # Connections page (placeholder)
        self._build_connections_page()

        # Remote files page (placeholder)
        self._build_remote_files_page()

        self._frame_layout.addWidget(self.view_stack)

    def _build_connections_page(self) -> None:
        """Build the connections management page."""
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self._connections_label = QLabel("Connections")
        self._connections_label.setObjectName("ServerExplorerSectionTitle")
        header_row.addWidget(self._connections_label)
        header_row.addStretch(1)

        self._add_connection_btn = QPushButton("+")
        self._add_connection_btn.setObjectName("ServerExplorerAddBtn")
        self._add_connection_btn.setFixedSize(24, 24)
        self._add_connection_btn.setToolTip("Add new server connection")
        self._add_connection_btn.clicked.connect(self._on_add_connection)
        header_row.addWidget(self._add_connection_btn)

        layout.addLayout(header_row)

        # Placeholder content
        placeholder = QFrame()
        placeholder.setObjectName("ServerExplorerPlaceholder")
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        placeholder_label = QLabel("No server connections configured.\n\n"
                                   "Click the (+) button to add a new connection.")
        placeholder_label.setObjectName("ServerExplorerPlaceholderText")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setWordWrap(True)
        placeholder_layout.addWidget(placeholder_label)

        layout.addWidget(placeholder)

        self.view_stack.addWidget(page)

    def _build_remote_files_page(self) -> None:
        """Build the remote files browsing page."""
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Placeholder content
        placeholder = QFrame()
        placeholder.setObjectName("ServerExplorerPlaceholder")
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        placeholder_label = QLabel("Connect to a server to browse files.")
        placeholder_label.setObjectName("ServerExplorerPlaceholderText")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)

        layout.addWidget(placeholder)

        self.view_stack.addWidget(page)

    def _on_add_connection(self) -> None:
        """Handle add connection button click."""
        # TODO: Implement connection dialog
        pass

    def _header_right_widgets(self) -> list[QWidget]:
        """Provide header widgets for the panel."""
        return []
