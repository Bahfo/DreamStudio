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

**Semantic refresh path:**
Text changes in the editor trigger ``CodeEditor._on_text_changed()``,
which starts a 300 ms debounce timer.  When the timer fires,
``CodeEditor._apply_semantic_indicators()`` calls
``HighlightingRegistry.get_provider("python").get_semantic_ranges(text)``
to obtain ``(start, length, "#RRGGBB")`` overlay ranges.  These are
painted as ``INDIC_TEXTFORE`` Scintilla indicators on top of the base
``LanguageLexer`` colours.

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
)
from editor.Ironica.plugins.python.semantic_highlights import (
    PythonSemanticProvider,
)

logger = logging.getLogger("DreamStudio.PythonPlugin.Highlighter")


def install(editor, config_path: str) -> None:
    """Register the Python language and install its lexer into *editor*.

    This is the plugin entry point called by ``CodeEditor._apply_theme``
    (or the editor's plugin loader) when a ``.py`` file is opened.

    Semantic overlays are refreshed automatically on text change via
    the editor's debounce timer (see module docstring for the full
    refresh path).  No additional signal wiring is required here --
    ``_apply_semantic_indicators`` looks up the registered provider
    through ``HighlightingRegistry``.

    Args:
        editor:      The ``CodeEditor`` instance.
        config_path: Absolute path to ``keywords/python.json``.
    """
    provider = None  # Future: PythonLanguageProvider()
    LanguageRegistry.register_language(config_path, provider)

    semantic = PythonSemanticProvider()
    HighlightingRegistry.register("python", semantic)

    config = LanguageRegistry.get_config("python")
    if config is None:
        logger.warning("Python config not loaded -- skipping lexer install")
        return

    lexer = LanguageLexer(editor, config)
    lexer.setPaper(editor.paper())
    lexer.setDefaultFont(editor.font())
    editor.setLexer(lexer)

    styles = config.get("styles", {})
    depth_colours = [
        styles.get("bracket", "#FFD700"),
        styles.get("bracket_2", "#C678DD"),
        styles.get("bracket_3", "#61AFEF"),
    ]
    editor._bracket_depth_colours = depth_colours

    logger.info("Python highlighter installed")


def refresh_semantic(editor) -> None:
    """Force an immediate semantic highlight refresh on *editor*.

    This bypasses the debounce timer and is intended for use after
    file loads, goto-definition, rewrite, paste, refactor, or other
    one-shot events that need up-to-date overlays without waiting
    for the timer tick.

    Always clears all indicator slots before reapplying so that stale
    overlays from a previous buffer state are never left behind.

    The normal edit-time refresh path uses the editor's own debounce
    timer and does **not** call this function.
    """
    provider = HighlightingRegistry.get_provider("python")
    if provider is None:
        return
    text = editor.text()
    if not text:
        return

    from PyQt6.Qsci import QsciScintilla  # noqa: F811

    length = len(text)

    # Always clear every indicator slot first.
    for ind in range(8):
        editor.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, ind)
        editor.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, length)

    try:
        ranges = provider.get_semantic_ranges(text)
    except Exception:
        return

    if not ranges:
        return

    colour_map: dict = {}
    slot = 0
    for start, rlen, colour in ranges:
        if colour not in colour_map:
            if slot >= 8:
                break
            colour_map[colour] = slot
            slot += 1
        ind = colour_map[colour]
        editor.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, ind)
        editor.SendScintilla(
            QsciScintilla.SCI_INDICATORFILLRANGE, start, rlen
        )
