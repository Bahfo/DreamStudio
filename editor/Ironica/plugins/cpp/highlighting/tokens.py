"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

libclang semantic overlay for C++ buffers.

The JSON lexer keeps keywords, strings, comments, numbers, and
operators; this module adds identifier intelligence on top via
Scintilla indicator ranges: every ``IDENTIFIER`` token resolves its
declaration through ``token.cursor`` and paints in that symbol's
theme color (VSCode-style semantic tokens). Offsets are absolute
UTF-8 bytes, self-validated against token spellings so libclang
column units can never shift highlights.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("DreamStudio.Cpp.Highlighting")

_INCLUDE_PATH = re.compile(
    r"^\s*#\s*(?:include_next|include|import)\s*[<\"](?P<path>[^<>\"']*)"
)

_CATEGORY_BY_CURSOR = {
    "FUNCTION_DECL": "definition",
    "FUNCTION_TEMPLATE": "definition",
    "CXX_METHOD": "definition",
    "CONSTRUCTOR": "definition",
    "CXX_CONSTRUCTOR": "definition",
    "DESTRUCTOR": "definition",
    "CXX_DESTRUCTOR": "definition",
    "CXX_CONVERSION": "definition",
    "CLASS_DECL": "class_def",
    "STRUCT_DECL": "class_def",
    "UNION_DECL": "class_def",
    "ENUM_DECL": "class_def",
    "CLASS_TEMPLATE": "class_def",
    "CLASS_TEMPLATE_PARTIAL_SPEC": "class_def",
    "TYPEDEF_DECL": "class_def",
    "TYPE_ALIAS_DECL": "class_def",
    "TYPE_ALIAS_TEMPLATE_DECL": "class_def",
    "TYPE_REF": "class_def",
    "TEMPLATE_REF": "class_def",
    "NAMESPACE": "import",
    "NAMESPACE_REF": "import",
    "NAMESPACE_ALIAS": "import",
    "VAR_DECL": "variable",
    "PARM_DECL": "variable",
    "FIELD_DECL": "variable",
    "ENUM_CONSTANT_DECL": "number",
    "MACRO_DEFINITION": "decorator",
    "MACRO_INSTANTIATION": "decorator",
    "INCLUSION_DIRECTIVE": "decorator",
    "CONCEPT_DECL": "keyword",
    "FRIEND_DECL": "keyword",
}

_RICH_FALLBACK = {
    "definition": "#DCDCAA",
    "class_def": "#4EC9B0",
    "import": "#CE9178",
    "variable": "#9CDCFE",
    "number": "#B5CEA8",
    "decorator": "#C586C0",
    "keyword": "#C586C0",
    "header": "#8A76A5",
}

_CATEGORY_STYLE_KEYS = {
    "definition": ("definition",),
    "class_def": ("class_def",),
    "import": ("import",),
    "variable": ("variable",),
    "number": ("number",),
    "decorator": ("decorator",),
    "keyword": ("keyword",),
    "header": ("header",),
}

_MAX_TOKENS = 40000
_MAX_VISITED = 60000

_WORD_BYTE = frozenset(
    b"abcdefghijklmnopqrstuvwxyz" b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)


_REFERENCE_KINDS = frozenset(
    {
        "DECL_REF_EXPR",
        "MEMBER_REF_EXPR",
        "MEMBER_REF",
        "TYPE_REF",
        "NAMESPACE_REF",
        "TEMPLATE_REF",
        "OVERLOADED_DECL_REF",
        "CALL_EXPR",
    }
)

_CALL_KEYWORDS = frozenset(
    {
        "if", "for", "while", "switch", "catch", "return", "sizeof",
        "decltype", "typeid", "static_assert", "requires", "co_await",
        "co_return", "co_yield", "new", "delete", "throw", "using",
    }
)

_DEFINE_RE = re.compile(r"^\s*#\s*define\s+(?P<name>[A-Za-z_]\w*)")
_TYPE_DECL_RE = re.compile(
    r"\b(?:class|struct|union|enum(?:\s+class|\s+struct)?|namespace|typename)\s+"
    r"(?P<name>[A-Za-z_]\w*)"
)
_CALL_RE = re.compile(r"\b(?P<name>[A-Za-z_]\w*)\s*(?=\()")
_UPPER_RE = re.compile(r"\b(?P<name>[A-Z][A-Z0-9_]{1,})\b")
_VAR_ASSIGN_RE = re.compile(r"\b(?P<name>[A-Za-z_]\w*)\s*(?=[=;,\[])")
_TRAILING_DECL_RE = re.compile(
    r"^\s*(?:[A-Za-z_][\w:<>*&]*\s+)+(?P<name>[A-Za-z_]\w*)\s*\(?\s*$"
)
_FOR_RANGE_RE = re.compile(r"\bfor\s*\([^;:]*[:]\s*(?P<rest>[^)]*)\)")


def _kind_name(cursor) -> str:
    """Return the cursor-kind name for enum members and int codes."""
    if cursor is None or isinstance(cursor, str):
        return ""
    kind = getattr(cursor, "kind", None)
    name = getattr(kind, "name", None)
    if isinstance(name, str) and name:
        return name
    try:
        from clang.cindex import CursorKind

        return str(CursorKind(int(kind))).split(".")[-1]
    except (TypeError, ValueError):
        return ""


def _resolve_decl(cursor):
    """Follow references to the declaration behind a use-site cursor.

    Args:
        cursor: libclang cursor attached to an identifier token.

    Returns:
        The resolved declaration cursor, or the original cursor when
        it already is a declaration or cannot be followed further.
    """
    node = cursor
    for _ in range(4):
        if node is None or isinstance(node, str):
            break
        try:
            kind = _kind_name(node)
        except Exception:
            break
        if not kind or kind not in _REFERENCE_KINDS:
            break
        try:
            target = node.referenced
        except Exception:
            break
        if target is None or target == node:
            break
        node = target
    return node


def _line_byte_offsets(source: str) -> List[int]:
    """Return cumulative UTF-8 byte offsets of each line start."""
    offsets = [0]
    current = 0
    for line in source.splitlines(keepends=True):
        current += len(line.encode("utf-8"))
        offsets.append(current)
    return offsets


def _resolve_colors(
    config: Optional[dict], theme_name: Optional[str] = None
) -> Dict[str, str]:
    """Resolve theme colors for categories from a language config.

    Args:
        config: Raw language config with ``styles``/``palette`` sections.
        theme_name: Active IDE theme; resolved automatically when omitted.

    Returns:
        Category-to-hex mapping with hard fallbacks for missing keys.
    """
    colors = dict(_RICH_FALLBACK)
    if isinstance(config, dict):
        try:
            from editor.Ironica.retheme import (
                active_theme_name,
                resolve_language_config,
            )

            resolved = resolve_language_config(
                config, theme_name or active_theme_name()
            )
            styles = resolved.get("styles") or {}
            for category, keys in _CATEGORY_STYLE_KEYS.items():
                for key in keys:
                    raw = styles.get(key)
                    if isinstance(raw, str) and raw.startswith("#"):
                        colors[category] = raw
                        break
            return colors
        except Exception:
            pass
    if not isinstance(config, dict):
        return colors
    styles = config.get("styles") or {}
    palette = config.get("palette") or {}
    for category, keys in _CATEGORY_STYLE_KEYS.items():
        for key in keys:
            raw = styles.get(key)
            if isinstance(raw, str):
                if raw.startswith("#"):
                    colors[category] = raw
                    break
                elif raw in palette:
                    colors[category] = palette[raw]
                    break
    return colors


def invalidate_semantic_cache() -> None:
    """Drop cached highlight state (colors resolve per call)."""
    return None


def _token_kind_name(token) -> str:
    """Return the token-kind name for enum members and int codes."""
    kind = getattr(token, "kind", None)
    name = getattr(kind, "name", None)
    if isinstance(name, str) and name:
        return name
    try:
        from clang.cindex import TokenKind

        return str(TokenKind(int(kind))).split(".")[-1]
    except (TypeError, ValueError):
        return ""


def _locate(line_bytes: bytes, spelling: bytes, hint: int) -> int:
    """Locate *spelling* in *line_bytes* nearest the hinted column.

    Only word-boundary matches count, so earlier same-word prefixes
    can never collide regardless of libclang column units. Returns
    the byte column or ``-1``.
    """
    if not spelling or hint < 0:
        return -1
    best = -1
    best_distance = None
    start = line_bytes.find(spelling)
    while start != -1:
        before = line_bytes[start - 1] if start > 0 else 0
        after = (
            line_bytes[start + len(spelling)]
            if start + len(spelling) < len(line_bytes)
            else 0
        )
        if before not in _WORD_BYTE and after not in _WORD_BYTE:
            distance = abs(start - hint)
            if best == -1 or distance < best_distance:
                best = start
                best_distance = distance
                if distance == 0:
                    break
        start = line_bytes.find(spelling, start + 1)
    return best


def _include_ranges(
    source: str, line_offsets: List[int], colors: dict
) -> List[Tuple[int, int, str]]:
    """Paint library names after ``#include`` in the header color.

    The lexer colors the whole ``<…>``/``"…"`` span as a string; this
    overlay recolors just the path so headers read distinctly.
    """
    color = colors.get("header")
    if not color:
        return []
    out: List[Tuple[int, int, str]] = []
    for index, line in enumerate(source.split("\n")):
        match = _INCLUDE_PATH.match(line)
        if not match:
            continue
        path = match.group("path")
        if not path:
            continue
        byte_col = len(line[: match.start("path")].encode("utf-8"))
        start = line_offsets[index] + byte_col
        out.append((start, len(path.encode("utf-8")), color))
    return out


def _guess_category(spelling: str, after: str) -> Optional[str]:
    """Guess a highlight category when libclang gives no declaration.

    Args:
        spelling: Identifier text at the use site.
        after: Source text following the identifier on its line.

    Returns:
        Category name, or ``None`` for keywords that the lexer owns.
    """
    if not spelling or spelling in _CALL_KEYWORDS:
        return None
    if after.lstrip().startswith("("):
        return "definition"
    if len(spelling) >= 2 and spelling.isupper():
        return "decorator"
    if spelling[0].isupper():
        return "class_def"
    return "variable"


def _exclusion_ranges(source: str) -> List[Tuple[int, int]]:
    """Return ``(start, end)`` byte ranges covering strings/comments."""
    encoded = source.encode("utf-8")
    out: List[Tuple[int, int]] = []
    i = 0
    n = len(encoded)
    block_start = -1
    in_str = 0
    str_start = 0
    while i < n:
        byte = encoded[i]
        if block_start >= 0:
            if byte == 0x2A and i + 1 < n and encoded[i + 1] == 0x2F:
                out.append((block_start, i + 2))
                block_start = -1
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if byte == 0x5C and i + 1 < n:
                i += 2
                continue
            if byte == in_str:
                out.append((str_start, i + 1))
                in_str = 0
            i += 1
            continue
        if byte == 0x2F and i + 1 < n:
            nxt = encoded[i + 1]
            if nxt == 0x2F:
                eol = encoded.find(b"\n", i)
                out.append((i, n if eol == -1 else eol))
                i = n if eol == -1 else eol
                continue
            if nxt == 0x2A:
                block_start = i
                i += 2
                continue
        if byte in (0x22, 0x27):
            in_str = byte
            str_start = i
            i += 1
            continue
        i += 1
    if block_start >= 0:
        out.append((block_start, n))
    out.sort()
    return out


def _in_exclusion(pos: int, length: int, exclude: List[Tuple[int, int]]) -> bool:
    """Return ``True`` when ``[pos, pos+length)`` touches an exclusion."""
    end = pos + length
    lo, hi = 0, len(exclude) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        e_start, e_end = exclude[mid]
        if pos >= e_end:
            lo = mid + 1
        elif end <= e_start:
            hi = mid - 1
        else:
            return True
    return False


def _fallback_ranges(
    source: str, line_offsets: List[int], colors: Dict[str, str]
) -> List[Tuple[int, int, str]]:
    """Compute regex highlights when libclang is unavailable.

    Args:
        source: Full editor buffer content.
        line_offsets: Cumulative UTF-8 byte offsets per line.
        colors: Category-to-color mapping from the active theme.

    Returns:
        Sorted, deduplicated overlay ranges.
    """
    out: List[Tuple[int, int, str]] = []
    exclude = _exclusion_ranges(source)
    raw_lines = source.split("\n")

    def _emit(line_no: int, char_col: int, text: str, category: str) -> None:
        color = colors.get(category)
        if not color or not text:
            return
        start = line_offsets[line_no] + len(
            raw_lines[line_no][:char_col].encode("utf-8")
        )
        length = len(text.encode("utf-8"))
        if length <= 0 or _in_exclusion(start, length, exclude):
            return
        out.append((start, length, color))

    for line_no, line in enumerate(raw_lines):
        match = _DEFINE_RE.match(line)
        if match:
            _emit(line_no, match.start("name"), match.group("name"), "decorator")
        for match in _TYPE_DECL_RE.finditer(line):
            category = "import" if "namespace" in match.group(0) else "class_def"
            _emit(line_no, match.start("name"), match.group("name"), category)
        for match in _CALL_RE.finditer(line):
            name = match.group("name")
            if name in _CALL_KEYWORDS:
                continue
            _emit(line_no, match.start("name"), name, "definition")
        for match in _UPPER_RE.finditer(line):
            _emit(line_no, match.start("name"), match.group("name"), "decorator")
        for match in _VAR_ASSIGN_RE.finditer(line):
            name = match.group("name")
            if name in _CALL_KEYWORDS:
                continue
            _emit(line_no, match.start("name"), name, "variable")
        if not line.lstrip().startswith("#"):
            match = _TRAILING_DECL_RE.match(line)
            if match:
                name = match.group("name")
                if name not in _CALL_KEYWORDS:
                    after = line[match.end("name"):]
                    category = (
                        "definition" if "(" in after else "variable"
                    )
                    _emit(line_no, match.start("name"), name, category)
    try:
        out.extend(_include_ranges(source, line_offsets, colors))
    except Exception as exc:
        logger.debug("include ranges failed: %s", exc)
    out.sort()
    deduped: List[Tuple[int, int, str]] = []
    last_end = -1
    for start, length, color in out:
        if start >= last_end:
            deduped.append((start, length, color))
            last_end = start + length
    return deduped


def _merge_with_fallback(
    primary: List[Tuple[int, int, str]],
    fallback: List[Tuple[int, int, str]],
) -> List[Tuple[int, int, str]]:
    """Merge libclang ranges over regex fallback ranges.

    Args:
        primary: Authoritative libclang ranges winning any overlap.
        fallback: Regex ranges filling gaps libclang missed.

    Returns:
        Sorted, non-overlapping overlay ranges.
    """
    if not fallback:
        combined = sorted(primary)
    elif not primary:
        combined = sorted(fallback)
    else:
        spans = sorted((s, s + n) for s, n, _ in primary)
        kept = list(primary)
        for start, length, color in fallback:
            end = start + length
            overlap = False
            for p_start, p_end in spans:
                if start < p_end and end > p_start:
                    overlap = True
                    break
                if p_start >= end:
                    break
            if not overlap:
                kept.append((start, length, color))
        combined = sorted(kept)
    merged: List[Tuple[int, int, str]] = []
    last_end = -1
    for start, length, color in combined:
        if start >= last_end:
            merged.append((start, length, color))
            last_end = start + length
    return merged


def compute_highlights(
    source: str, tu, colors: Dict[str, str], main_path: Optional[str] = None
) -> List[Tuple[int, int, str]]:
    """Compute ``(start, length, color)`` overlays for identifier tokens.

    Args:
        source: Full editor buffer content.
        tu: Parsed translation unit for token and cursor resolution.
        colors: Category-to-color mapping from the active theme.
        main_path: Main-file path; tokens from headers are skipped.

    Returns:
        Sorted, non-overlapping overlay ranges with UTF-8 byte offsets.
    """
    if not source or not source.strip():
        return []
    line_offsets = _line_byte_offsets(source)
    if tu is None:
        return _fallback_ranges(source, line_offsets, colors)
    try:
        from clang.cindex import TokenGroup

        tokens = TokenGroup.get_tokens(tu, tu.cursor.extent)
    except Exception as exc:
        logger.debug("token walk unavailable: %s", exc)
        return _fallback_ranges(source, line_offsets, colors)
    raw_lines = source.split("\n")
    encoded = [line.encode("utf-8") for line in raw_lines]
    out: List[Tuple[int, int, str]] = []
    last_end = -1
    visited = 0
    for token in tokens:
        visited += 1
        if visited > _MAX_VISITED or len(out) >= _MAX_TOKENS:
            break
        try:
            if _token_kind_name(token) != "IDENTIFIER":
                continue
            spelling = token.spelling or ""
            if not spelling:
                continue
            location = token.location
            line_1 = int(location.line)
            column_1 = int(location.column)
            if line_1 < 1 or line_1 > len(raw_lines):
                continue
            if main_path:
                try:
                    token_file = location.file
                    if token_file is not None and str(token_file.name) != main_path:
                        continue
                except Exception:
                    pass
            line_bytes = encoded[line_1 - 1]
            wanted = spelling.encode("utf-8")
            column = _locate(line_bytes, wanted, column_1 - 1)
            if column == -1:
                continue
            start = line_offsets[line_1 - 1] + column
            length = len(wanted)
            if start < last_end:
                continue
            try:
                resolved = _resolve_decl(token.cursor)
                category = _CATEGORY_BY_CURSOR.get(_kind_name(resolved))
            except Exception:
                category = None
            if category is None:
                try:
                    after = raw_lines[line_1 - 1][
                        len(line_bytes[:column].decode("utf-8", "ignore"))
                        + len(spelling):
                    ]
                except Exception:
                    after = ""
                category = _guess_category(spelling, after)
            if category is None:
                continue
            color = colors.get(category)
            if not color:
                continue
            out.append((start, length, color))
            last_end = start + length
        except Exception:
            continue
    if not out:
        return _fallback_ranges(source, line_offsets, colors)
    try:
        out.extend(_include_ranges(source, line_offsets, colors))
    except Exception as exc:
        logger.debug("include ranges failed: %s", exc)
    out.sort()
    deduped: List[Tuple[int, int, str]] = []
    last_end = -1
    for start, length, color in out:
        if start >= last_end:
            deduped.append((start, length, color))
            last_end = start + length
    try:
        fallback = _fallback_ranges(source, line_offsets, colors)
    except Exception as exc:
        logger.debug("fallback ranges failed: %s", exc)
        return deduped
    return _merge_with_fallback(deduped, fallback)
