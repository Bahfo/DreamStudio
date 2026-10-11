"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared theming and screen-centering helpers for the solution-management
widgets (start window, create dialog, scaffold dialog, confirm boxes).

Also loads the standalone start-window QSS files (``editor/qss/startup_*``)
and the create-dialog fallback QSS so no widget embeds stylesheets inline.
"""

from PyQt6.QtWidgets import QApplication, QWidget

from editor.utils.resource_path import resource_path

_STARTUP_QSS_FILES = {
    "dark": "editor/qss/startup_dark.qss",
    "light": "editor/qss/startup_light.qss",
}

_DIALOG_QSS_FILE = "editor/qss/create_dialog.qss"

_HIGHLIGHT_COLORS = {
    "dark": "#5B5BD6",
    "light": "#4F46E5",
}


def normalize_theme_mode(mode: str = "dark") -> str:
    """Normalize a theme mode to ``"dark"`` or ``"light"``.

    Args:
        mode: Raw mode string (case-insensitive).

    Returns:
        ``"light"`` for light input, ``"dark"`` for anything else.
    """
    return "light" if str(mode).strip().lower() == "light" else "dark"


def _read_qss(relative_path: str) -> str:
    """Read a QSS resource file, returning ``""`` when unavailable.

    Args:
        relative_path: Project-relative resource path.

    Returns:
        File content or an empty string on any failure.
    """
    try:
        with open(resource_path(relative_path), encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def load_startup_qss(mode: str = "dark") -> str:
    """Load the standalone start-window QSS for *mode*.

    Args:
        mode: ``"dark"`` or ``"light"`` (anything else falls back to dark).

    Returns:
        QSS content, or ``""`` when neither file is readable.
    """
    content = _read_qss(_STARTUP_QSS_FILES[normalize_theme_mode(mode)])
    if content:
        return content
    return _read_qss(_STARTUP_QSS_FILES["dark"])


def load_dialog_qss() -> str:
    """Load the create-dialog fallback QSS.

    Returns:
        QSS content, or ``""`` when the file is unreadable.
    """
    return _read_qss(_DIALOG_QSS_FILE)


def startup_highlight(mode: str = "dark") -> str:
    """Return the search-match highlight color for *mode*.

    Args:
        mode: ``"dark"`` or ``"light"``.

    Returns:
        Hex color string used for template match highlighting.
    """
    return _HIGHLIGHT_COLORS[normalize_theme_mode(mode)]


def apply_theme(widget: QWidget, registry=None) -> bool:
    """Apply the boot theme's QSS to *widget* when one is available.

    Args:
        widget: The widget to style.
        registry: Optional bootstrap ServiceRegistry holding ``theme_content``.

    Returns:
        ``True`` when a theme was applied, ``False`` otherwise.
    """
    theme_content = None
    try:
        if registry is not None:
            theme_content = registry.get("theme_content")
    except Exception:
        theme_content = None
    if theme_content:
        widget.setStyleSheet(theme_content)
        return True
    return False


def inherit_theme(widget: QWidget) -> bool:
    """Copy the nearest ancestor's theme QSS onto *widget*.

    :class:`~PyQt6.QtWidgets.QDialog` and other top-level popups do not
    cascade the parent window's stylesheet on their own, so the theme is
    duplicated explicitly from the nearest parent whose ``styleSheet()`` is
    non-empty.

    Args:
        widget: The dialog/box to style from its ancestor window.

    Returns:
        ``True`` when a stylesheet was copied, ``False`` otherwise.
    """
    qss = ""
    try:
        parent = (
            widget.parentWidget()
            if hasattr(widget, "parentWidget")
            else widget.parent()
        )
        while parent is not None and not qss:
            qss = parent.styleSheet() or ""
            parent = (
                parent.parentWidget()
                if hasattr(parent, "parentWidget")
                else parent.parent()
            )
    except Exception:
        qss = ""
    if qss:
        widget.setStyleSheet(qss)
        return True
    return False


def center_on_screen(widget: QWidget) -> None:
    """Move *widget* to the center of its current screen geometry.

    Args:
        widget: The dialog or message box to reposition.
    """
    try:
        screen = widget.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        frame = widget.frameGeometry()
        widget.move(
            geometry.center().x() - frame.width() // 2,
            geometry.center().y() - frame.height() // 2,
        )
    except Exception:
        try:
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            geometry = screen.availableGeometry()
            widget.move(
                geometry.center().x() - widget.width() // 2,
                geometry.center().y() - widget.height() // 2,
            )
        except Exception:
            pass


def center_on_screen_show(widget: QWidget, event) -> None:
    """Center a dialog from ``showEvent`` then pass the event through.

    Args:
        widget: The dialog being shown.
        event: The original ``QShowEvent``.
    """
    center_on_screen(widget)
    super(widget.__class__, widget).showEvent(event)
