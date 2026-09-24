"""
(C) COPYRIGHT 2026 Excellent TechStacks - All Rights Reserved.

C/C++ semantic highlighting provider for DreamStudio.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from editor import *
from clang.cindex import CursorKind

from editor.Ironica.language_engine import LanguageRegistry
from editor.Ironica.retheme import active_theme_name, resolve_language_config
from editor.Ironica.utils.highlighting_api import (
    ITokenProvider,
    Token,
    TokenStyle,
    styles_from_config,
)

from .clang_adapter import ClangAdapter
from .clang_domain_models import CContext

logger = logging.getLogger("DreamStudio.CSupport.SemanticHighlights")

_RE_IDENTIFIER = re.compile(r"[A-Za-z_]\w*")
_RE_NUMBER = re.compile(
    r"(?:0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[uUlLfF]*"
)
_RE_PREPROCESSOR = re.compile(r"^\s*#\s*[A-Za-z_]\w*")

_FUNCTION_KINDS = {
    CursorKind.FUNCTION_DECL,
    CursorKind.CXX_METHOD,
    CursorKind.FUNCTION_TEMPLATE,
    CursorKind.CONSTRUCTOR,
    CursorKind.DESTRUCTOR,
    CursorKind.CONVERSION_FUNCTION,
}
_TYPE_KINDS = {
    CursorKind.STRUCT_DECL,
    CursorKind.UNION_DECL,
    CursorKind.CLASS_DECL,
    CursorKind.TYPEDEF_DECL,
    CursorKind.TYPE_ALIAS_DECL,
    CursorKind.ENUM_DECL,
}
_REFERENCE_KINDS = {
    CursorKind.CALL_EXPR,
    CursorKind.MEMBER_REF_EXPR,
    CursorKind.DECL_REF_EXPR,
    CursorKind.TYPE_REF,
    CursorKind.NAMESPACE_REF,
    CursorKind.MACRO_INSTANTIATION,
}


def _line_offsets(text: str) -> List[int]:
    """Return UTF-8 byte offsets for every source line."""
    offsets = [0]
    current = 0
    for line in text.splitlines(keepends=True):
        current += len(line.encode("utf-8"))
        offsets.append(current)
    if len(offsets) == 1 or offsets[-1] < len(text.encode("utf-8")):
        offsets.append(len(text.encode("utf-8")))
    return offsets


def _word_span(source_line: str, col_0based: int) -> Optional[Tuple[int, int]]:
    """Return (start_byte_offset_in_line, byte_length) for identifier at 0-based col."""
    for match in _RE_IDENTIFIER.finditer(source_line):
        if match.start() <= col_0based < match.end():
            prefix_bytes = len(source_line[: match.start()].encode("utf-8"))
            word_bytes = len(match.group(0).encode("utf-8"))
            return prefix_bytes, word_bytes
    return None


def _in_ranges(start: int, end: int, ranges: List[Tuple[int, int]]) -> bool:
    """Return whether a byte range overlaps any excluded range."""
    return any(start < item_end and end > item_start for item_start, item_end in ranges)


def _non_code_ranges(text: str) -> List[Tuple[int, int]]:
    """Return byte ranges occupied by C comments and literals."""
    ranges: List[Tuple[int, int]] = []
    index = 0
    length = len(text)
    while index < length:
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            end = length if end == -1 else end
            ranges.append(
                (len(text[:index].encode("utf-8")), len(text[:end].encode("utf-8")))
            )
            index = end
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = length if end == -1 else end + 2
            ranges.append(
                (len(text[:index].encode("utf-8")), len(text[:end].encode("utf-8")))
            )
            index = end
            continue
        if text[index] in ('"', "'"):
            quote = text[index]
            cursor = index + 1
            while cursor < length:
                if text[cursor] == "\\":
                    cursor += 2
                    continue
                if text[cursor] == quote:
                    cursor += 1
                    break
                cursor += 1
            ranges.append(
                (len(text[:index].encode("utf-8")), len(text[:cursor].encode("utf-8")))
            )
            index = cursor
            continue
        index += 1
    return ranges


class CSemanticProvider(ITokenProvider):
    """Provide lexical and libclang-derived C/C++ highlight tokens."""

    def __init__(self, adapter: Optional[ClangAdapter] = None) -> None:
        self._adapter = adapter
        self._cache_text = ""
        self._cache_file_path: Optional[str] = None
        self._cache_lexical: List[Token] = []
        self._cache_semantic: List[Token] = []
        self._styles: Dict[str, TokenStyle] = {}
        self._non_code_ranges: List[Tuple[int, int]] = []

    def _get_styles(self) -> Dict[str, TokenStyle]:
        if not self._styles:
            config = LanguageRegistry.get_config("clang")
            resolved = (
                resolve_language_config(config, active_theme_name()) if config else {}
            )
            self._styles = styles_from_config(resolved)
        return self._styles

    def invalidate_cache(self) -> None:
        self._cache_text = ""
        self._cache_file_path = None
        self._cache_lexical = []
        self._cache_semantic = []
        self._styles = {}
        self._non_code_ranges = []

    def _ensure_adapter(self) -> ClangAdapter:
        if self._adapter is None:
            self._adapter = ClangAdapter()
        return self._adapter

    def _compute(self, text: str, file_path: Optional[str] = None) -> None:
        if text == self._cache_text and file_path == self._cache_file_path:
            return
        self._cache_text = text
        self._cache_file_path = file_path
        self._non_code_ranges = _non_code_ranges(text)
        self._cache_lexical = self._lex(text)
        self._cache_semantic = self._semantic(text, file_path)

    def _token(
        self,
        start: int,
        length: int,
        style_key: str,
        kind: str,
        allow_non_code: bool = False,
    ) -> Optional[Token]:
        if start < 0 or length <= 0:
            return None
        if not allow_non_code and _in_ranges(
            start, start + length, self._non_code_ranges
        ):
            return None
        style = self._get_styles().get(style_key)
        return Token(start, length, style, kind) if style is not None else None

    def _lex(self, text: str) -> List[Token]:
        if not text.strip():
            return []
        tokens: List[Token] = []
        config = LanguageRegistry.get_config("clang") or {}
        keyword_styles: Dict[str, str] = {}
        for category, words in config.get("keywords", {}).items():
            style_key = {
                "keyword": "keyword",
                "builtin": "builtin",
                "exception": "exception",
                "decorator": "decorator",
                "additional": "additional",
            }.get(category)
            if style_key:
                for word in words:
                    keyword_styles.setdefault(word, style_key)

        lines = text.splitlines(keepends=True)
        offsets = _line_offsets(text)
        for line_number, line in enumerate(lines, start=1):
            line_start = offsets[line_number - 1]
            preprocessor = _RE_PREPROCESSOR.match(line)
            if preprocessor:
                token = self._token(
                    line_start + len(line[: preprocessor.start()].encode("utf-8")),
                    len(preprocessor.group(0).strip().encode("utf-8")),
                    "decorator",
                    "preprocessor",
                    allow_non_code=True,
                )
                if token:
                    tokens.append(token)
            for match in re.finditer(
                r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
                line,
                re.DOTALL,
            ):
                token_text = match.group(0)
                style_key = (
                    "comment" if token_text.startswith(("//", "/*")) else "string"
                )
                token = self._token(
                    line_start + len(line[: match.start()].encode("utf-8")),
                    len(token_text.encode("utf-8")),
                    style_key,
                    style_key,
                    allow_non_code=True,
                )
                if token:
                    tokens.append(token)
            for match in _RE_NUMBER.finditer(line):
                token = self._token(
                    line_start + len(line[: match.start()].encode("utf-8")),
                    len(match.group(0).encode("utf-8")),
                    "number",
                    "number",
                )
                if token:
                    tokens.append(token)
            for match in _RE_IDENTIFIER.finditer(line):
                style_key = keyword_styles.get(match.group(0))
                if style_key:
                    token = self._token(
                        line_start + len(line[: match.start()].encode("utf-8")),
                        len(match.group(0).encode("utf-8")),
                        style_key,
                        style_key,
                    )
                    if token:
                        tokens.append(token)
        return self._dedupe(tokens)

    @staticmethod
    def _cursor_style(cursor) -> Optional[str]:
        """Map libclang cursor kinds to valid language configuration style keys."""
        candidate = cursor
        if cursor.kind in _REFERENCE_KINDS:
            try:
                candidate = cursor.referenced or cursor
            except Exception:
                candidate = cursor

        if candidate.kind in _FUNCTION_KINDS:
            return "definition"
        if candidate.kind in _TYPE_KINDS:
            return "class_def"
        if candidate.kind == CursorKind.ENUM_CONSTANT_DECL:
            return "number"
        if candidate.kind in (CursorKind.VAR_DECL, CursorKind.FIELD_DECL):
            return "variable"
        if candidate.kind == CursorKind.PARM_DECL:
            return "additional"
        if candidate.kind in (
            CursorKind.MACRO_DEFINITION,
            CursorKind.MACRO_INSTANTIATION,
        ):
            return "decorator"
        if candidate.kind == CursorKind.NAMESPACE:
            return "class_def"
        return None

    def _semantic(self, text: str, file_path: Optional[str]) -> List[Token]:
        if not text.strip():
            return []
        source_path = file_path or "unsaved_buffer.c"
        context = CContext(
            source_code=text,
            line=1,
            col=1,
            file_path=source_path,
            compile_args=[],
        )
        try:
            translation_unit = self._ensure_adapter()._parse_translation_unit(context)
        except Exception:
            logger.debug("C semantic parse failed", exc_info=True)
            return []
        if translation_unit is None:
            return []

        target_file = translation_unit.get_file(source_path)
        if target_file is None:
            return []
        target_name = target_file.name

        tokens: List[Token] = []
        lines = text.splitlines(keepends=True)
        offsets = _line_offsets(text)

        for cursor in translation_unit.cursor.walk_preorder():
            if cursor.location.file is None or cursor.location.file.name != target_name:
                continue

            style_key = self._cursor_style(cursor)
            if style_key is None:
                continue

            line_idx = cursor.location.line - 1
            col_0based = max(0, cursor.location.column - 1)

            if line_idx < 0 or line_idx >= len(lines):
                continue

            source_line = lines[line_idx]
            span = _word_span(source_line, col_0based)
            if span is None:
                continue

            token_start = offsets[line_idx] + span[0]
            token_len = span[1]

            token = self._token(token_start, token_len, style_key, style_key)
            if token:
                tokens.append(token)

        return self._dedupe(tokens)

    @staticmethod
    def _dedupe(tokens: List[Token]) -> List[Token]:
        """Remove overlapping tokens, giving preference to leaf (specific) tokens."""
        ordered = sorted(tokens, key=lambda t: (t.start, t.length))
        result: List[Token] = []
        last_end = -1
        for token in ordered:
            if token.start >= last_end:
                result.append(token)
                last_end = token.start + token.length
        return result

    def get_tokens(self, text: str) -> List[Token]:
        self._compute(text)
        return list(self._cache_lexical)

    def get_semantic_ranges(
        self, text: str, file_path: Optional[str] = None
    ) -> List[Tuple[int, int, str]]:
        self._compute(text, file_path)
        return [
            (token.start, token.length, token.style.colour)
            for token in self._cache_semantic
            if token.style and hasattr(token.style, "colour")
        ]


_legacy_provider = CSemanticProvider()


def get_semantic_highlights(
    text: str, file_path: Optional[str] = None
) -> List[Tuple[int, int, str]]:
    return _legacy_provider.get_semantic_ranges(text, file_path)


def get_tokens(text: str) -> List[Token]:
    return _legacy_provider.get_tokens(text)


def invalidate_semantic_cache() -> None:
    _legacy_provider.invalidate_cache()
