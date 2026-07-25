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
from typing import List, Optional, Tuple

from editor.Ironica.utils.highlighting_api import (
    ITokenProvider,
    Token,
    STYLES,
)

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

    def invalidate_cache(self) -> None:
        self._cache_text = ""
        self._cache_lexical = []
        self._cache_semantic = []

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
        self._cache_semantic = self._semantic(text, line_offsets, exclude, tok_stream)

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
                tokens.append(Token(start_byte, length, STYLES["comment"], "comment"))
            elif tok.type == tokenize.STRING or tok.type in _FSTRING_TOKEN_TYPES:
                tokens.append(Token(start_byte, length, STYLES["string"], "string"))
            elif tok.type == tokenize.NUMBER:
                tokens.append(Token(start_byte, length, STYLES["number"], "number"))
            elif tok.type == tokenize.OP:
                if tok.string == "@":
                    tokens.append(
                        Token(start_byte, length, STYLES["decorator"], "decorator")
                    )
                else:
                    tokens.append(
                        Token(start_byte, length, STYLES["operator"], "operator")
                    )
            elif tok.type == tokenize.NAME and keyword.iskeyword(tok.string):
                tokens.append(Token(start_byte, length, STYLES["keyword"], "keyword"))
        return tokens

    def _semantic(
        self,
        text: str,
        line_offsets: List[int],
        exclude: List[Tuple[int, int]],
        tok_stream,
    ) -> List[Token]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return self._semantic_lexical_fallback(line_offsets, exclude, tok_stream)

        tokens: List[Token] = []
        for node in ast.walk(tree):
            try:
                self._process_node(node, line_offsets, exclude, tok_stream, tokens)
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
                    tokens.append(Token(start_byte, length, STYLES["self"], "self"))
                else:
                    if state == "def":
                        tokens.append(
                            Token(start_byte, length, STYLES["function"], "function")
                        )
                        state = "def_args"
                    elif state == "class":
                        tokens.append(
                            Token(start_byte, length, STYLES["class"], "class")
                        )
                        state = None
                    elif state == "def_args" and paren_depth > 0:
                        tokens.append(
                            Token(start_byte, length, STYLES["parameter"], "parameter")
                        )
                    elif state == "import":
                        if tok.string != "as":
                            style = (
                                STYLES["class"]
                                if tok.string[:1].isupper()
                                else STYLES["module"]
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

    def _find_next_name_after_token(self, tok_stream, lineno: int, keyword_text: str):
        seen_keyword = False
        for tok in tok_stream:
            if tok.start[0] != lineno:
                continue
            if tok.type == tokenize.NAME and tok.string == keyword_text:
                seen_keyword = True
                continue
            if seen_keyword and tok.type == tokenize.NAME:
                return tok
        return None

    def _find_importfrom_module_span(self, tok_stream, lineno: int):
        seen_from = False
        module_start_tok = None
        module_end_tok = None

        for tok in tok_stream:
            if tok.start[0] != lineno:
                continue

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
        tok_stream,
        tokens: List[Token],
    ) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name_tok = self._find_next_name_after_token(tok_stream, node.lineno, "def")
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
                    tokens.append(Token(start, length, STYLES["function"], "function"))

            for arg in _iter_param_args(node.args):
                if not hasattr(arg, "col_offset"):
                    continue
                start = line_offsets[arg.lineno - 1] + arg.col_offset
                length = len(arg.arg.encode("utf-8"))
                if start >= 0 and not _in_exclusion(start, length, exclude):
                    style = (
                        STYLES["self"]
                        if arg.arg in ("self", "cls")
                        else STYLES["parameter"]
                    )
                    tokens.append(Token(start, length, style, "parameter"))

        elif isinstance(node, ast.ClassDef):
            name_tok = self._find_next_name_after_token(
                tok_stream, node.lineno, "class"
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
                    tokens.append(Token(start, length, STYLES["class"], "class"))

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if not hasattr(alias, "col_offset"):
                    continue
                start = line_offsets[alias.lineno - 1] + alias.col_offset
                length = len(alias.name.encode("utf-8"))
                if start >= 0 and not _in_exclusion(start, length, exclude):
                    tokens.append(Token(start, length, STYLES["module"], "module"))

        elif isinstance(node, ast.ImportFrom):
            mod_span = self._find_importfrom_module_span(tok_stream, node.lineno)
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
                    tokens.append(Token(start, length, STYLES["module"], "module"))

            for alias in node.names:
                if alias.name == "*" or not hasattr(alias, "col_offset"):
                    continue
                start = line_offsets[alias.lineno - 1] + alias.col_offset
                length = len(alias.name.encode("utf-8"))
                if start >= 0 and not _in_exclusion(start, length, exclude):
                    style = (
                        STYLES["class"]
                        if alias.name[:1].isupper()
                        else STYLES["function"]
                    )
                    tokens.append(Token(start, length, style, "definition"))

        elif isinstance(node, ast.Name) and node.id in ("self", "cls"):
            if not hasattr(node, "col_offset"):
                return
            start = line_offsets[node.lineno - 1] + node.col_offset
            length = len(node.id.encode("utf-8"))
            if start >= 0 and not _in_exclusion(start, length, exclude):
                tokens.append(Token(start, length, STYLES["self"], "self"))

    def get_token_at(self, text: str, offset: int) -> Optional[Token]:
        tokens = self.get_tokens(text)
        for tok in tokens:
            if tok.start <= offset < tok.start + tok.length:
                return tok
        return None

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
