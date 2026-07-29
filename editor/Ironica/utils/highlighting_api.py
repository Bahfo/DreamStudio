"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Core Highlighting API for DreamStudio.

Defines the abstract contract between the QScintilla lexer pipeline
and language-aware token providers.  The editor never guesses what a
token is -- it asks the API.

**Design Principles**

- All token data is returned as exact ``(start_offset, length,
  style_id_or_color)`` tuples.  No partial string matching.
- Style IDs map to QScintilla style indices (integers).  Colors are
  ``#RRGGBB`` hex strings for Scintilla indicator overlays.
- The API is language-agnostic.  Language plugins implement the
  ``ITokenProvider`` interface and register themselves with the
  ``HighlightingRegistry``.
- Callers must use strict word boundaries (``\\b``) or exact ``length``
  properties from the parser.  Substring matching is forbidden.
"""

from __future__ import annotations

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==================================================================
# Token style definitions
# ==================================================================


@dataclass(frozen=True)
class TokenStyle:
    """Maps a semantic token type to a QScintilla style index and
    foreground colour.

    Attributes:
        style_id:   QScintilla style index (0-based).  Style 0 is
                    always the default.
        colour:     ``#RRGGBB`` hex colour string.
        bold:       Whether the token should render in bold.
        italic:     Whether the token should render in italic.
    """

    style_id: int
    colour: str
    bold: bool = False
    italic: bool = False


# Style 0 is reserved as DEFAULT by QScintilla.
STYLE_DEFAULT = TokenStyle(0, "#D4D4D4")

# Mapping from semantic token types to JSON config style keys.
# The JSON files (keywords/*.json) are the single source of truth for colours.
# This map tells `styles_from_config()` how to translate config style names
# into semantic token types used by the highlighting API.
SEMANTIC_TO_CONFIG_KEY: Dict[str, str] = {
    "keyword": "keyword",
    "builtin": "builtin",
    "definition": "definition",
    "class": "class_def",
    "string": "string",
    "number": "number",
    "comment": "comment",
    "decorator": "decorator",
    "self": "additional",
    "operator": "operator",
    "variable": "variable",
    "module": "import",
    "function": "definition",
    "parameter": "additional",
    "constant": "additional",
    "bracket": "bracket",
    "bracket_2": "bracket_2",
    "bracket_3": "bracket_3",
    "exception": "exception",
}

# Fallback colours for semantic types not present in the language config.
_DEFAULT_COLOURS: Dict[str, str] = {
    "keyword": "#C586C0",
    "builtin": "#4FC1FF",
    "definition": "#DCDCAA",
    "class": "#4EC9B0",
    "class_def": "#4EC9B0",
    "string": "#CE9178",
    "number": "#B5CEA8",
    "comment": "#6A9955",
    "decorator": "#D7BA7D",
    "additional": "#569CD6",
    "operator": "#D4D4D4",
    "variable": "#9CDCFE",
    "module": "#4FC1FF",
    "function": "#DCDCAA",
    "parameter": "#9CDCFE",
    "constant": "#569CD6",
    "bracket": "#FFD700",
    "bracket_2": "#C678DD",
    "bracket_3": "#61AFEF",
    "exception": "#FF6B6B",
    "import": "#82AAFF",
}


def styles_from_config(config: dict) -> Dict[str, TokenStyle]:
    """Build a STYLES dict from a language configuration.

    Reads the ``"styles"`` section of *config* and maps each semantic
    token type to its colour.  Semantic types that are not present in
    the config fall back to ``_DEFAULT_COLOURS``.

    Style IDs are assigned sequentially starting at 1 (0 is reserved
    as DEFAULT by QScintilla).
    """
    config_styles = config.get("styles", {})
    style_id = 1
    result: Dict[str, TokenStyle] = {}

    # Collect all unique config keys referenced by semantic types.
    needed_keys: set = set(SEMANTIC_TO_CONFIG_KEY.values())

    # Assign IDs from the config, preserving order from the config dict.
    config_key_to_id: Dict[str, int] = {}
    for key in config_styles:
        if key in needed_keys:
            config_key_to_id[key] = style_id
            style_id += 1

    # Build result for every semantic type.
    for sem_type, config_key in SEMANTIC_TO_CONFIG_KEY.items():
        colour = config_styles.get(config_key) or _DEFAULT_COLOURS.get(sem_type, "#D4D4D4")
        sid = config_key_to_id.get(config_key, 0)
        result[sem_type] = TokenStyle(sid, colour)

    return result


STYLES: Dict[str, TokenStyle] = {}


# ==================================================================
# Token data model
# ==================================================================


@dataclass(frozen=True)
class Token:
    """A single styled token with exact byte boundaries.

    Attributes:
        start:   Start offset in the document (0-indexed byte position).
        length:  Length of the token in bytes.
        style:   The ``TokenStyle`` to apply.
        kind:    Semantic category string (e.g. ``"keyword"``,
                 ``"variable"``, ``"string"``).
    """

    start: int
    length: int
    style: TokenStyle
    kind: str


# ==================================================================
# Abstract token provider interface
# ==================================================================


class ITokenProvider(ABC):
    """Abstract contract for language-aware token providers.

    A token provider analyses source text and returns a list of
    ``Token`` objects with exact ``(start, length, style)`` tuples.

    **Critical contract:**

    - Every token MUST specify its exact ``start`` offset and
      ``length``.  No partial or approximate ranges.
    - Tokens MUST NOT overlap.  If two providers claim the same
      range, the later-registered provider wins.
    - Providers MUST respect string and comment boundaries.  Tokens
      inside strings or comments MUST NOT be returned.
    """

    @abstractmethod
    def get_tokens(self, text: str) -> List[Token]:
        """Return styled tokens for the full document text.

        Args:
            text: The complete editor buffer content.

        Returns:
            A list of ``Token`` objects sorted by start offset.
        """
        return []

    @abstractmethod
    def get_token_at(self, text: str, offset: int) -> Optional[Token]:
        """Return the token covering the given byte offset.

        Args:
            text:   The complete editor buffer content.
            offset: Byte offset (0-indexed) in the document.

        Returns:
            The ``Token`` at *offset*, or ``None`` if no token covers
            that position.
        """
        return None

    @abstractmethod
    def get_semantic_ranges(self, text: str) -> List[Tuple[int, int, str]]:
        """Return ``(start_offset, length, "#RRGGBB")`` tuples for
        Scintilla indicator overlays.

        These are additional semantic highlights (AST-derived,
        Jedi-derived) that layer on top of the base lexer tokens.

        Args:
            text: The complete editor buffer content.

        Returns:
            A list of ``(start, length, colour)`` tuples.
        """
        return []


# ==================================================================
# Highlighting registry — central token provider lookup
# ==================================================================


class HighlightingRegistry:
    """Class-level registry mapping language identifiers to their
    ``ITokenProvider`` implementations.

    All methods are ``@classmethod`` -- no instantiation required.
    """

    _providers: Dict[str, ITokenProvider] = {}

    @classmethod
    def register(cls, lang: str, provider: ITokenProvider) -> None:
        """Register a token provider for *lang*."""
        if lang in cls._providers:
            logger.warning("Overwriting token provider for %r", lang)
        cls._providers[lang] = provider
        logger.info("Registered token provider for %s", lang)

    @classmethod
    def unregister(cls, lang: str) -> bool:
        """Remove the provider for *lang*.  Returns ``True`` if found."""
        if lang not in cls._providers:
            return False
        del cls._providers[lang]
        logger.info("Unregistered token provider for %s", lang)
        return True

    @classmethod
    def get_provider(cls, lang: str) -> Optional[ITokenProvider]:
        """Return the provider for *lang*, or ``None``."""
        return cls._providers.get(lang)

    @classmethod
    def has_provider(cls, lang: str) -> bool:
        return lang in cls._providers

    @classmethod
    def reset(cls) -> None:
        """Clear all registrations (for testing)."""
        cls._providers.clear()


# ==================================================================
# Boundary helpers — enforce strict word boundaries
# ==================================================================


def is_word_boundary(text: str, offset: int) -> bool:
    """Return ``True`` if *offset* is at a word boundary in *text*.

    A word boundary is the transition between a word character
    (``\\w``) and a non-word character (``\\W``), or the start/end
    of the string.
    """
    if offset <= 0 or offset >= len(text):
        return True
    left_alnum = text[offset - 1].isalnum() or text[offset - 1] == "_"
    right_alnum = text[offset].isalnum() or text[offset] == "_"
    return left_alnum != right_alnum


def find_word_at(text: str, offset: int) -> Tuple[int, int]:
    """Return ``(start, end)`` of the word containing *offset*.

    A word is a contiguous sequence of ``\\w`` characters (letters,
    digits, underscores).  This enforces strict word boundaries so
    that ``STYLE_PAREN_3`` is treated as a single token, never split
    into ``STYLE``, ``PAREN``, ``3``.
    """
    if not text or offset < 0 or offset >= len(text):
        return (offset, offset)

    # Expand left.
    start = offset
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
        start -= 1

    # Expand right.
    end = offset
    while end < len(text) and (text[end].isalnum() or text[end] == "_"):
        end += 1

    return (start, end)


def make_token(
    start: int,
    length: int,
    style: TokenStyle,
    kind: str,
) -> Token:
    """Factory function to create a validated ``Token``.

    Raises ``ValueError`` if bounds are invalid.
    """
    if length <= 0:
        raise ValueError(f"Token length must be > 0, got {length}")
    if start < 0:
        raise ValueError(f"Token start must be >= 0, got {start}")
    return Token(start=start, length=length, style=style, kind=kind)
