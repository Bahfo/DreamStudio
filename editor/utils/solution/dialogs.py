"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared themed message boxes for the solution-management flow.

Every dialog in this package used to build its own ``QMessageBox`` with the
same inherit-theme plus center-on-screen pair. Those helpers live here now so
``startup_window``, ``QDreamDialog`` and ``QScafoldController`` share one.
"""

from editor import *

from editor.utils.solution.theme import center_on_screen, inherit_theme


def themed_box(
    parent,
    icon,
    title: str,
    text: str,
    buttons=QMessageBox.StandardButton.Ok,
) -> QMessageBox:
    """Build a themed message box centered on the screen.

    Args:
        parent: Parent widget the theme is inherited from.
        icon: Standard message-box icon.
        title: Dialog window title.
        text: Message body.
        buttons: Standard buttons to show.

    Returns:
        Configured but unshown message box.
    """
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    inherit_theme(box)
    center_on_screen(box)
    return box


def ask_yes_no(parent, title: str, text: str) -> bool:
    """Ask a Yes/No question with a themed dialog.

    Args:
        parent: Parent widget the theme is inherited from.
        title: Dialog window title.
        text: Question body.

    Returns:
        ``True`` when the user answers Yes, ``False`` otherwise.
    """
    reply = themed_box(
        parent,
        QMessageBox.Icon.Question,
        title,
        text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    ).exec()
    return reply == QMessageBox.StandardButton.Yes
