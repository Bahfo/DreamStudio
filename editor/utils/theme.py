"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Central theme application shared by main window and dialogs.
"""

import logging
import re

logger = logging.getLogger(__name__)


def ensure_font_family(content: str, family: str) -> str:
    """Inject *family* into QSS when no font-family is set."""
    if not content or "font-family" in content:
        return content
    return re.sub(
        r"(QMainWindow\s*\{[^}]*?)(})",
        r"\1  font-family: '%s';\n\2" % family,
        content,
        count=1,
    )


def extract_qss_color(content: str, name: str) -> str:
    """Extract hex color for *name* from QSS content."""
    match = re.search(rf"{re.escape(name)}\s*:\s*(#[0-9a-fA-F]{{3,8}})", content)
    return match.group(1) if match else ""


def apply_theme(window, theme_name: str, content: str | None = None) -> str:
    """Apply *theme_name* QSS to *window* and sync derived state."""
    try:
        registry = getattr(window, "_registry", None)
        manager = registry.get("resource_manager") if registry else None
        if content is None:
            if manager is not None and hasattr(manager, "load_theme"):
                content = manager.load_theme(theme_name)
            else:
                from editor.utils.resource_path import resource_path

                with open(
                    resource_path(f"editor/qss/{theme_name}.qss"), encoding="utf-8"
                ) as handle:
                    content = handle.read()
        try:
            config = registry.get("config") if registry else None
            family = None
            if isinstance(config, dict):
                family = config.get("editor", {}).get("font_family")
            if family:
                content = ensure_font_family(content, family)
        except Exception:
            pass
        window.setStyleSheet(content or "")
        return content or ""
    except Exception as exc:
        logger.warning("Theme apply failed %s: %s", theme_name, exc)
        return ""
