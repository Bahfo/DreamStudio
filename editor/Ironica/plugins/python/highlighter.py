"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Python syntax highlighter plugin for DreamStudio.

Wires the ``ITokenProvider`` interface (from the Core Highlighting API)
to the ``LanguageLexer`` in ``language_engine.py``.  This module is
the single entry point that:

1. Registers the Python language with ``LanguageRegistry``.
2. Registers ``PythonSemanticProvider`` with ``HighlightingRegistry``.
3. Installs the ``LanguageLexer`` into the editor's Scintilla widget.
4. Provides the ``install()`` hook called by ``CodeEditor._apply_theme``.

All highlighting uses exact ``(start_offset, length, colour)`` tuples
with strict word boundaries -- no substring matching.
"""

import logging

from editor.Ironica.language_engine import (
    LanguageLexer,
    LanguageRegistry,
)
from editor.Ironica.utils.highlighting_api import (
    HighlightingRegistry,
    STYLES,
)
from editor.Ironica.plugins.python.semantic_highlights import (
    PythonSemanticProvider,
)

logger = logging.getLogger("DreamStudio.PythonPlugin.Highlighter")


def install(editor, config_path: str) -> None:
    """Register the Python language and install its lexer into *editor*.

    This is the plugin entry point called by ``CodeEditor._apply_theme``
    (or the editor's plugin loader) when a ``.py`` file is opened.

    Args:
        editor:      The ``CodeEditor`` instance.
        config_path: Absolute path to ``keywords/python.json``.
    """
    # 1. Register with LanguageRegistry.
    provider = None  # Future: PythonLanguageProvider()
    LanguageRegistry.register_language(config_path, provider)

    # 2. Register the semantic provider with the HighlightingRegistry.
    semantic = PythonSemanticProvider()
    HighlightingRegistry.register("python", semantic)

    # 3. Install the LanguageLexer into the editor.
    config = LanguageRegistry.get_config("python")
    if config is None:
        logger.warning("Python config not loaded -- skipping lexer install")
        return

    lexer = LanguageLexer(editor, config)
    lexer.setPaper(editor.paper())
    lexer.setDefaultFont(editor.font())
    editor.setLexer(lexer)

    # Apply bracket matching colours from the config.
    styles = config.get("styles", {})
    depth_colours = [
        styles.get("bracket", "#FFD700"),
        styles.get("bracket_2", "#C678DD"),
        styles.get("bracket_3", "#61AFEF"),
    ]
    # Store for later use by the bracket depth manager.
    editor._bracket_depth_colours = depth_colours

    logger.info("Python highlighter installed")
