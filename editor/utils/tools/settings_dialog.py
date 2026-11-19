"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Theme and font preference panel for DreamStudio.
"""

from editor import *

THEMES = [
    ("dark", "Dark"),
    ("light", "Light"),
    ("moses", "Moses"),
    ("davy", "Davy"),
    ("tokyonight", "Tokyo Night"),
    ("solarized_dark", "Solarized Dark"),
    ("solarized_light", "Solarized Light"),
    ("monokai", "Monokai"),
    ("dark_hc", "Dark High Contrast"),
    ("light_hc", "Light High Contrast"),
    ("coffee_dark", "Coffee Dark"),
    ("coffee_light", "Coffee Light"),
    ("material_dark", "Material Dark"),
    ("material_light", "Material Light"),
]


class SettingsPanel(QWidget):
    """Theme and font preferences embedded as an editor tab."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._window = None
        self.setObjectName("SettingsPanel")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        section = QLabel("Appearance")
        section.setObjectName("SettingsSectionTitle")
        section.setStyleSheet("font-size: 16px;")
        layout.addWidget(section)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.theme_combo = QComboBox()
        for key, label in THEMES:
            self.theme_combo.addItem(label, key)
        form.addRow("Theme", self.theme_combo)

        self.font_combo = QFontComboBox()
        form.addRow("Font family", self.font_combo)

        layout.addLayout(form)

        hint = QLabel(
            "Theme changes apply immediately. The font family is re-applied to the "
            "whole interface when you press Apply."
        )
        hint.setWordWrap(True)
        hint.setObjectName("SettingsHint")
        layout.addWidget(hint)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.apply_button = QPushButton("Apply")
        self.apply_button.setObjectName("SettingsApplyButton")
        self.apply_button.clicked.connect(self._apply)
        actions.addWidget(self.apply_button)
        layout.addLayout(actions)

        layout.addStretch(1)

        scroll.setWidget(content)

        self._load_current_values()

    def set_window(self, window) -> None:
        """Point the panel at the IDE main window and refresh its values."""
        self._window = window
        self._load_current_values()

    def _window_ref(self):
        """Resolve the IDE main window that owns this panel."""
        if self._window is not None:
            return self._window

        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, "_set_theme_by_name"):
                return parent
            parent = parent.parentWidget()

        window = self.window()
        if window is not None and hasattr(window, "_set_theme_by_name"):
            return window
        return None

    def _load_current_values(self) -> None:
        """Populate the controls from the current IDE configuration."""
        window = self._window_ref()
        if window is None:
            return

        current = getattr(window, "_current_theme_name", None) or "dark"
        index = self.theme_combo.findData(current)
        self.theme_combo.setCurrentIndex(index if index >= 0 else 0)

        family = getattr(window, "_get_configured_font_family", lambda: None)()
        if family:
            self.font_combo.setCurrentFont(QFont(family))

    def _apply(self) -> None:
        """Apply the selected theme and font family to the IDE."""
        window = self._window_ref()
        if window is None:
            return

        theme = self.theme_combo.currentData()
        family = self.font_combo.currentFont().family()

        if theme:
            window._set_theme_by_name(str(theme))
        if family:
            window.set_global_font(str(family))

        self._persist(window, theme, family)

    def _persist(self, window, theme, family) -> None:
        """Write the chosen appearance values back to the configuration."""
        registry = getattr(window, "_registry", None)
        if registry is None:
            return

        if registry.has("config_service"):
            service = registry.get("config_service")
            editor_cfg = dict(service.get("editor") or {})
            if theme:
                editor_cfg["theme"] = str(theme)
            if family:
                editor_cfg["font_family"] = str(family)
            service.set("editor", editor_cfg)

        if registry.has("config"):
            config = registry.get("config")
            if isinstance(config, dict):
                config.setdefault("editor", {})
                if theme:
                    config["editor"]["theme"] = str(theme)
                if family:
                    config["editor"]["font_family"] = str(family)
