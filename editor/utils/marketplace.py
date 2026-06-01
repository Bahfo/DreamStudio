import json
import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QSizePolicy,
    QScrollArea,
    QLineEdit,
    QWidget,
    QLabel,
    QFrame,
)

from editor.widgets.QCardButton import CardButton


current_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.abspath(os.path.join(current_dir, "..", "data", "marketplace.json"))

class ExtensionsTab(QFrame):
    def __init__(self, _parent=None):
        super().__init__()
        self._parent = _parent
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setStyleSheet("background-color: #171717; border: none;")

        self.marketplace_cards = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.main_layout.addSpacing(10)
        self._market_label = QLabel("MARKETPLACE")
        self._market_label.setStyleSheet(
            "color: #969696; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        self.main_layout.addWidget(self._market_label)
        self.main_layout.addSpacing(10)

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

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(15)
        data = self.load_data_from_json(json_path)

        # 1. Populate Marketplace
        self.marketplace_container = QVBoxLayout()
        self.marketplace_container.setSpacing(2)
        
        for item in data.get("marketplace", []):
            card = CardButton(
                item.get("icon", "path/to/icon.png"), 
                item.get("title", "Unknown"), 
                item.get("desc", ""), 
                item.get("publisher", "Unknown")
            )
            self.marketplace_container.addWidget(card)
            self.marketplace_cards.append((item.get("title", "").lower(), card))

        scroll_layout.addLayout(self.marketplace_container)

        self._installed_label = QLabel("INSTALLED")
        self._installed_label.setStyleSheet("""
            color: #969696; 
            font-size:11px; 
            font-weight: bold; 
            letter-spacing: 1px; 
            margin-top: 10px;
        """)
        scroll_layout.addWidget(self._installed_label)

        self.installed_container = QVBoxLayout()
        self.installed_container.setSpacing(2)
        
        for item in data.get("installed", []):
            card = CardButton(
                item.get("icon", "path/to/icon.png"), 
                item.get("title", "Unknown"), 
                item.get("desc", ""), 
                item.get("publisher", "Unknown")
            )
            self.installed_container.addWidget(card)

        scroll_layout.addLayout(self.installed_container)
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        self.main_layout.addWidget(scroll_area)

    def load_data_from_json(self, filepath: str) -> dict:
        """Helper method to load and parse json configuration safely."""
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print(f"Warning: Configuration file not found at {filepath}")
        except Exception as e:
            print(f"Error loading JSON configuration: {e}")
        
        return {"marketplace": [], "installed": []}

    def retheme(self, t) -> None:
        bg = t.color("sidebar.background")
        txt = t.color("sidebar.text")
        input_bg = t.color("input.background")
        input_border = t.color("input.border")
        input_focus = t.color("input.focus_border")
        input_txt = t.color("input.text")
        self.setStyleSheet(f"background-color: {bg}; border: none;")
        self._market_label.setStyleSheet(
            f"color: {txt}; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        self._installed_label.setStyleSheet(
            f"color: {txt}; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-top: 10px;"
        )
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_txt};
                border: 1px solid {input_border};
                border-radius: 2px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {input_focus};
            }}
        """)
        for card in self.findChildren(CardButton):
            card.retheme(t)

    def filter_marketplace(self, text):
        """Filters the Marketplace section items by name only."""
        search_query = text.lower().strip()

        for title, card in self.marketplace_cards:
            if search_query in title:
                card.show()
            else:
                card.hide()