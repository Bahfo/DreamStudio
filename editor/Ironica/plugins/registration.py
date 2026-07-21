"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Registration bridge between the Python language plugin and DreamStudio's
LanguageRegistry.  This module is the only file in the plugin package that
imports from the editor core -- it keeps the provider code fully decoupled.
"""

import os
import logging

from editor.Ironica.language_engine import LanguageRegistry

logger = logging.getLogger(__name__)

_KEYWORDS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "keywords")
)
_PYTHON_JSON = os.path.join(_KEYWORDS_DIR, "python.json")


def register_python_language() -> bool:
    """Register the Python language with the LanguageRegistry.

    Loads the Python keyword/style JSON config and attaches a fully
    wired ``PythonLanguageProvider`` backed by Jedi.

    Returns:
        ``True`` on success, ``False`` on any failure.
    """
    try:
        from editor.Ironica.plugins.python.jedi_adapter import JediAdapter
        from editor.Ironica.plugins.python.provider import PythonLanguageProvider
        from editor.Ironica.plugins.python.cache import LanguageCache

        adapter = JediAdapter()
        cache = LanguageCache()
        provider = PythonLanguageProvider(adapter=adapter, cache=cache)

        success = LanguageRegistry.register_language(_PYTHON_JSON, provider)
        if success:
            logger.info("Python language plugin registered successfully")
        else:
            logger.warning("Python language plugin registration returned False")
        return success

    except Exception as exc:
        logger.error("Failed to register Python language plugin: %s", exc)
        return False


def unregister_python_language() -> bool:
    """Remove the Python language from the LanguageRegistry.

    Returns:
        ``True`` if Python was registered and has been removed.
    """
    return LanguageRegistry.unregister_language("python")
