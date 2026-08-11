"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Registration bridge between the Python language plugin and DreamStudio's
LanguageRegistry.  This module is the only file in the plugin package that
imports from the editor core -- it keeps the provider code fully decoupled.
"""

import os
import logging

from editor.Ironica.language_engine import LanguageRegistry
from editor.utils.notifications.notification_manager import get_notification_manager

logger = logging.getLogger(__name__)

_KEYWORDS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "keywords")
)
_PYTHON_JSON = os.path.join(_KEYWORDS_DIR, "python.json")
_BASH_JSON = os.path.join(_KEYWORDS_DIR, "bash.json")
_CMD_JSON = os.path.join(_KEYWORDS_DIR, "cmd.json")


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
            get_notification_manager().add_success(
                "Python Support Loaded",
                "Python language support initialized successfully.",
                "Plugins",
            )
        else:
            logger.warning("Python language plugin registration returned False")
            get_notification_manager().add_warning(
                "Python Plugin Warning",
                "Python language plugin could not be registered. "
                "Code intelligence may be unavailable.",
                "Plugins",
            )
        return success

    except Exception as exc:
        logger.error("Failed to register Python language plugin: %s", exc)
        get_notification_manager().add_error(
            "Python Plugin Error",
            f"Python language plugin failed to initialize: {exc}. "
            "Code intelligence disabled.",
            "Plugins",
        )
        return False


def unregister_python_language() -> bool:
    """Remove the Python language from the LanguageRegistry.

    Returns:
        ``True`` if Python was registered and has been removed.
    """
    return LanguageRegistry.unregister_language("python")


def register_bash_plugin() -> bool:
    """Register the Bash language with the LanguageRegistry.

    Loads the Bash keyword/style JSON config.
    Returns:
        ``True`` on success, ``False`` on any failure.
    """
    try:
        success = LanguageRegistry.register_language(_BASH_JSON)
        if success:
            logger.info("Bash language plugin registered successfully")
            get_notification_manager().add_success(
                "Bash Support Loaded",
                "Bash language support initialized successfully.",
                "Plugins",
            )
        else:
            logger.warning("Bash language plugin registration returned False")
            get_notification_manager().add_warning(
                "Bash Plugin Warning",
                "Bash language plugin could not be registered. "
                "Syntax highlighting may be unavailable.",
                "Plugins",
            )
        return success
    except Exception as exc:
        logger.error("Failed to register Bash language plugin: %s", exc)
        get_notification_manager().add_error(
            "Bash Plugin Error",
            f"Bash language plugin failed to initialize: {exc}.",
            "Plugins",
        )
        return False


def register_cmd_plugin() -> bool:
    """Register the Batch language with the LanguageRegistry.

    Loads the Batch keyword/style JSON config.

    Returns:
        ``True`` on success, ``False`` on any failure.
    """
    try:
        success = LanguageRegistry.register_language(_CMD_JSON)
        if success:
            logger.info("Batch language plugin registered successfully")
            get_notification_manager().add_success(
                "Batch Support Loaded",
                "Batch language support initialized successfully.",
                "Plugins",
            )
        else:
            logger.warning("Batch language plugin registration returned False")
            get_notification_manager().add_warning(
                "Batch Plugin Warning",
                "Batch language plugin could not be registered. "
                "Syntax highlighting may be unavailable.",
                "Plugins",
            )
        return success
    except Exception as exc:
        logger.error("Failed to register Batch language plugin: %s", exc)
        get_notification_manager().add_error(
            "Batch Plugin Error",
            f"Batch language plugin failed to initialize: {exc}.",
            "Plugins",
        )
        return False
