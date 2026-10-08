"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Call-site and expected-type resolution for context-aware completion.

Cursor-based resolution fails on incomplete code (the AST node being
typed does not exist yet), so contexts resolve lexically against the
current buffer. The translation unit is consulted only for callee
parameter lists, via the same pruned walk used for macro collection.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("DreamStudio.Cpp.CallSite")

_IDENT = re.compile(r"[A-Za-z_]\w*")
_DECL_INIT = re.compile(r"^\s*(?P<type>.+?)\s+(?P<name>[A-Za-z_]\w*)\s*=\s*$")
_FUNC_HEADER = re.compile(
    r"(?P<ret>[A-Za-z_:][\w:<>,\s*&]*?)\s+(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*$"
)
_CONDITION = re.compile(r"\b(?:if|while|assert|static_assert)\s*\(\s*$")
_TYPE_CHARS = re.compile(r"^[\w:<>,\s*&~]+$")
_SKIP_TYPE_WORDS = frozenset(
    {"return", "new", "delete", "case", "throw", "co_return", "co_yield"}
)

_CALLABLE_CODES: Optional[set] = None

_INTEGRAL = frozenset(
    {
        "bool",
        "char",
        "char8_t",
        "char16_t",
        "char32_t",
        "wchar_t",
        "short",
        "int",
        "long",
        "signed",
        "unsigned",
        "size_t",
        "ssize_t",
        "ptrdiff_t",
        "int8_t",
        "uint8_t",
        "int16_t",
        "uint16_t",
        "int32_t",
        "uint32_t",
        "int64_t",
        "uint64_t",
        "intptr_t",
        "uintptr_t",
        "intmax_t",
        "uintmax_t",
        "int_least8_t",
        "int_least16_t",
        "int_least32_t",
        "int_least64_t",
        "uint_least8_t",
        "uint_least16_t",
        "uint_least32_t",
        "uint_least64_t",
        "int_fast8_t",
        "int_fast16_t",
        "int_fast32_t",
        "int_fast64_t",
        "uint_fast8_t",
        "uint_fast16_t",
        "uint_fast32_t",
        "uint_fast64_t",
    }
)
_FLOATING = frozenset({"float", "double", "long double"})
_STRINGY = frozenset(
    {
        "std::string",
        "string",
        "std::string_view",
        "string_view",
        "char*",
        "const char*",
        "char[]",
    }
)

_OVERLOAD_CACHE_BOUND = 16
_overload_cache: Dict[Tuple[str, int, str], List[List[str]]] = {}


@dataclass(frozen=True)
class CallSite:
    """Resolved completion context with optional expected types."""

    kind: str = "plain"
    callee: str = ""
    arg_index: int = 0
    expected: Tuple[str, ...] = ()
    boolean: bool = False


def normalize_type(spelling: str) -> str:
    """Normalize a type spelling for comparison purposes."""
    text = (spelling or "").strip()
    text = re.sub(
        r"\b(?:const|constexpr|volatile|static|inline|virtual|"
        r"friend|mutable|explicit)\b",
        " ",
        text,
    )
    text = text.replace("&", " ").replace("*", " * ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _type_family(normalized: str) -> str:
    """Return the coarse family bucket for a normalized type."""
    base = normalized.replace(" *", "").strip()
    if base in _INTEGRAL:
        return "integral"
    if base in _FLOATING:
        return "floating"
    if base in _STRINGY or normalized in _STRINGY:
        return "string"
    if "*" in normalized:
        return "pointer"
    if base in ("bool",):
        return "integral"
    return "other:" + base


def type_tier(expected: Tuple[str, ...], candidate: str) -> int:
    """Rank a candidate type: 0 exact, 1 family-or-unknown, 2 mismatch."""
    if not expected:
        return 0
    norm_candidate = normalize_type(candidate)
    if not norm_candidate:
        return 1
    for want in expected:
        if normalize_type(want) == norm_candidate:
            return 0
    candidate_family = _type_family(norm_candidate)
    for want in expected:
        if _type_family(normalize_type(want)) == candidate_family:
            return 1
    return 2


def find_call(lines: List[str], line0: int, col0: int) -> Optional[Tuple[str, int]]:
    """Find the enclosing call ``(name, arg_index)`` scanning backwards.

    Balances ``()`` (and ``[]`` inside them) best-effort — incomplete
    code is unbalanced by nature. A ``{``/``[``/``;`` at nesting depth
    zero ends the search: braced initializers spanning backwards are a
    documented non-goal (clang's own results still apply). Bounded.
    """
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: List[str] = []
    commas = 0
    scanned = 0
    line = line0
    first = True
    while line >= 0:
        text = lines[line] if 0 <= line < len(lines) else ""
        segment = text[: max(0, col0)] if first else text
        first = False
        index = len(segment) - 1
        while index >= 0:
            scanned += 1
            if scanned > 4000:
                return None
            char = segment[index]
            if char in ")]}":
                stack.append(char)
            elif char in "([{":
                if not stack:
                    if char != "(":
                        return None
                    head = segment[:index].rstrip()
                    match = _IDENT.search(head[::-1])
                    if not match:
                        return None
                    return (match.group(0)[::-1], commas)
                if pairs.get(stack[-1]) == char:
                    stack.pop()
                elif char == "(":
                    head = segment[:index].rstrip()
                    match = _IDENT.search(head[::-1])
                    if not match:
                        return None
                    return (match.group(0)[::-1], commas)
                # Mismatched opener inside nesting: ignore and continue.
            elif char == "," and not stack:
                commas += 1
            elif char == ";" and not stack:
                return None
            index -= 1
        line -= 1
    return None


def declared_init_type(line_text: str) -> Optional[str]:
    """Return the declared type for ``<type> <name> =`` line ends."""
    match = _DECL_INIT.match(line_text)
    if not match:
        return None
    type_text = match.group("type").strip().rstrip("*&").strip()
    if (
        not type_text
        or "(" in type_text
        or ";" in type_text
        or "=" in type_text
        or not _TYPE_CHARS.match(type_text)
    ):
        return None
    if type_text.split()[-1] in _SKIP_TYPE_WORDS:
        return None
    return type_text or None


def enclosing_return_type(lines: List[str], line0: int, col0: int) -> Optional[str]:
    """Find the enclosing function definition's return type lexically."""
    depth = 0
    line = line0
    first = True
    while line >= 0:
        text = lines[line] if 0 <= line < len(lines) else ""
        segment = text[: max(0, col0)] if first else text
        first = False
        for char in reversed(segment):
            if char == "}":
                depth += 1
            elif char == "{":
                if depth == 0:
                    header = text.split("{")[0]
                    probe = line - 1
                    while (
                        "(" not in header
                        and probe >= max(0, line - 5)
                        and header.strip()
                        and not header.strip().startswith(
                            ("if", "for", "while", "switch", "catch")
                        )
                    ):
                        header = (
                            (lines[probe] if 0 <= probe < len(lines) else "")
                            + " "
                            + header
                        )
                        probe -= 1
                    match = _FUNC_HEADER.search(header + " ")
                    if match:
                        ret = match.group("ret").strip()
                        if ret and ret not in (
                            "if",
                            "for",
                            "while",
                            "switch",
                            "catch",
                            "return",
                        ):
                            return ret
                    return None
                depth -= 1
        line -= 1
    return None


def in_condition(line_text: str, col0: int) -> bool:
    """Return whether the cursor sits in an ``if/while`` condition open."""
    return _CONDITION.search(line_text[: max(0, col0)]) is not None


def buffer_declared_types(source: str) -> Dict[str, str]:
    """Map declared variable names to their lexical types in *source*.

    Completion rows for variables carry no type chunks, so ranking
    consults this map. Only unambiguous ``<type> <name> [=;{]`` shapes
    match — call followers (``f(x)``) are skipped outright.
    """
    found: Dict[str, str] = {}
    if not source:
        return found
    pattern = re.compile(
        r"^\s*(?P<type>[\w:<>,\s*&~]+?)\s+(?P<name>[A-Za-z_]\w*)"
        r"\s*(?P<follow>[=;{])",
        re.MULTILINE,
    )
    for match in pattern.finditer(source):
        type_text = match.group("type").strip().rstrip("*&").strip()
        name = match.group("name")
        if (
            not type_text
            or not _TYPE_CHARS.match(type_text)
            or "(" in type_text
            or type_text.split()[-1] in _SKIP_TYPE_WORDS
            or name in found
        ):
            continue
        found[name] = type_text
    return found


def _callable_codes() -> set:
    """Return libclang value codes for callable declaration kinds."""
    global _CALLABLE_CODES
    if _CALLABLE_CODES is not None:
        return _CALLABLE_CODES
    codes: set = set()
    try:
        from clang.cindex import CursorKind

        for name in (
            "FUNCTION_DECL",
            "FUNCTION_TEMPLATE",
            "CXX_METHOD",
            "CONSTRUCTOR",
            "CXX_CONSTRUCTOR",
            "DESTRUCTOR",
            "CXX_DESTRUCTOR",
        ):
            member = getattr(CursorKind, name, None)
            if member is not None:
                try:
                    codes.add(int(member.value))
                except (TypeError, ValueError):
                    continue
    except Exception:
        pass
    _CALLABLE_CODES = codes
    return codes


def overload_param_types(
    tu, main_path: Optional[str], callee: str, source_hash: int, cache_tag: str
) -> List[List[str]]:
    """Collect parameter-type lists for same-named callables (cached).

    Keyed by translation-unit identity rather than buffer hash: a
    reparse mutates the TU in place, so the entry survives keystrokes
    and rescans happen only after a full reparse mints a new unit.
    Declaration edits between reparses keep slightly stale ranks;
    rows are never hidden by this cache.
    """
    tu_tag = id(tu) if tu is not None else source_hash
    key = (cache_tag, tu_tag, callee)
    cached = _overload_cache.get(key)
    if cached is not None:
        return [list(params) for params in cached]
    collected: List[List[str]] = []
    wanted = _callable_codes()
    if tu is not None and callee and wanted:
        try:
            stack = list(tu.cursor.get_children())
            visited = 0
            while stack and visited < 5000:
                cursor = stack.pop()
                visited += 1
                try:
                    code = int(getattr(cursor.kind, "value", cursor.kind))
                except (TypeError, ValueError):
                    continue
                if code in wanted:
                    if cursor.spelling == callee:
                        try:
                            params = [a.type.spelling for a in cursor.get_arguments()]
                        except Exception:
                            continue
                        if params not in collected:
                            collected.append(params)
                    continue
                try:
                    location = cursor.location
                except Exception:
                    continue
                file_name = ""
                if location is not None and location.file is not None:
                    file_name = str(location.file.name)
                if file_name and main_path and file_name == main_path:
                    try:
                        stack.extend(cursor.get_children())
                    except Exception:
                        continue
        except Exception as exc:
            logger.debug("overload scan unavailable: %s", exc)
    if len(_overload_cache) >= _OVERLOAD_CACHE_BOUND:
        _overload_cache.pop(next(iter(_overload_cache)))
    _overload_cache[key] = [list(params) for params in collected]
    return collected


def resolve(
    lines: List[str],
    line0: int,
    col0: int,
    tu=None,
    main_path: Optional[str] = None,
    source_hash: int = 0,
    cache_tag: str = "",
) -> CallSite:
    """Resolve the completion context for a cursor position."""
    row = lines[line0] if 0 <= line0 < len(lines) else ""
    head = row[: max(0, col0)]
    call = find_call(lines, line0, col0)
    if call is not None:
        name, index = call
        expected: List[str] = []
        params_lists = overload_param_types(tu, main_path, name, source_hash, cache_tag)
        for params in params_lists:
            if 0 <= index < len(params):
                expected.append(params[index])
        return CallSite(
            kind="call_arg", callee=name, arg_index=index, expected=tuple(expected)
        )
    declared = declared_init_type(head)
    if declared is not None and declared != "auto":
        return CallSite(kind="initializer", expected=(declared,))
    if in_condition(row, col0):
        return CallSite(kind="condition", boolean=True, expected=("bool",))
    if re.search(r"\breturn\s+[A-Za-z_]*$", head):
        ret = enclosing_return_type(lines, line0, col0)
        if ret is not None and ret != "void":
            return CallSite(kind="return_value", expected=(ret,))
    return CallSite()


def candidate_type(signature: str) -> str:
    """Extract the salient type from a completion signature string."""
    text = (signature or "").strip()
    if not text or text in ("macro", "header", "directory", "snippet", "text"):
        return ""
    if "(" in text:
        head = text.split("(")[0].rstrip()
        if " " in head:
            return head.rsplit(" ", 1)[0].strip()
        return ""
    return text


def signature_params(signature: str) -> List[str]:
    """Split a rendered call signature into raw parameter spellings."""
    text = (signature or "").strip()
    start = text.find("(")
    end = text.rfind(")")
    if start == -1 or end == -1 or end <= start:
        return []
    inner = text[start + 1 : end]
    params: List[str] = []
    depth = 0
    current: List[str] = []
    for char in inner:
        if char in "<([":
            depth += 1
        elif char in ">)]}":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            params.append("".join(current))
            current = []
        else:
            current.append(char)
    params.append("".join(current))
    return [p.strip() for p in params if p.strip()]


def param_type(param: str) -> str:
    """Strip the parameter name, keeping the declared type."""
    text = (param or "").strip()
    if not text or text == "...":
        return ""
    if " " in text.rstrip():
        return text.rstrip().rsplit(" ", 1)[0].strip()
    return text
