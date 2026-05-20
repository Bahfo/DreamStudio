from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QScrollArea,
    QLineEdit,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QMenu,
    QFrame,
    QSizePolicy,
)


class ExtensionsTab(QFrame):
    def __init__(self, _parent=None):
        super().__init__()
        self._parent = _parent
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setStyleSheet("background-color: #171717; border: none;")

        # Track marketplace cards for the search filter
        self.marketplace_cards = []

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 1. Search Bar at the absolute top
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search extensions in Marketplace...")
        self.search_bar.textChanged.connect(self.filter_marketplace)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #252526;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 2px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
        """)
        self.main_layout.addWidget(self.search_bar)

        # 2. Scrollable Body Area (to handle long lists gracefully)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(15)

        # Mock Data Split
        marketplace_data = [
            (
                "Composer Studio",
                "Make your applications come to live with excellent tools for designers.",
                "EXcellent TechStacks",
            ),
            (
                "Bash Commands Pack",
                "Unlock next capabilities of Bash with powerful set of automation commands.",
                "EXcellent TechStacks",
            ),
            (
                "IronKinter",
                """A powerful GUI framework built on top of CustomTkinter to add more responsiveness,
more powerful widgets, and more.""",
                "EXcellent TechStacks",
            ),
            (
                "Developer Support Tools Pack",
                "Install a handful of tools that everyday's developer uses.",
                "EXcellent TechStacks",
            ),
        ]

        installed_data = [
            (
                "Python Support",
                "Rich support for Python language features",
                "EXcellent TechStacks",
            ),
        ]

        # --- SECTION A: MARKETPLACE ---
        # Header Label
        market_label = QLabel("MARKETPLACE")
        market_label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        scroll_layout.addWidget(market_label)

        # Container for Marketplace items
        self.marketplace_container = QVBoxLayout()
        self.marketplace_container.setSpacing(2)
        for title, desc, pub in marketplace_data:
            card = ExtensionCard("path/to/icon.png", title, desc, pub)
            self.marketplace_container.addWidget(card)
            self.marketplace_cards.append(
                (title.lower(), card)
            )  # Keep reference for filter

        scroll_layout.addLayout(self.marketplace_container)

        # --- SECTION B: INSTALLED ---
        # Header Label
        installed_label = QLabel("INSTALLED")
        installed_label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-top: 10px;"
        )
        scroll_layout.addWidget(installed_label)

        # Container for Installed items
        self.installed_container = QVBoxLayout()
        self.installed_container.setSpacing(2)
        for title, desc, pub in installed_data:
            card = ExtensionCard("path/to/icon.png", title, desc, pub)
            # Optional: Customize the installed card button string here if your ExtensionCard supports it (e.g. "Uninstall")
            self.installed_container.addWidget(card)

        scroll_layout.addLayout(self.installed_container)

        # Spacer to push everything up smoothly
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        self.main_layout.addWidget(scroll_area)

    def filter_marketplace(self, text):
        """Filters the Marketplace section items by name only."""
        search_query = text.lower().strip()

        for title, card in self.marketplace_cards:
            if search_query in title:
                card.show()
            else:
                card.hide()


class ExtensionCard(QWidget):
    def __init__(self, icon_path, title, description, publisher, parent=None):
        super().__init__(parent)
        self.init_ui(icon_path, title, description, publisher)

    def init_ui(self, icon_path, title, description, publisher):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(12)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(48, 48)
        self.set_circular_icon(icon_path)
        main_layout.addWidget(self.icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("TitleLabel")

        self.desc_label = QLabel(description, self)
        self.desc_label.setObjectName("DescLabel")
        self.desc_label.setWordWrap(True)

        self.pub_label = QLabel(publisher, self)
        self.pub_label.setObjectName("PubLabel")

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.desc_label)
        text_layout.addWidget(self.pub_label)

        main_layout.addLayout(text_layout, stretch=1)

        self.install_btn = QPushButton("Install", self)
        self.install_btn.setFixedSize(70, 24)
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.action_menu = QMenu(self)
        self.action_menu.addAction("Install Release Version")
        self.action_menu.addAction("Install Pre-Release Version")
        self.install_btn.setMenu(self.action_menu)

        main_layout.addWidget(self.install_btn, alignment=Qt.AlignmentFlag.AlignTop)

        self.setStyleSheet("""
            QWidget {
                background-color: #181818;
                font-family: 'Segoe UI', sans-serif;
            }
            QWidget:hover {
                background-color: #202020;
            }
            
            QLabel {
                background-color: transparent;
            }
            
            #TitleLabel {
                color: #cccccc;
                font-size: 13px;
                font-weight: bold;
            }
            #DescLabel {
                color: #858585;
                font-size: 12px;
            }
            #PubLabel {
                color: #858585;
                font-size: 11px;
            }
            
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 12px;
                font-weight: 500;
                padding-right: 15px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton::menu-indicator {
                image: none;
                subcontrol-position: right center;
                subcontrol-origin: padding;
                left: -4px;
            }
            QMenu {
                background-color: #1f1f1f;
                border: 1px solid #454545;
                color: #cccccc;
                padding: 4px 0px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #007acc;
                color: white;
            }
        """)

    def set_circular_icon(self, icon_path):
        """Creates a smooth circular cutout for any source image."""
        src_pixmap = QPixmap(icon_path)
        if src_pixmap.isNull():
            self.icon_label.setStyleSheet(
                "background-color: #333; border-radius: 24px;"
            )
            return

        size = self.icon_label.size()
        target = QPixmap(size)
        target.fill(Qt.GlobalColor.transparent)

        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        path = QPainterPath()
        path.addEllipse(0, 0, size.width(), size.height())
        painter.setClipPath(path)

        painter.drawPixmap(0, 0, size.width(), size.height(), src_pixmap)
        painter.end()

        self.icon_label.setPixmap(target)
