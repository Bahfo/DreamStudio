"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Shared themed message boxes for the solution-management flow.
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
    """Build a themed message box centered on the screen."""
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    inherit_theme(box)
    center_on_screen(box)
    return box


def ask_yes_no(parent, title: str, text: str) -> bool:
    """Ask a Yes/No question with a themed dialog."""
    reply = themed_box(
        parent,
        QMessageBox.Icon.Question,
        title,
        text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    ).exec()
    return reply == QMessageBox.StandardButton.Yes
