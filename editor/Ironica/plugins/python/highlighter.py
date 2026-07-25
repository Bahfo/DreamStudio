"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
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
    provider = None
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
    provider = HighlightingRegistry.get_provider("python")
    if provider is None:
        return
    text = editor.text()
    if not text:
        return

    from PyQt6.Qsci import QsciScintilla  # noqa: F811

    # Scintilla strictly requires byte length to clear the document indicators correctly
    length = len(text.encode("utf-8"))

    # Always clear every indicator slot first.
    for ind in range(8):
        editor.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, ind)
        editor.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, length)

    try:
        provider.invalidate_cache()
    except Exception:
        pass

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
        editor.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE, start, rlen)
