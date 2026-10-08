"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Fast buffer symbol table for instant naming completion.

libclang stays silent or slow in several real situations (cold parse,
broken code, macro bodies), yet the names the user needs are usually
already visible in the open buffer. This module extracts them with a
single linear lexical pass (~1ms) and serves prefix matches instantly
while the semantic engine still computes. Kinds are real
(function/method/field/type/...) — never plain text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import CppCompletion

logger = logging.getLogger("DreamStudio.Cpp.Symbols")

_DEFINE = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)")
_NAMESPACE = re.compile(r"^\s*namespace\s+([A-Za-z_]\w*)")
_RECORD = re.compile(
    r"^\s*(?:class|struct|union|enum(?:\s+class)?)\s+([A-Za-z_]\w*)")
_TYPEDEF = re.compile(r"^\s*typedef\s+.*?\s+([A-Za-z_]\w*)\s*;")
_ALIAS = re.compile(r"^\s*using\s+([A-Za-z_]\w*)\s*=")
_METHOD_DEF = re.compile(
    r"^\s*[\w:<>,\s*&~]+?\s+([A-Za-z_]\w*)::([A-Za-z_]\w*)\s*\(")
_FUNC = re.compile(
    r"^\s*([\w:<>,\s*&~]+?)\s+([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*([{;])?\s*$")
_VAR = re.compile(
    r"^\s*([\w:<>,\s*&~]+?)\s+([A-Za-z_]\w*)\s*(?:=[^;{}]*;|[{;])\s*$")
_ENUM_VALUE = re.compile(r"([A-Za-z_]\w*)(?:\s*=\s*[^,{}]+)?\s*[,}]")
_COMMENT_LINE = re.compile(r"//[^\n]*")

_FAST_CAP = 100


@dataclass(frozen=True)
class Symbol:
    """One named declaration found in the buffer."""

    name: str
    kind: str
    line: int
    scope: str = ""


def _strip_line(line: str) -> str:
    """Remove line comments and string literals for scanning purposes."""
    text = _COMMENT_LINE.sub(" ", line)
    text = re.sub(r"'(?:[^'\\]|\\.)*'", "'c'", text)
    text = re.sub(r'"(?:[^"\\]|\\.)*"', '"s"', text)
    return text


def scan_symbols(source: str) -> List[Symbol]:
    """Extract declarations from *source* in a single linear pass.

    Tracks brace depth with a scope stack so members land in their
    record scope and globals stay global. Multi-line signatures are
    skipped by design (clang covers complete code); malformed lines
    never raise.
    """
    found: List[Symbol] = []
    seen: set = set()

    def add(name: str, kind: str, line: int, scope: str = "") -> None:
        key = (name, kind, scope)
        if name and key not in seen:
            seen.add(key)
            found.append(Symbol(name, kind, line, scope))

    scope_stack: List[Tuple[str, str, int]] = []
    depth = 0
    pending_scope: Optional[Tuple[str, str]] = None
    in_block_comment = False
    lines = source.splitlines() if source else []
    for lineno, raw in enumerate(lines, 1):
        line = raw
        if in_block_comment:
            end = line.find("*/")
            if end == -1:
                continue
            line = line[end + 2:]
            in_block_comment = False
        start = line.find("/*")
        if start != -1:
            end = line.find("*/", start + 2)
            if end == -1:
                line = line[:start]
                in_block_comment = True
            else:
                line = line[:start] + " " + line[end + 2:]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            match = _DEFINE.match(line)
            if match:
                add(match.group(1), "macro", lineno)
            depth += line.count("{") - line.count("}")
            continue
        code = _strip_line(line)
        match = _NAMESPACE.match(code)
        if match:
            add(match.group(1), "namespace", lineno)
            pending_scope = ("namespace", match.group(1))
        else:
            match = _RECORD.match(code)
            if match:
                kind = ("enum" if code.strip().startswith("enum")
                        else "type")
                add(match.group(1), kind, lineno)
                pending_scope = (kind, match.group(1))
            else:
                match = _METHOD_DEF.match(code)
                if match:
                    add(match.group(2), "method", lineno, match.group(1))
                else:
                    match = _FUNC.match(code)
                    if (match and match.group(4) in ("{", ";", None)
                            and re.search(r"[A-Za-z_]", match.group(1))):
                        scope = scope_stack[-1][1] if scope_stack else ""
                        kind = ("method" if scope_stack and scope_stack[-1][0]
                                in ("type",) else "function")
                        add(match.group(2), kind, lineno, scope)
                        for param in _split_params(match.group(3)):
                            if param:
                                add(param, "parameter", lineno, scope)
                    else:
                        match = _TYPEDEF.match(code)
                        if match:
                            add(match.group(1), "type", lineno)
                        else:
                            match = _ALIAS.match(code)
                            if match:
                                add(match.group(1), "type", lineno)
                            else:
                                match = _VAR.match(code)
                                if (match and re.search(
                                        r"[A-Za-z_]", match.group(1))):
                                    scope = (scope_stack[-1][1]
                                             if scope_stack else "")
                                    kind = ("field" if scope_stack
                                            and scope_stack[-1][0] in
                                            ("type",) else "variable")
                                    add(match.group(2), kind, lineno,
                                        scope)
        if scope_stack and scope_stack[-1][0] == "enum":
            for value in _ENUM_VALUE.finditer(code):
                add(value.group(1), "constant", lineno,
                    scope_stack[-1][1])
        opens = code.count("{")
        closes = code.count("}")
        if pending_scope is not None and opens > 0:
            scope_stack.append((pending_scope[0], pending_scope[1],
                                depth + 1))
            pending_scope = None
        depth += opens - closes
        if depth < 0:
            depth = 0
        while scope_stack and scope_stack[-1][2] > depth + 1:
            scope_stack.pop()
        while scope_stack and scope_stack[-1][2] > depth:
            if opens == 0:
                scope_stack.pop()
            else:
                break
    return found


def _split_params(text: str) -> List[str]:
    """Split a parameter list, keeping only bare parameter names."""
    names: List[str] = []
    depth = 0
    current: List[str] = []
    for char in text:
        if char in "<([":
            depth += 1
        elif char in ">]}":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            names.append(_param_name("".join(current)))
            current = []
        else:
            current.append(char)
    names.append(_param_name("".join(current)))
    return [n for n in names if n]


def _param_name(text: str) -> str:
    """Strip a single parameter down to its declared name."""
    cleaned = text.strip()
    cleaned = re.sub(r"\s*=\s*.*$", "", cleaned)
    if not cleaned or cleaned in ("void", "..."):
        return ""
    token = cleaned.rsplit(None, 1)[-1].lstrip("*&")
    if re.fullmatch(r"[A-Za-z_]\w*", token or ""):
        return token
    return ""


@dataclass
class SymbolsCache:
    """Version-gated symbol table for one open buffer."""

    symbols: List[Symbol] = field(default_factory=list)
    _hash: Optional[int] = None

    def update(self, source: str) -> bool:
        """Rescan when *source* changed; return whether it changed."""
        digest = hash(source) if source else 0
        if digest == self._hash:
            return False
        self._hash = digest
        try:
            self.symbols = scan_symbols(source)
        except Exception as exc:
            logger.debug("symbol scan failed: %s", exc)
            self.symbols = []
        return True

    def match(self, prefix: str, limit: int = _FAST_CAP
              ) -> List[CppCompletion]:
        """Return cached rows whose names start with *prefix*."""
        lowered = (prefix or "").lower()
        if not lowered:
            return []
        exact: List[CppCompletion] = []
        rest: List[CppCompletion] = []
        seen: set = set()
        for symbol in self.symbols:
            if symbol.name in seen:
                continue
            if not symbol.name.lower().startswith(lowered):
                continue
            seen.add(symbol.name)
            row = CppCompletion(text=symbol.name, insert_text=symbol.name,
                                kind=symbol.kind,
                                signature=symbol.scope or symbol.kind)
            if symbol.name.startswith(prefix):
                exact.append(row)
            else:
                rest.append(row)
            if len(exact) + len(rest) >= limit:
                break
        exact.sort(key=lambda c: c.text.lower())
        rest.sort(key=lambda c: c.text.lower())
        return exact + rest


def buffer_symbols(source: str) -> Dict[str, str]:
    """Map buffer symbol names to kinds (for ranking boosts)."""
    try:
        return {s.name: s.kind for s in scan_symbols(source)}
    except Exception:
        return {}
