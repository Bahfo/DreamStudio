"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Language-agnostic file outline backend.  Parses source code into a tree of
``OutlineNode`` objects that the GUI renders.  The outliner knows nothing
about who supplies the source — it only receives text and produces structure.

Language plugins register their own parsers via :func:`register_parser`.
When a file is opened the IDE calls :func:`build_outline` which dispatches
to the registered parser for the file's language.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data models
# ------------------------------------------------------------------


class SymbolKind(Enum):
    """Category of outline symbol."""

    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    DECORATOR = "decorator"
    PROPERTY = "property"
    IMPORT = "import"


@dataclass
class OutlineNode:
    """A single node in the file outline tree.

    Attributes:
        name: Display name (e.g. ``"MyClass"``).
        kind: Symbol category.
        line_start: 0-indexed line where the symbol begins.
        line_end: 0-indexed line where the symbol ends (inclusive).
        col_start: 0-indexed column offset.
        children: Nested symbols (methods inside a class, etc.).
        detail: Optional extra text (e.g. type annotation, signature).
    """

    name: str
    kind: SymbolKind
    line_start: int = 0
    line_end: int = 0
    col_start: int = 0
    children: list[OutlineNode] = field(default_factory=list)
    detail: str = ""


@dataclass
class OutlineResult:
    """Result of parsing a source file for outline symbols.

    Attributes:
        root: Top-level ``OutlineNode`` representing the file itself.
        language: Language identifier (e.g. ``"python"``).
    """

    root: OutlineNode
    language: str = ""


# ------------------------------------------------------------------
# Parser registry
# ------------------------------------------------------------------

_PARSERS: dict[str, Callable[[str], OutlineResult]] = {}


def register_parser(language: str, parser: Callable[[str], OutlineResult]) -> None:
    """Register an outline parser for *language*.

    Args:
        language: Language identifier matching the editor's ``current_lang``.
        parser: Callable that takes source code and returns ``OutlineResult``.
    """
    _PARSERS[language] = parser


def get_parser(language: str) -> Optional[Callable[[str], OutlineResult]]:
    """Return the registered parser for *language*, or ``None``."""
    return _PARSERS.get(language)


def supported_languages() -> list[str]:
    """Return language identifiers that have outline parsers."""
    return list(_PARSERS.keys())


def build_outline(
    source_code: str, language: str, filename: str = ""
) -> Optional[OutlineResult]:
    """Build an outline tree from *source_code*.

    Args:
        source_code: Raw source text.
        language: Language identifier.
        filename: Optional filename for the root node label.

    Returns:
        ``OutlineResult`` if a parser is registered and parsing succeeds,
        or ``None`` if no parser is available or parsing fails.
    """
    parser = get_parser(language)
    if parser is None:
        return None

    try:
        result = parser(source_code)
        if result.root.name == "" and filename:
            result.root.name = filename
        return result
    except Exception as exc:
        logger.debug("Outline parsing failed for %s: %s", language, exc)
        return None


def unregister_parser(language: str) -> bool:
    """Remove the outline parser for *language*.

    Args:
        language: Language identifier whose parser should be removed.

    Returns:
        ``True`` when a parser was registered and has been removed.
    """
    return _PARSERS.pop(language, None) is not None
