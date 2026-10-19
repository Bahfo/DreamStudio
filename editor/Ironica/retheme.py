"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Dynamic IDE theme engine for DreamStudio.
"""

from editor import *
from editor.utils.resource_path import resource_path

_THEMES_DIR = resource_path("editor/Ironica/themes")
_QSS_DIR = resource_path("editor/qss")
_DEFAULT_THEME = "dark"

_ACTIVE_THEME = _DEFAULT_THEME

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$")


def is_hex_color(value: object) -> bool:
    """Return ``True`` if *value* is a hex colour string like ``#RRGGBB``."""
    return isinstance(value, str) and bool(_HEX_COLOR_RE.match(value.strip()))


def theme_palette(theme_name: str = _DEFAULT_THEME) -> Dict[str, str]:
    """Load the syntax-colour palette for *theme_name* from the themes dir."""
    path = os.path.join(_THEMES_DIR, f"{theme_name}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    palette = data.get("palette", {}) if isinstance(data, dict) else {}
    return {key: value for key, value in palette.items() if is_hex_color(value)}


DIAGNOSTIC_PALETTE_KEYS = {
    "ERROR": "ERROR_COLOR",
    "WARNING": "WARNING_COLOR",
    "CHECK": "CHECK_COLOR",
    "TYPO": "TYPO_COLOR",
    "INFO": "INFO_COLOR",
}

DEFAULT_DIAGNOSTIC_PALETTE = {
    "ERROR": "#F14C4C",
    "WARNING": "#FCC700",
    "CHECK": "#C586C0",
    "TYPO": "#3794FF",
    "INFO": "#4EC9B0",
}


def diagnostic_palette(theme_name: Optional[str] = None) -> Dict[str, str]:
    """Return ``{severity_name:"""
    palette = theme_palette(theme_name or active_theme_name())
    resolved = {}
    for severity, key in DIAGNOSTIC_PALETTE_KEYS.items():
        resolved[severity] = palette.get(key) or DEFAULT_DIAGNOSTIC_PALETTE[severity]
    return resolved


DEFAULT_DOC_PALETTE = {
    "link": "#4FC1FF",
    "code": "#CE9178",
    "muted": "#8B9099",
    "quote": "#6A737D",
    "rule": "#3C3C3C",
    "name": "#9CDCFE",
    "kind": "#C586C0",
    "surface": "#202124",
    "surface_alt": "#25262A",
    "text": "#BCBEC4",
    "border": "#3C3C3C",
}


def doc_palette(theme_name: Optional[str] = None) -> Dict[str, str]:
    """Return surface and accent colours for the documentation flyout."""
    name = theme_name or active_theme_name()
    palette = theme_palette(name)
    editor = editor_colors(name)

    link = palette.get("ADDITIONAL_COLOR") or palette.get("HEADER_COLOR")
    quote = palette.get("COMMENT_COLOR")

    base = editor.get("bg")
    base_hex = base.name() if base is not None else None
    is_dark = (base.lightness() < 128) if base is not None else True

    surface_alt = base_hex or DEFAULT_DOC_PALETTE["surface"]
    if base is not None:
        surface_alt = (
            base.lighter(112).name() if is_dark else base.darker(103).name()
        )

    text = editor.get("fg")
    resolved = {
        "link": link or DEFAULT_DOC_PALETTE["link"],
        "code": palette.get("STRING_COLOR") or DEFAULT_DOC_PALETTE["code"],
        "muted": quote or DEFAULT_DOC_PALETTE["muted"],
        "quote": quote or DEFAULT_DOC_PALETTE["quote"],
        "name": palette.get("ADDITIONAL_COLOR") or DEFAULT_DOC_PALETTE["name"],
        "kind": palette.get("KEYWORD_COLOR") or DEFAULT_DOC_PALETTE["kind"],
        "surface": base_hex or DEFAULT_DOC_PALETTE["surface"],
        "surface_alt": surface_alt,
        "text": text.name() if text is not None else DEFAULT_DOC_PALETTE["text"],
        "border": editor.get("edge").name()
        if editor.get("edge") is not None
        else DEFAULT_DOC_PALETTE["border"],
    }
    resolved["rule"] = _mix_with_background(resolved["muted"], name)
    resolved["code"] = _ensure_contrast(
        resolved["code"], resolved["surface_alt"], 3.0, lighten=is_dark
    )
    return resolved


def _relative_luminance(color: QColor) -> float:
    """Return the WCAG relative luminance of *color*."""
    channels = []
    for value in (color.red(), color.green(), color.blue()):
        srgb = value / 255.0
        channels.append(
            srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(first: QColor, second: QColor) -> float:
    """Return the WCAG contrast ratio between two colours."""
    a = _relative_luminance(first)
    b = _relative_luminance(second)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _ensure_contrast(
    hex_color: str, hex_background: str, minimum: float, lighten: bool
) -> str:
    """Shift *hex_color* until it reaches *minimum* contrast on the background."""
    fg = QColor(hex_color)
    bg = QColor(hex_background)
    if not fg.isValid() or not bg.isValid():
        return hex_color

    step = 8 if lighten else -8
    for _ in range(32):
        if _contrast_ratio(fg, bg) >= minimum:
            break
        nudged = QColor(
            max(0, min(255, fg.red() + step)),
            max(0, min(255, fg.green() + step)),
            max(0, min(255, fg.blue() + step)),
        )
        if nudged == fg:
            break
        fg = nudged
    return fg.name()


def _mix_with_background(hex_color: str, theme_name: str) -> str:
    """Blend *hex_color* toward the theme background."""
    background = editor_colors(theme_name).get("bg")
    if background is None:
        return DEFAULT_DOC_PALETTE["rule"]
    from PyQt6.QtGui import QColor

    fg = QColor(hex_color)
    bg = QColor(background.name())
    return QColor(
        (fg.red() * 2 + bg.red()) // 3,
        (fg.green() * 2 + bg.green()) // 3,
        (fg.blue() * 2 + bg.blue()) // 3,
    ).name()


def resolve_colour(
    value: object, palette: Optional[Dict[str, str]] = None, default: str = ""
) -> str:
    """Resolve *value* to a concrete hex colour string."""
    if is_hex_color(value):
        return value
    palette = palette or {}
    resolved = palette.get(value) if isinstance(value, str) else None
    if resolved is not None:
        return resolved
    return default if default else (str(value) if value is not None else "")


def resolve_language_config(
    config: dict, theme_name: str = _DEFAULT_THEME
) -> dict:
    """Return a copy of *config* with every symbolic style resolved to hex."""
    palette = dict(config.get("palette", {}) or {})
    palette.update(theme_palette(theme_name))

    styles = config.get("styles", {}) or {}
    resolved_styles = {
        key: resolve_colour(value, palette, str(value))
        for key, value in styles.items()
    }

    resolved = dict(config)
    resolved["styles"] = resolved_styles
    return resolved


def _read_qss(theme_name: str) -> str:
    """Read the raw QSS source for *theme_name*, or ``""`` on failure."""
    try:
        with open(os.path.join(_QSS_DIR, f"{theme_name}.qss"), "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _qss_value(qss: str, selector_re: str, property_name: str) -> Optional[str]:
    """Extract a single QSS property value from the first matching rule."""
    pattern = re.compile(
        rf"{selector_re}\s*\{{[^}}]*(?<![\w-]){property_name}\s*:\s*([^;\s}}]+)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(qss)
    return match.group(1).strip() if match else None


def editor_colors(theme_name: str) -> Dict[str, QColor]:
    """Return the base editor colours for *theme_name* as ``QColor`` values."""
    qss = _read_qss(theme_name)

    bg_hex = (
        _qss_value(qss, r"QWidget#CodeEditor", "background-color")
        or _qss_value(qss, r"QMainWindow\s*,\s*QWidget", "background-color")
        or "#1E1E1E"
    )
    fg_hex = _qss_value(qss, r"QWidget#CodeEditor", "color") or "#D4D4D4"
    sel_hex = (
        _qss_value(qss, r"QWidget#CodeEditor", "selection-background-color")
        or _qss_value(qss, r"QStackedWidget#UtilityStack", "selection-background-color")
        or bg_hex
    )

    bg = QColor(bg_hex)
    fg = QColor(fg_hex)
    sel = QColor(sel_hex)

    if bg.lightness() < 128:
        mid = bg.lighter(130)
        border = bg.lighter(150)
    else:
        mid = bg.darker(115)
        border = bg.darker(130)

    return {
        "bg": bg,
        "fg": fg,
        "sel": sel,
        "caret_line": mid,
        "edge": border,
    }


def set_active_theme(theme_name: str) -> None:
    """Record the currently active theme for palette resolution."""
    global _ACTIVE_THEME
    if theme_name:
        _ACTIVE_THEME = theme_name
        try:
            from editor.Ironica.plugins.python.semantic_highlights import (
                invalidate_semantic_cache,
            )

            invalidate_semantic_cache()
        except Exception:
            pass
        try:
            from editor.Ironica.plugins.cpp.highlighting.tokens import (
                invalidate_semantic_cache as _invalidate_cpp,
            )

            _invalidate_cpp()
        except Exception:
            pass


def active_theme_name() -> str:
    """Return the currently active theme name (defaults to ``"dark"``)."""
    return _ACTIVE_THEME


class RethemeEngine:
    """Class-level engine that applies the active IDE theme."""

    @classmethod
    def current_theme(cls, window) -> str:
        """Return the active theme name reported by *window*."""
        name = getattr(window, "_current_theme_name", None)
        return name if name else active_theme_name()

    @classmethod
    def apply_current(cls, window) -> None:
        """Re-colour every open editor to match the window's active theme."""
        theme_name = cls.current_theme(window)
        set_active_theme(theme_name)
        for editor in cls._iter_editors(window):
            retheme = getattr(editor, "retheme", None)
            if retheme is None:
                continue
            try:
                retheme(theme_name)
            except Exception:
                continue

    @classmethod
    def _iter_editors(cls, window):
        """Yield the ``CodeEditor`` widgets currently open in *window*."""
        hero = getattr(window, "hero_window", None)
        center = getattr(hero, "_text_editor_center", None)
        tabs = getattr(center, "tabs", None)
        if tabs is None:
            return
        for index in range(tabs.count()):
            widget = tabs.widget(index)
            editor = getattr(widget, "editor", None)
            if editor is not None:
                yield editor
                continue
            if getattr(widget, "is_diff_view", False):
                yield widget
