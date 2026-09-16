"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Dynamic IDE theme engine for DreamStudio.

This module is the single runtime hook that keeps the code editors in
sync with the active IDE theme.  It discovers every theme shipped under
``editor/qss`` and ``editor/Ironica/themes``, resolves symbolic
syntax-highlight colours (e.g. ``KEYWORD_COLOR``) to concrete hex values
for the active theme, and re-colours every open editor on demand.

Public entry points:

- ``RethemeEngine`` — class-level facade used by the IDE.  Callers use
  ``set_theme``, ``toggle`` or ``apply_current`` and never instantiate it.
- ``resolve_language_config`` — used by the lexer pipeline to turn a
  language config's symbolic ``styles`` into concrete hex colours.
- ``editor_colors`` — extracts the base editor colours (background,
  foreground, selection) from the active QSS file.
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


def available_themes() -> List[str]:
    """Return the sorted names of all shipped IDE themes (no extension)."""
    try:
        names = [
            f[:-4]
            for f in os.listdir(_QSS_DIR)
            if f.endswith(".qss") and f != "resource_manager.qss"
        ]
    except OSError:
        names = []
    return sorted(names)


def theme_palette(theme_name: str = _DEFAULT_THEME) -> Dict[str, str]:
    """Load the syntax-colour palette for *theme_name* from the themes dir.

    Returns an empty dict when the theme file is missing or malformed.
    """
    path = os.path.join(_THEMES_DIR, f"{theme_name}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    palette = data.get("palette", {}) if isinstance(data, dict) else {}
    return {key: value for key, value in palette.items() if is_hex_color(value)}


def resolve_colour(
    value: object, palette: Optional[Dict[str, str]] = None, default: str = ""
) -> str:
    """Resolve *value* to a concrete hex colour string.

    Literal hex values pass through unchanged.  Symbolic names (e.g.
    ``KEYWORD_COLOR``) are looked up in *palette*; unknown names fall
    back to *default* and ultimately to *value* itself.
    """
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
    """Return a copy of *config* with every symbolic style resolved to hex.

    The theme palette takes precedence over the language config's own
    ``"palette"`` section so an active IDE theme always wins.  Key order
    and all non-style keys are preserved, keeping lexer style indices
    stable across theme switches.
    """
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
    """Extract a single QSS property value from the first matching rule.

    The property is guarded by a negative lookbehind so that generic
    names like ``color`` or ``background-color`` never match inside a
    longer property such as ``selection-color``.
    """
    pattern = re.compile(
        rf"{selector_re}\s*\{{[^}}]*(?<![\w-]){property_name}\s*:\s*([^;\s}}]+)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(qss)
    return match.group(1).strip() if match else None


def editor_colors(theme_name: str) -> Dict[str, QColor]:
    """Return the base editor colours for *theme_name* as ``QColor`` values.

    Values are read from the active QSS ``QWidget#CodeEditor`` rule, so
    the stylesheet remains the single source of truth.  Derived colours
    (caret line, margin border) are computed from the background.
    """
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
    """Record the currently active theme for palette resolution.

    The Python plugin's semantic-highlight cache is invalidated on every
    theme switch so cached overlay tokens never keep the palette of a
    previously active theme.
    """
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


def active_theme_name() -> str:
    """Return the currently active theme name (defaults to ``"dark"``)."""
    return _ACTIVE_THEME


@dataclass(frozen=True)
class ThemePalette:
    """Immutable view of one theme's syntax-colour palette."""

    theme: str
    name: str
    palette: Dict[str, str]


class RethemeEngine:
    """Class-level engine that applies and toggles the IDE theme.

    The engine discovers every theme shipped with DreamStudio, exposes
    them in sorted order, and re-colours all open code editors so the
    base editor surface and the syntax lexer both follow the active
    theme.  It is stateless apart from the module-level active theme
    name used by the resolution helpers.

    **Usage** (from the main window)::

        from editor.Ironica.retheme import RethemeEngine

        RethemeEngine.apply_current(window)
        next_theme = RethemeEngine.toggle(window)
    """

    @classmethod
    def themes(cls) -> List[str]:
        """Return the sorted names of all available themes."""
        return available_themes()

    @classmethod
    def current_theme(cls, window) -> str:
        """Return the active theme name reported by *window*."""
        name = getattr(window, "_current_theme_name", None)
        return name if name else active_theme_name()

    @classmethod
    def set_theme(cls, window, theme_name: str) -> str:
        """Apply *theme_name* through *window* and re-colour all editors.

        Args:
            window: The ``DreamStudio`` main window (or a compatible stub).
            theme_name: A theme name from ``themes()``.

        Returns:
            The theme name that was applied.
        """
        setter = getattr(window, "_set_theme_by_name", None)
        if setter is None:
            set_active_theme(theme_name)
            return theme_name
        setter(theme_name)
        cls.apply_current(window)
        return theme_name

    @classmethod
    def toggle(cls, window) -> str:
        """Cycle to the next theme and apply it.

        Returns:
            The newly applied theme name.
        """
        themes = cls.themes()
        if not themes:
            return active_theme_name()
        current = cls.current_theme(window)
        if current in themes:
            next_theme = themes[(themes.index(current) + 1) % len(themes)]
        else:
            next_theme = themes[0]
        return cls.set_theme(window, next_theme)

    @classmethod
    def apply_current(cls, window) -> None:
        """Re-colour every open editor to match the window's active theme.

        Each editor's ``retheme`` method re-applies the base surface
        colours (paper, foreground, caret, margins, selection) and the
        syntax lexer palette, then invalidates the semantic provider
        cache so overlay colours refresh too.
        """
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
