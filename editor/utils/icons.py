"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Single QIcon resolution path with cache and missing-asset warnings.
"""

import logging
import os

logger = logging.getLogger(__name__)

_ICON_CACHE: dict[str, object] = {}


def icon_path(icon: str) -> str | None:
    """Resolve project-relative icon *icon* to absolute path or None."""
    if not icon:
        return None
    try:
        from editor.utils.resource_path import resource_path

        resolved = resource_path(icon)
    except Exception:
        return None
    if resolved and os.path.isfile(resolved):
        return resolved
    logger.warning("Icon not found: %s", icon)
    return None


def get_qicon(icon: str):
    """Return cached QIcon for *icon*, or empty QIcon when missing."""
    from PyQt6.QtGui import QIcon

    if not icon:
        return QIcon()
    cached = _ICON_CACHE.get(icon)
    if cached is not None:
        return cached
    resolved = icon_path(icon)
    qicon = QIcon(resolved) if resolved else QIcon()
    _ICON_CACHE[icon] = qicon
    return qicon


def clear_icon_cache() -> None:
    """Drop cached QIcons, mainly for tests."""
    _ICON_CACHE.clear()
