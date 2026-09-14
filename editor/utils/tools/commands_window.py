from editor import *

logger = logging.getLogger(__name__)


class CommandWindow(QMenu):
    def __init__(self, hanging_widget, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("jetbrainsCommandMenu")
        self.setFixedWidth(580)
        self._parent = parent
        self._hang_widget = hanging_widget
        self._command_actions = []

        self._build_actions()

    def _build_actions(self):
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 8, 10, 8)
        search_layout.setSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("commandSearchInput")
        self.search_input.setPlaceholderText(
            "Search actions, commands... (Type to filter)"
        )

        self.search_input.setStyleSheet("""
            QLineEdit#commandSearchInput {
                border: none;
                font-size: 13px;
                padding: 4px 2px;
            }
        """)
        search_layout.addWidget(self.search_input)

        search_action = QWidgetAction(self)
        search_action.setDefaultWidget(search_container)
        self.addAction(search_action)

        self.addSeparator()

        self._load_commands_list()

        self.addSeparator()

        tip_container = QWidget()
        tip_layout = QHBoxLayout(tip_container)
        tip_layout.setContentsMargins(12, 4, 12, 6)

        self.tip_label = QLabel(
            "Navigate with up-down arrows. Enter to Select, and Esc to Close"
        )
        self.tip_label.setObjectName("commandTipLabel")
        self.tip_label.setStyleSheet("""
            QLabel#commandTipLabel {
                font-size: 11px;
                padding: 2px 0px;
            }
        """)
        tip_layout.addWidget(self.tip_label)

        tip_action = QWidgetAction(self)
        tip_action.setDefaultWidget(tip_container)
        self.addAction(tip_action)

        self.search_input.textChanged.connect(self._filter_commands)

    def _load_commands_list(self):
        try:
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                cmd_path = Path(sys._MEIPASS) / "editor" / "utils" / "tools" / "json" / "commands_list.json"  # type: ignore[attr-defined]
            else:
                cmd_path = Path(__file__).parent / "json" / "commands_list.json"
            with open(cmd_path, "r") as file:
                commands = json.load(file)

            for command, display in commands.items():
                action = QAction(command, self)
                action.setData(display)

                if isinstance(display, dict):
                    if "shortcut" in display:
                        action.setShortcut(QKeySequence(display["shortcut"]))
                    if "description" in display:
                        action.setToolTip(display["description"])
                elif isinstance(display, str) and display:
                    action.setShortcut(QKeySequence(display))

                action.triggered.connect(
                    lambda checked=False, c=command: self._on_choosing_command(c)
                )
                self.addAction(action)
                self._command_actions.append(action)

        except Exception as e:
            logger.error("Failed to load commands: %s", e)
            err_action = QAction(f"Error loading commands: {e}", self)
            err_action.setEnabled(False)
            self.addAction(err_action)

    def _filter_commands(self, text):
        """Triggered automatically every time the user types a letter."""
        search_text = text.lower()
        for action in self._command_actions:
            is_match = search_text in action.text().lower()
            action.setVisible(is_match)

    def _on_choosing_command(self, command):
        logger.info("Executing command: %s", command)

    def _show(self, event=None):
        """Positions menu and focuses search input upon display."""
        corner_left = self._hang_widget.rect().bottomLeft()
        global_pos = self._hang_widget.mapToGlobal(corner_left)
        self.search_input.clear()
        self.search_input.setFocus()
        self.exec(global_pos)
