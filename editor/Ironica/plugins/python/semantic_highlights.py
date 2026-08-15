"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Minimal two-path Python highlighting pipeline for DreamStudio.

**Design**

The provider exposes two independent output paths:

1. **Lexer path** (``get_tokens``): full syntax-coloured token stream
   produced entirely by ``tokenize``.  Keywords, strings, comments,
   numbers, operators, and decorator sigils are authoritative here.
   No AST inference is merged into this stream.

2. **Overlay path** (``get_semantic_ranges`` / ``get_semantic_highlights``):
   a *small* whitelist of AST-derived spans painted on top of the base
   lexer via Scintilla indicators.

**Guarantees**

- All offsets are strictly converted to UTF-8 Byte Offsets to perfectly
  align with QScintilla's internal buffer, preventing highlight shifting
  caused by multi-byte characters or non-breaking spaces.
"""

import ast
import io
import keyword
import tokenize
from typing import Dict, List, Optional, Tuple

from editor.Ironica.utils.highlighting_api import (
    ITokenProvider,
    Token,
    TokenStyle,
    styles_from_config,
)
from editor.Ironica.language_engine import LanguageRegistry
from editor.Ironica.retheme import active_theme_name, resolve_language_config

_FSTRING_TOKEN_TYPES = frozenset(
    t
    for t in (
        getattr(tokenize, "FSTRING_START", None),
        getattr(tokenize, "FSTRING_MIDDLE", None),
        getattr(tokenize, "FSTRING_END", None),
    )
    if t is not None
)

# ------------------------------------------------------------------
# UTF-8 Byte Offset Infrastructure
# ------------------------------------------------------------------


def _build_line_offsets(text: str) -> List[int]:
    """Build cumulative line-start offsets in UTF-8 bytes."""
    offsets = [0]
    current_byte = 0
    # io.StringIO(text).readlines() matches tokenize line boundaries
    for line in io.StringIO(text).readlines():
        current_byte += len(line.encode("utf-8"))
        offsets.append(current_byte)
    return offsets


def _tokenize_char_to_byte(
    line_offsets: List[int], line_str: str, row_1: int, char_col: int
) -> int:
    """Convert tokenize 1-indexed row and character col to absolute byte offset."""
    if row_1 - 1 < 0 or row_1 - 1 >= len(line_offsets):
        return -1
    byte_col = len(line_str[:char_col].encode("utf-8"))
    return line_offsets[row_1 - 1] + byte_col


def _build_line_index(tok_stream) -> Dict[int, List]:
    """Group tokens by their start line, preserving stream order.

    Avoids the O(nodes × tokens) quadratic behaviour of re-scanning the
    full token stream once per AST node on large files.
    """
    index: Dict[int, List] = {}
    for tok in tok_stream:
        index.setdefault(tok.start[0], []).append(tok)
    return index


# ------------------------------------------------------------------
# Exclusion-range builder
# ------------------------------------------------------------------


def _build_exclusions(text: str, line_offsets: List[int]) -> List[Tuple[int, int]]:
    exclude: List[Tuple[int, int]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if (
                tok.type in (tokenize.COMMENT, tokenize.STRING)
                or tok.type in _FSTRING_TOKEN_TYPES
            ):
                start_byte = _tokenize_char_to_byte(
                    line_offsets, tok.line, tok.start[0], tok.start[1]
                )
                end_byte = _tokenize_char_to_byte(
                    line_offsets, tok.line, tok.end[0], tok.end[1]
                )
                if start_byte >= 0 and end_byte >= start_byte:
                    exclude.append((start_byte, end_byte))
    except Exception:
        pass
    exclude.sort()
    return exclude


def _in_exclusion(pos: int, length: int, exclude: List[Tuple[int, int]]) -> bool:
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


# ------------------------------------------------------------------
# AST Helpers
# ------------------------------------------------------------------


def _iter_param_args(args: ast.arguments):
    yield from args.posonlyargs
    yield from args.args
    if args.vararg is not None:
        yield args.vararg
    yield from args.kwonlyargs
    if args.kwarg is not None:
        yield args.kwarg


# ==================================================================
# Token provider
# ==================================================================


class PythonSemanticProvider(ITokenProvider):
    def __init__(self) -> None:
        self._cache_text: str = ""
        self._cache_lexical: List[Token] = []
        self._cache_semantic: List[Token] = []
        self._styles: Dict[str, TokenStyle] = {}

    def _get_styles(self) -> Dict[str, TokenStyle]:
        if not self._styles:
            config = LanguageRegistry.get_config("python")
            if config:
                resolved = resolve_language_config(config, active_theme_name())
                self._styles = styles_from_config(resolved)
            else:
                self._styles = styles_from_config({})
        return self._styles

    def invalidate_cache(self) -> None:
        self._cache_text = ""
        self._cache_lexical = []
        self._cache_semantic = []
        self._styles = {}

    def _compute(self, text: str) -> None:
        if text == self._cache_text:
            return

        line_offsets = _build_line_offsets(text)
        exclude = _build_exclusions(text, line_offsets)

        tok_stream = []
        try:
            for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                tok_stream.append(tok)
        except Exception:
            pass

        self._cache_text = text
        self._cache_lexical = self._lex(tok_stream, line_offsets)
        self._cache_semantic = self._semantic(
            text, line_offsets, exclude, tok_stream, _build_line_index(tok_stream)
        )

    def get_tokens(self, text: str) -> List[Token]:
        if not text.strip():
            return []
        self._compute(text)
        return self._cache_lexical

    def _lex(self, tok_stream, line_offsets: List[int]) -> List[Token]:
        tokens: List[Token] = []
        for tok in tok_stream:
            start_byte = _tokenize_char_to_byte(
                line_offsets, tok.line, tok.start[0], tok.start[1]
            )
            end_byte = _tokenize_char_to_byte(
                line_offsets, tok.line, tok.end[0], tok.end[1]
            )
            length = end_byte - start_byte

            if length <= 0 or start_byte < 0:
                continue

            if tok.type == tokenize.COMMENT:
                tokens.append(
                    Token(start_byte, length, self._get_styles()["comment"], "comment")
                )
            elif tok.type == tokenize.STRING or tok.type in _FSTRING_TOKEN_TYPES:
                tokens.append(
                    Token(start_byte, length, self._get_styles()["string"], "string")
                )
            elif tok.type == tokenize.NUMBER:
                tokens.append(
                    Token(start_byte, length, self._get_styles()["number"], "number")
                )
            elif tok.type == tokenize.OP:
                if tok.string == "@":
                    tokens.append(
                        Token(
                            start_byte,
                            length,
                            self._get_styles()["decorator"],
                            "decorator",
                        )
                    )
                else:
                    tokens.append(
                        Token(
                            start_byte,
                            length,
                            self._get_styles()["operator"],
                            "operator",
                        )
                    )
            elif tok.type == tokenize.NAME and keyword.iskeyword(tok.string):
                tokens.append(
                    Token(start_byte, length, self._get_styles()["keyword"], "keyword")
                )
        return tokens

    def _semantic(
        self,
        text: str,
        line_offsets: List[int],
        exclude: List[Tuple[int, int]],
        tok_stream,
        line_index: Dict[int, List],
    ) -> List[Token]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return self._semantic_lexical_fallback(line_offsets, exclude, tok_stream)

        tokens: List[Token] = []
        for node in ast.walk(tree):
            try:
                self._process_node(node, line_offsets, exclude, line_index, tokens)
            except Exception:
                pass
        return self._dedupe(tokens)

    def _semantic_lexical_fallback(
        self, line_offsets: List[int], exclude: List[Tuple[int, int]], tok_stream
    ) -> List[Token]:
        tokens: List[Token] = []
        state = None
        paren_depth = 0

        for tok in tok_stream:
            start_byte = _tokenize_char_to_byte(
                line_offsets, tok.line, tok.start[0], tok.start[1]
            )
            end_byte = _tokenize_char_to_byte(
                line_offsets, tok.line, tok.end[0], tok.end[1]
            )
            length = end_byte - start_byte

            if start_byte < 0 or _in_exclusion(start_byte, length, exclude):
                continue

            if tok.type == tokenize.NAME:
                if tok.string == "def":
                    state = "def"
                elif tok.string == "class":
                    state = "class"
                elif tok.string in ("import", "from"):
                    state = "import"
                elif tok.string in ("self", "cls"):
                    tokens.append(
                        Token(start_byte, length, self._get_styles()["self"], "self")
                    )
                else:
                    if state == "def":
                        tokens.append(
                            Token(
                                start_byte,
                                length,
                                self._get_styles()["function"],
                                "function",
                            )
                        )
                        state = "def_args"
                    elif state == "class":
                        tokens.append(
                            Token(
                                start_byte, length, self._get_styles()["class"], "class"
                            )
                        )
                        state = None
                    elif state == "def_args" and paren_depth > 0:
                        tokens.append(
                            Token(
                                start_byte,
                                length,
                                self._get_styles()["parameter"],
                                "parameter",
                            )
                        )
                    elif state == "import":
                        if tok.string != "as":
                            style = (
                                self._get_styles()["class"]
                                if tok.string[:1].isupper()
                                else self._get_styles()["module"]
                            )
                            tokens.append(
                                Token(start_byte, length, style, "definition")
                            )
            elif tok.type == tokenize.OP:
                if tok.string == "(":
                    paren_depth += 1
                elif tok.string == ")":
                    paren_depth -= 1
                    if paren_depth <= 0 and state == "def_args":
                        state = None
                elif tok.string == ":" and paren_depth <= 0:
                    state = None
            elif tok.type in (tokenize.NEWLINE, tokenize.NL) and paren_depth <= 0:
                state = None
        return self._dedupe(tokens)

    def _dedupe(self, tokens: List[Token]) -> List[Token]:
        if not tokens:
            return []
        ordered = sorted(tokens, key=lambda t: (t.start, -(t.start + t.length)))
        out: List[Token] = []
        last_end = -1
        for tok in ordered:
            end = tok.start + tok.length
            if tok.start >= last_end:
                out.append(tok)
                last_end = end
        return out

    def _add_self_attr_var(
        self,
        target: ast.Attribute,
        line_offsets: List[int],
        exclude: List[Tuple[int, int]],
        tokens: List[Token],
    ) -> None:
        if isinstance(target.value, ast.Name) and target.value.id in ("self", "cls"):
            attr_start = (
                line_offsets[target.lineno - 1]
                + target.col_offset
                + len(target.value.id)
                + 1  # skip "self."
            )
            attr_len = len(target.attr.encode("utf-8"))
            if attr_start >= 0 and not _in_exclusion(attr_start, attr_len, exclude):
                tokens.append(
                    Token(
                        attr_start, attr_len, self._get_styles()["variable"], "variable"
                    )
                )

    def _find_next_name_after_token(self, line_index, lineno: int, keyword_text: str):
        seen_keyword = False
        for tok in line_index.get(lineno, []):
            if tok.type == tokenize.NAME and tok.string == keyword_text:
                seen_keyword = True
                continue
            if seen_keyword and tok.type == tokenize.NAME:
                return tok
        return None

    def _find_importfrom_module_span(self, line_index, lineno: int):
        seen_from = False
        module_start_tok = None
        module_end_tok = None

        for tok in line_index.get(lineno, []):
            if tok.type == tokenize.NAME and tok.string == "from":
                seen_from = True
                continue

            if not seen_from:
                continue

            # This MUST be checked before evaluating a generic tokenize.NAME
            if tok.type == tokenize.NAME and tok.string == "import":
                break

            if tok.type == tokenize.NAME:
                if module_start_tok is None:
                    module_start_tok = tok
                module_end_tok = tok
                continue

            if tok.type == tokenize.OP and tok.string == ".":
                if module_start_tok is not None:
                    module_end_tok = tok
                continue

        if module_start_tok is None or module_end_tok is None:
            return None
        return module_start_tok, module_end_tok

    def _process_node(
        self,
        node: ast.AST,
        line_offsets: List[int],
        exclude,
        line_index,
        tokens: List[Token],
    ) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if not isinstance(node, ast.Lambda):
                name_tok = self._find_next_name_after_token(
                    line_index, node.lineno, "def"
                )
                if name_tok is not None:
                    start = _tokenize_char_to_byte(
                        line_offsets, name_tok.line, name_tok.start[0], name_tok.start[1]
                    )
                    length = len(name_tok.string.encode("utf-8"))
                    if (
                        start >= 0
                        and length > 0
                        and not _in_exclusion(start, length, exclude)
                    ):
                        tokens.append(
                            Token(start, length, self._get_styles()["function"], "function")
                        )

            for arg in _iter_param_args(node.args):
                if not hasattr(arg, "col_offset"):
                    continue
                start = line_offsets[arg.lineno - 1] + arg.col_offset
                length = len(arg.arg.encode("utf-8"))
                if start >= 0 and not _in_exclusion(start, length, exclude):
                    kind = "self" if arg.arg in ("self", "cls") else "parameter"
                    style = self._get_styles()[kind]
                    tokens.append(Token(start, length, style, kind))

        elif isinstance(node, ast.ClassDef):
            name_tok = self._find_next_name_after_token(
                line_index, node.lineno, "class"
            )
            if name_tok is not None:
                start = _tokenize_char_to_byte(
                    line_offsets, name_tok.line, name_tok.start[0], name_tok.start[1]
                )
                length = len(name_tok.string.encode("utf-8"))
                if (
                    start >= 0
                    and length > 0
                    and not _in_exclusion(start, length, exclude)
                ):
                    tokens.append(
                        Token(start, length, self._get_styles()["class"], "class")
                    )

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if not hasattr(alias, "col_offset"):
                    continue
                start = line_offsets[alias.lineno - 1] + alias.col_offset
                length = len(alias.name.encode("utf-8"))
                if start >= 0 and not _in_exclusion(start, length, exclude):
                    tokens.append(
                        Token(start, length, self._get_styles()["module"], "module")
                    )

        elif isinstance(node, ast.ImportFrom):
            mod_span = self._find_importfrom_module_span(line_index, node.lineno)
            if mod_span is not None:
                start_tok, end_tok = mod_span
                start = _tokenize_char_to_byte(
                    line_offsets, start_tok.line, start_tok.start[0], start_tok.start[1]
                )
                end = _tokenize_char_to_byte(
                    line_offsets, end_tok.line, end_tok.end[0], end_tok.end[1]
                )
                length = end - start
                if (
                    start >= 0
                    and length > 0
                    and not _in_exclusion(start, length, exclude)
                ):
                    tokens.append(
                        Token(start, length, self._get_styles()["module"], "module")
                    )

            for alias in node.names:
                if alias.name == "*" or not hasattr(alias, "col_offset"):
                    continue
                start = line_offsets[alias.lineno - 1] + alias.col_offset
                length = len(alias.name.encode("utf-8"))
                if start >= 0 and not _in_exclusion(start, length, exclude):
                    style = (
                        self._get_styles()["class"]
                        if alias.name[:1].isupper()
                        else self._get_styles()["function"]
                    )
                    tokens.append(Token(start, length, style, "definition"))

        # ── Variable definitions ──────────────────────────────────
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    start = line_offsets[target.lineno - 1] + target.col_offset
                    length = len(target.id.encode("utf-8"))
                    if start >= 0 and not _in_exclusion(start, length, exclude):
                        tokens.append(
                            Token(
                                start,
                                length,
                                self._get_styles()["variable"],
                                "variable",
                            )
                        )
                elif isinstance(target, ast.Attribute):
                    self._add_self_attr_var(target, line_offsets, exclude, tokens)

        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name):
                start = line_offsets[target.lineno - 1] + target.col_offset
                length = len(target.id.encode("utf-8"))
                if start >= 0 and not _in_exclusion(start, length, exclude):
                    tokens.append(
                        Token(start, length, self._get_styles()["variable"], "variable")
                    )
            elif isinstance(target, ast.Attribute):
                self._add_self_attr_var(target, line_offsets, exclude, tokens)

        elif isinstance(node, (ast.For, ast.AsyncFor)):
            target = node.target
            if isinstance(target, ast.Name):
                start = line_offsets[target.lineno - 1] + target.col_offset
                length = len(target.id.encode("utf-8"))
                if start >= 0 and not _in_exclusion(start, length, exclude):
                    tokens.append(
                        Token(start, length, self._get_styles()["variable"], "variable")
                    )

        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                opt = item.optional_vars
                if opt is not None and isinstance(opt, ast.Name):
                    start = line_offsets[opt.lineno - 1] + opt.col_offset
                    length = len(opt.id.encode("utf-8"))
                    if start >= 0 and not _in_exclusion(start, length, exclude):
                        tokens.append(
                            Token(
                                start,
                                length,
                                self._get_styles()["variable"],
                                "variable",
                            )
                        )

        # ── Exception clause ─────────────────────────────────────
        elif isinstance(node, ast.ExceptHandler):
            if isinstance(node.type, ast.Name):
                start = line_offsets[node.type.lineno - 1] + node.type.col_offset
                length = len(node.type.id.encode("utf-8"))
                if start >= 0 and not _in_exclusion(start, length, exclude):
                    tokens.append(
                        Token(
                            start, length, self._get_styles()["exception"], "exception"
                        )
                    )
            if node.name:
                name_tok = self._find_next_name_after_token(
                    line_index, node.lineno, "as"
                )
                if name_tok is not None and name_tok.string == node.name:
                    start = _tokenize_char_to_byte(
                        line_offsets,
                        name_tok.line,
                        name_tok.start[0],
                        name_tok.start[1],
                    )
                    length = len(name_tok.string.encode("utf-8"))
                    if start >= 0 and not _in_exclusion(start, length, exclude):
                        tokens.append(
                            Token(
                                start,
                                length,
                                self._get_styles()["variable"],
                                "variable",
                            )
                        )

        elif isinstance(node, ast.Name) and node.id in ("self", "cls"):
            if not hasattr(node, "col_offset"):
                return
            start = line_offsets[node.lineno - 1] + node.col_offset
            length = len(node.id.encode("utf-8"))
            if start >= 0 and not _in_exclusion(start, length, exclude):
                tokens.append(Token(start, length, self._get_styles()["self"], "self"))

    def get_semantic_ranges(self, text: str) -> List[Tuple[int, int, str]]:
        if not text.strip():
            return []
        self._compute(text)
        return [
            (tok.start, tok.length, tok.style.colour) for tok in self._cache_semantic
        ]


_legacy_provider = PythonSemanticProvider()


def get_semantic_highlights(text: str) -> List[Tuple[int, int, str]]:
    return _legacy_provider.get_semantic_ranges(text)


def invalidate_semantic_cache() -> None:
    """Drop the cached style map and semantic token stream.

    The module-level provider caches ``TokenStyle`` objects (whose
    colours are baked in at compute time) together with the token
    stream, so without this hook a theme switch would keep painting
    definitions/classes/variables/modules with the previous theme's
    palette.  The editor calls this on every ``retheme``.
    """
    _legacy_provider.invalidate_cache()
