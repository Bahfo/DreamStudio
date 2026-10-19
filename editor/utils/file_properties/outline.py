"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Language-agnostic file outline backend.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


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
    """A single node in the file outline tree."""

    name: str
    kind: SymbolKind
    line_start: int = 0
    line_end: int = 0
    col_start: int = 0
    children: list[OutlineNode] = field(default_factory=list)
    detail: str = ""


@dataclass
class OutlineResult:
    """Result of parsing a source file for outline symbols."""

    root: OutlineNode
    language: str = ""


_PARSERS: dict[str, Callable[[str], OutlineResult]] = {}


def register_parser(language: str, parser: Callable[[str], OutlineResult]) -> None:
    """Register an outline parser for *language*."""
    _PARSERS[language] = parser


def get_parser(language: str) -> Optional[Callable[[str], OutlineResult]]:
    """Return the registered parser for *language*, or ``None``."""
    return _PARSERS.get(language)


def build_outline(
    source_code: str, language: str, filename: str = ""
) -> Optional[OutlineResult]:
    """Build an outline tree from *source_code*."""
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
    """Remove the outline parser for *language*."""
    return _PARSERS.pop(language, None) is not None
