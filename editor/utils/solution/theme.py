"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared theming and screen-centering helpers for the solution-management
widgets (start window, create dialog, scaffold dialog, confirm boxes).

The IDE theme (a QSS string registered as ``theme_content`` during boot) is
applied here so every dialer the solution flow creates matches whatever theme
the IDE is running with, and every popup is centered on the screen.
"""

from PyQt6.QtWidgets import QApplication, QWidget


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
