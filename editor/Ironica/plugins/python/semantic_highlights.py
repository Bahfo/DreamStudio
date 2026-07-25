"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Two-stage Python syntax highlighting pipeline for DreamStudio.

**Layer separation**

The provider serves two distinct output paths that must never mix:

1. **Lexer path** (``get_tokens``): full syntax-coloured token stream
   covering keywords, strings, comments, numbers, operators, decorators
   *and* semantic identifiers (definitions, params, imports, self/cls,
   constants, calls).  The ``LanguageLexer`` or any consumer that
   needs complete document colouring calls this method.

2. **Overlay path** (``get_semantic_ranges`` / ``get_semantic_highlights``):
   semantic-only spans that layer *on top of* the base lexer colours.
   This path must **never** emit keywords, strings, comments, numbers,
   operators, or decorator tokens — those are owned by the lexer layer.
   Only AST-derived definition names, parameters, imports, self/cls
   references, constants, and call names are returned.

Keeping these two layers separate prevents the overlay system from
repainting the full document, which would fight with the base lexer
and cause wrong colours after goto-definition, rewrite, or file switch.

On ``SyntaxError`` (incomplete code during live typing), only lexical
tokens are returned by the lexer path.  The overlay path returns an
empty list because the AST could not be built.

**Design guarantees:**
- All offsets are computed via ``_line_col_to_offset`` with a
  precomputed ``line_offsets`` array for O(1) lookups.
- No ``text.find()`` substring heuristics are used.  Every token
  specifies its exact ``start`` and ``length`` from AST positions or
  deterministic offset computation.
- Token interiors inside strings/comments are excluded from semantic
  overlays via the ``tokenize`` module.
- The same keyword always resolves to the same style and colour
  regardless of file content or editor action (no per-file drift).
"""

import ast
import builtins
import io
import keyword
import tokenize
from typing import List, Optional, Tuple

from editor.Ironica.utils.highlighting_api import (
    ITokenProvider,
    Token,
    STYLES,
)

# ------------------------------------------------------------------
# Priority levels for overlap resolution
# ------------------------------------------------------------------
_PRIORITY_SEMANTIC = 10
_PRIORITY_LEXICAL = 5

# ------------------------------------------------------------------
# Builtins (for distinguishing `len(...)` / `hasattr(...)` / etc. from
# ordinary user-defined function calls in the lexer's fallback colouring)
# ------------------------------------------------------------------
_BUILTIN_NAMES = frozenset(dir(builtins))

# ------------------------------------------------------------------
# PEP 701 (Python 3.12+) split f-strings into FSTRING_START /
# FSTRING_MIDDLE / FSTRING_END tokens instead of one STRING token.
# The embedded ``{expr}`` portions are tokenized as ordinary code
# tokens (NAME, OP, NUMBER, ...) and are intentionally left alone so
# they highlight exactly like regular code. Only the literal
# start/middle/end pieces need to be treated as string material.
# On Python < 3.12 these attributes don't exist, so this set is empty
# and f-strings fall through to the single-STRING branch as before.
# ------------------------------------------------------------------
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
# Line-offset infrastructure
# ------------------------------------------------------------------


def _build_line_offsets(text: str) -> List[int]:
    """Build cumulative line-start offsets for O(1) line/col conversion.

    ``line_offsets[0]`` is always 0.  ``line_offsets[i]`` is the byte
    offset of the start of line *i* (0-indexed).
    """
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _line_col_to_offset(line_offsets: List[int], lineno: int, col_offset: int) -> int:
    """Convert 0-indexed ``(line, col)`` to a flat byte offset.

    Returns -1 if *lineno* is out of range.
    """
    if lineno < 0 or lineno >= len(line_offsets):
        return -1
    return line_offsets[lineno] + col_offset


# ------------------------------------------------------------------
# Exclusion-range builder (strings + comments) via tokenize
# ------------------------------------------------------------------


def _build_exclusions(text: str, line_offsets: List[int]) -> List[Tuple[int, int]]:
    """Build a sorted list of ``(start, end)`` exclusion ranges from
    comments and string literals in *text*.

    Tokenize is authoritative for Python string/comment boundaries.
    """
    exclude: List[Tuple[int, int]] = []
    try:
        for tok_type, tok_string, start, end, line in tokenize.generate_tokens(
            io.StringIO(text).readline
        ):
            if (
                tok_type in (tokenize.COMMENT, tokenize.STRING)
                or tok_type in _FSTRING_TOKEN_TYPES
            ):
                flat_start = _line_col_to_offset(line_offsets, start[0] - 1, start[1])
                flat_end = _line_col_to_offset(line_offsets, end[0] - 1, end[1])
                if flat_start >= 0 and flat_end >= flat_start:
                    exclude.append((flat_start, flat_end))
    except tokenize.TokenError:
        pass
    exclude.sort()
    return exclude


def _in_exclusion(pos: int, length: int, exclude: List[Tuple[int, int]]) -> bool:
    """Binary search: does ``[pos, pos+length)`` overlap any exclusion?"""
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
# Deterministic offset helpers (no text.find)
# ------------------------------------------------------------------


def _name_after_keyword(
    text: str,
    line_offsets: List[int],
    lineno: int,
    col_offset: int,
    keyword_len: int,
) -> Optional[int]:
    """Return the byte offset of the name immediately after a keyword
    at ``(lineno, col_offset)``.

    *keyword_len* is the length of the keyword token (e.g. 3 for
    ``def``, 5 for ``class`` or ``async``).  Whitespace between the
    keyword and the name is skipped.

    Returns ``None`` if the offset cannot be resolved.
    """
    start = _line_col_to_offset(line_offsets, lineno - 1, col_offset)
    if start < 0 or start >= len(text):
        return None
    pos = start + keyword_len
    while pos < len(text) and text[pos] in " \t":
        pos += 1
    return pos if pos < len(text) else None


def _decorator_name_span(
    deco: ast.AST, line_offsets: List[int]
) -> Optional[Tuple[int, int]]:
    """Return ``(start, length)`` for the callable name of a decorator.

    Handles plain decorators (``@staticmethod``), dotted decorators
    (``@app.route``), and decorator calls (``@lru_cache(maxsize=2)``,
    ``@app.route("/x")``) by unwrapping to the underlying ``Call.func``
    first, then taking the right-most ``Name``/``Attribute`` segment.

    Returns ``None`` if the span cannot be resolved.
    """
    target = deco.func if isinstance(deco, ast.Call) else deco
    if isinstance(target, ast.Name) and hasattr(target, "col_offset"):
        start = _line_col_to_offset(line_offsets, target.lineno - 1, target.col_offset)
        return (start, len(target.id)) if start >= 0 else None
    if isinstance(target, ast.Attribute) and hasattr(target, "end_col_offset"):
        end = _line_col_to_offset(
            line_offsets, target.end_lineno - 1, target.end_col_offset
        )
        start = end - len(target.attr)
        return (start, len(target.attr)) if start >= 0 else None
    return None


def _iter_param_args(args: ast.arguments):
    """Yield every ``ast.arg`` declared on a function/lambda signature.

    ``ast.arguments`` splits parameters across several lists depending
    on how they're declared (positional-only before ``/``, regular,
    ``*args``, keyword-only after ``*``, ``**kwargs``). Iterating only
    ``args.args`` -- a common oversight -- silently drops positional-only
    params, keyword-only params, ``*args`` and ``**kwargs`` from
    highlighting, which is especially noticeable in modern, heavily
    type-hinted function signatures.
    """
    yield from args.posonlyargs
    yield from args.args
    if args.vararg is not None:
        yield args.vararg
    yield from args.kwonlyargs
    if args.kwarg is not None:
        yield args.kwarg


def _module_after_from(
    text: str,
    line_offsets: List[int],
    lineno: int,
    col_offset: int,
) -> Optional[int]:
    """Return the byte offset of the module name after a ``from`` keyword.

    Skips whitespace and leading dots for relative imports.
    Returns ``None`` if the offset cannot be resolved.
    """
    start = _line_col_to_offset(line_offsets, lineno - 1, col_offset)
    if start < 0 or start >= len(text):
        return None
    pos = start + 4  # skip 'from'
    while pos < len(text) and text[pos] in " \t.":
        pos += 1
    return pos if pos < len(text) else None


# ------------------------------------------------------------------
# Same-layer overlap resolution
# ------------------------------------------------------------------


def _dedupe_overlaps(tokens: List[Token]) -> List[Token]:
    """Resolve overlapping tokens produced *within a single layer*.

    A handful of AST node shapes are visited more than once for the
    same span -- most notably a called attribute like ``obj.method()``,
    where both the ``Call`` handling and the plain ``Attribute``
    handling independently emit a token for ``method``. Without this
    step both tokens (with two different colours) would be handed to
    the caller for the identical span.

    Sorted by start offset; on an exact tie, the token that was
    produced first wins (Python's sort is stable, and ``ast.walk`` is
    breadth-first, so a ``Call`` node is always processed -- and its
    token appended -- before the ``Attribute`` node nested inside it).
    """
    ordered = sorted(tokens, key=lambda t: t.start)
    result: List[Token] = []
    last_end = 0
    for tok in ordered:
        if tok.start >= last_end:
            result.append(tok)
            last_end = tok.start + tok.length
    return result


# ------------------------------------------------------------------
# Token merge
# ------------------------------------------------------------------


def _merge_tokens(lexical: List[Token], semantic: List[Token]) -> List[Token]:
    """Merge lexical and semantic tokens into a non-overlapping list.

    Semantic tokens have higher priority and override lexical tokens
    at overlapping positions.  Output is sorted by start offset.
    """
    tagged: List[Tuple[int, int, Token, int]] = []
    for tok in lexical:
        tagged.append((tok.start, tok.start + tok.length, tok, _PRIORITY_LEXICAL))
    for tok in semantic:
        tagged.append((tok.start, tok.start + tok.length, tok, _PRIORITY_SEMANTIC))

    # Sort by start, then by priority descending (semantic wins ties)
    tagged.sort(key=lambda x: (x[0], -x[3]))

    result: List[Token] = []
    last_end = 0
    for start, end, tok, _ in tagged:
        if start >= last_end:
            result.append(tok)
            last_end = end

    return result


# ==================================================================
# Two-stage token provider
# ==================================================================


class PythonSemanticProvider(ITokenProvider):
    """Two-layer Python syntax highlighter.

    **Lexer layer** (``get_tokens``):
        Full syntax-coloured token stream.  ``tokenize`` produces exact
        spans for keywords, strings, comments, numbers, operators, and
        decorators.  ``ast`` produces exact spans for definitions,
        parameters, imports, self/cls, constants, and calls.  The two
        layers are merged with semantic tokens winning overlaps.

    **Overlay layer** (``get_semantic_ranges``):
        Semantic-only spans for the Scintilla indicator system.
        Returns *only* AST-derived tokens: definition names, parameters,
        imports, self/cls, constants, and call names.  Never returns
        keywords, strings, comments, numbers, operators, or decorators.

    On ``SyntaxError`` the semantic stage is skipped.  The lexer layer
    still returns lexical tokens.  The overlay layer returns an empty
    list.
    """

    def __init__(self) -> None:
        self._cache_text: str = ""
        self._cache_lexical: List[Token] = []
        self._cache_semantic: List[Token] = []
        self._cache_merged: List[Token] = []

    def _compute(self, text: str) -> None:
        """Compute both layers once, cache for reuse."""
        if text == self._cache_text:
            return
        line_offsets = _build_line_offsets(text)
        exclude = _build_exclusions(text, line_offsets)
        lexical = self._lex(text, line_offsets, exclude)
        semantic = self._semantic(text, line_offsets, exclude)
        merged = _merge_tokens(lexical, semantic)
        self._cache_text = text
        self._cache_lexical = lexical
        self._cache_semantic = semantic
        self._cache_merged = merged

    # ------------------------------------------------------------------
    # Lexer path: full syntax-coloured token stream
    # ------------------------------------------------------------------

    def get_tokens(self, text: str) -> List[Token]:
        """Return the full syntax-coloured token stream (lexer path).

        Covers every meaningful byte: keywords, strings, comments,
        numbers, operators, decorators *plus* definitions, parameters,
        imports, self/cls, constants, and calls.  Semantic tokens win
        at overlapping positions.
        """
        if not text.strip():
            return []
        self._compute(text)
        return self._cache_merged

    # ------------------------------------------------------------------
    # Stage 1: Lexical
    # ------------------------------------------------------------------

    def _lex(
        self,
        text: str,
        line_offsets: List[int],
        exclude: List[Tuple[int, int]],
    ) -> List[Token]:
        """Lexical tokenization via Python's ``tokenize`` module.

        Produces exact spans for keywords, strings, comments, numbers,
        operators, and the ``@`` decorator sign.  Identifier names are
        left to the semantic stage.
        """
        tokens: List[Token] = []
        try:
            for tok_type, tok_string, start, end, _line in tokenize.generate_tokens(
                io.StringIO(text).readline
            ):
                flat_start = _line_col_to_offset(line_offsets, start[0] - 1, start[1])
                flat_end = _line_col_to_offset(line_offsets, end[0] - 1, end[1])
                length = flat_end - flat_start

                if length <= 0 or flat_start < 0:
                    continue

                if tok_type == tokenize.COMMENT:
                    tokens.append(
                        Token(flat_start, length, STYLES["comment"], "comment")
                    )
                elif tok_type == tokenize.STRING:
                    tokens.append(Token(flat_start, length, STYLES["string"], "string"))
                elif tok_type in _FSTRING_TOKEN_TYPES:
                    # PEP 701 (3.12+): quote/prefix delimiters and the
                    # literal text pieces of an f-string. The embedded
                    # {expr} tokens are NOT of this type and fall
                    # through to the normal NAME/OP/NUMBER handling
                    # below, so expressions inside f-strings continue
                    # to highlight like ordinary code.
                    tokens.append(Token(flat_start, length, STYLES["string"], "string"))
                elif tok_type == tokenize.NUMBER:
                    tokens.append(Token(flat_start, length, STYLES["number"], "number"))
                elif tok_type == tokenize.OP:
                    if tok_string == "@":
                        tokens.append(
                            Token(
                                flat_start,
                                length,
                                STYLES["decorator"],
                                "decorator",
                            )
                        )
                    else:
                        tokens.append(
                            Token(
                                flat_start,
                                length,
                                STYLES["operator"],
                                "operator",
                            )
                        )
                elif tok_type == tokenize.NAME:
                    if keyword.iskeyword(tok_string):
                        tokens.append(
                            Token(
                                flat_start,
                                length,
                                STYLES["keyword"],
                                "keyword",
                            )
                        )
        except tokenize.TokenError:
            pass
        return tokens

    # ------------------------------------------------------------------
    # Stage 2: Semantic
    # ------------------------------------------------------------------

    def _semantic(
        self,
        text: str,
        line_offsets: List[int],
        exclude: List[Tuple[int, int]],
    ) -> List[Token]:
        """Semantic analysis via Python's ``ast`` module.

        Produces exact spans for definitions, parameters, imports,
        self/cls, constants, and function/class calls.  Tokens inside
        string/comment exclusion ranges are skipped.

        Returns an empty list on ``SyntaxError`` (incomplete input).
        """
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []

        tokens: List[Token] = []
        for node in ast.walk(tree):
            try:
                self._process_node(node, text, line_offsets, exclude, tokens)
            except Exception:
                pass
        return _dedupe_overlaps(tokens)

    def _process_node(
        self,
        node: ast.AST,
        text: str,
        line_offsets: List[int],
        exclude: List[Tuple[int, int]],
        tokens: List[Token],
    ) -> None:
        """Dispatch a single AST node and append semantic tokens."""

        # ── Function definitions ───────────────────────────────────
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kw_len = (
                6 if isinstance(node, ast.AsyncFunctionDef) else 0
            )  # "async " (6 chars incl. space)
            name_off = _name_after_keyword(
                text,
                line_offsets,
                node.lineno,
                node.col_offset,
                3 + kw_len,  # "def" + "async "
            )
            if name_off is not None and not _in_exclusion(
                name_off, len(node.name), exclude
            ):
                tokens.append(
                    Token(
                        name_off,
                        len(node.name),
                        STYLES["function"],
                        "function",
                    )
                )

            for arg in _iter_param_args(node.args):
                if not hasattr(arg, "col_offset"):
                    continue
                a_start = _line_col_to_offset(
                    line_offsets, arg.lineno - 1, arg.col_offset
                )
                if a_start < 0 or _in_exclusion(a_start, len(arg.arg), exclude):
                    continue
                if arg.arg in ("self", "cls"):
                    tokens.append(
                        Token(
                            a_start,
                            len(arg.arg),
                            STYLES["self"],
                            "self",
                        )
                    )
                else:
                    tokens.append(
                        Token(
                            a_start,
                            len(arg.arg),
                            STYLES["parameter"],
                            "parameter",
                        )
                    )

            for deco in node.decorator_list:
                span = _decorator_name_span(deco, line_offsets)
                if span is None:
                    continue
                d_start, d_len = span
                if d_start >= 0 and not _in_exclusion(d_start, d_len, exclude):
                    tokens.append(
                        Token(d_start, d_len, STYLES["decorator"], "decorator")
                    )

        # ── Class definitions ──────────────────────────────────────
        elif isinstance(node, ast.ClassDef):
            name_off = _name_after_keyword(
                text, line_offsets, node.lineno, node.col_offset, 5
            )  # "class"
            if name_off is not None and not _in_exclusion(
                name_off, len(node.name), exclude
            ):
                tokens.append(
                    Token(
                        name_off,
                        len(node.name),
                        STYLES["class"],
                        "class",
                    )
                )

            for deco in node.decorator_list:
                span = _decorator_name_span(deco, line_offsets)
                if span is None:
                    continue
                d_start, d_len = span
                if d_start >= 0 and not _in_exclusion(d_start, d_len, exclude):
                    tokens.append(
                        Token(d_start, d_len, STYLES["decorator"], "decorator")
                    )

        # ── Lambda parameters ───────────────────────────────────────
        elif isinstance(node, ast.Lambda):
            for arg in _iter_param_args(node.args):
                if not hasattr(arg, "col_offset"):
                    continue
                a_start = _line_col_to_offset(
                    line_offsets, arg.lineno - 1, arg.col_offset
                )
                if a_start < 0 or _in_exclusion(a_start, len(arg.arg), exclude):
                    continue
                tokens.append(
                    Token(
                        a_start,
                        len(arg.arg),
                        STYLES["parameter"],
                        "parameter",
                    )
                )

        # ── import ─────────────────────────────────────────────────
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if not hasattr(alias, "col_offset"):
                    continue
                a_start = _line_col_to_offset(
                    line_offsets, alias.lineno - 1, alias.col_offset
                )
                if a_start < 0 or _in_exclusion(a_start, len(alias.name), exclude):
                    continue
                tokens.append(
                    Token(
                        a_start,
                        len(alias.name),
                        STYLES["module"],
                        "module",
                    )
                )

        # ── from ... import ────────────────────────────────────────
        elif isinstance(node, ast.ImportFrom):
            if node.module and hasattr(node, "col_offset"):
                mod_off = _module_after_from(
                    text, line_offsets, node.lineno, node.col_offset
                )
                if mod_off is not None and not _in_exclusion(
                    mod_off, len(node.module), exclude
                ):
                    tokens.append(
                        Token(
                            mod_off,
                            len(node.module),
                            STYLES["module"],
                            "module",
                        )
                    )
            for alias in node.names:
                if alias.name == "*" or not hasattr(alias, "col_offset"):
                    continue
                a_start = _line_col_to_offset(
                    line_offsets, alias.lineno - 1, alias.col_offset
                )
                if a_start < 0 or _in_exclusion(a_start, len(alias.name), exclude):
                    continue
                style = (
                    STYLES["class"] if alias.name[0].isupper() else STYLES["function"]
                )
                tokens.append(
                    Token(
                        a_start,
                        len(alias.name),
                        style,
                        "definition",
                    )
                )

        # ── Constants (None, True, False) ──────────────────────────
        elif (
            isinstance(node, ast.Constant)
            # `is` (identity), not `in`/`==`: bool is a subclass of int
            # in Python, so `1 == True` and `0 == False`. Using `in`
            # here previously caused plain integer literals 1 and 0 to
            # be misdetected as the True/False keywords and repainted
            # with the constant colour instead of the number colour.
            and (node.value is None or node.value is True or node.value is False)
            and hasattr(node, "col_offset")
        ):
            c_start = _line_col_to_offset(
                line_offsets, node.lineno - 1, node.col_offset
            )
            val_len = len(str(node.value))
            if c_start >= 0 and not _in_exclusion(c_start, val_len, exclude):
                tokens.append(
                    Token(
                        c_start,
                        val_len,
                        STYLES["constant"],
                        "constant",
                    )
                )

        # ── self / cls references ──────────────────────────────────
        elif isinstance(node, ast.Name) and node.id in ("self", "cls"):
            if not hasattr(node, "col_offset"):
                return
            n_start = _line_col_to_offset(
                line_offsets, node.lineno - 1, node.col_offset
            )
            if n_start >= 0 and not _in_exclusion(n_start, len(node.id), exclude):
                tokens.append(
                    Token(
                        n_start,
                        len(node.id),
                        STYLES["self"],
                        "self",
                    )
                )

        # ── Function / class calls ─────────────────────────────────
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and hasattr(func, "col_offset"):
                f_start = _line_col_to_offset(
                    line_offsets, func.lineno - 1, func.col_offset
                )
                if f_start >= 0 and not _in_exclusion(f_start, len(func.id), exclude):
                    # Distinguish builtins (hasattr, getattr, set,
                    # isinstance, len, ...) and capitalized callables
                    # (class instantiation, e.g. ConfirmDialog(...))
                    # from ordinary user-defined function calls -- all
                    # three previously collapsed onto the same
                    # "function" colour.
                    if func.id in _BUILTIN_NAMES:
                        call_style, call_kind = STYLES["builtin"], "builtin"
                    elif func.id[:1].isupper():
                        call_style, call_kind = STYLES["class"], "class"
                    else:
                        call_style, call_kind = STYLES["function"], "function"
                    tokens.append(Token(f_start, len(func.id), call_style, call_kind))
            elif isinstance(func, ast.Attribute) and hasattr(func, "end_col_offset"):
                f_end = _line_col_to_offset(
                    line_offsets,
                    func.end_lineno - 1,
                    func.end_col_offset,
                )
                f_start = f_end - len(func.attr)
                if f_start >= 0 and not _in_exclusion(f_start, len(func.attr), exclude):
                    # A dotted call whose attribute name is capitalized
                    # (e.g. `module.ConfirmDialog(...)`) is very likely
                    # a class instantiation, same convention as above.
                    if func.attr[:1].isupper():
                        call_style, call_kind = STYLES["class"], "class"
                    else:
                        call_style, call_kind = STYLES["function"], "function"
                    tokens.append(Token(f_start, len(func.attr), call_style, call_kind))

        # ── Attributes (obj.property) ─────────────────────────────
        elif isinstance(node, ast.Attribute) and hasattr(node, "end_col_offset"):
            a_end = _line_col_to_offset(
                line_offsets,
                node.end_lineno - 1,
                node.end_col_offset,
            )
            a_start = a_end - len(node.attr)
            if a_start < 0 or _in_exclusion(a_start, len(node.attr), exclude):
                return
            if node.attr.isupper():
                tokens.append(
                    Token(
                        a_start,
                        len(node.attr),
                        STYLES["constant"],
                        "constant",
                    )
                )
            elif node.attr[0].isupper():
                tokens.append(
                    Token(
                        a_start,
                        len(node.attr),
                        STYLES["class"],
                        "class",
                    )
                )
            else:
                tokens.append(
                    Token(
                        a_start,
                        len(node.attr),
                        STYLES["variable"],
                        "variable",
                    )
                )

    # ------------------------------------------------------------------
    # ITokenProvider interface
    # ------------------------------------------------------------------

    def get_token_at(self, text: str, offset: int) -> Optional[Token]:
        tokens = self.get_tokens(text)
        for tok in tokens:
            if tok.start <= offset < tok.start + tok.length:
                return tok
        return None

    # ------------------------------------------------------------------
    # Overlay path: semantic-only spans
    # ------------------------------------------------------------------

    def get_semantic_ranges(self, text: str) -> List[Tuple[int, int, str]]:
        """Return **semantic-only** ``(start, length, colour)`` tuples.

        This is the **overlay path**.  It returns *only* AST-derived
        spans that the base lexer cannot provide:

        - Function / class definition names
        - Function parameters
        - ``import`` module names and ``from … import`` aliases
        - ``self`` / ``cls`` references
        - ``None`` / ``True`` / ``False`` constants
        - Function / class call names
        - Attribute access names

        Keywords, strings, comments, numbers, operators, and the
        ``@`` decorator sign are **never** returned — those are owned
        by the lexer layer and would cause duplicate painting if
        emitted here.
        """
        if not text.strip():
            return []
        self._compute(text)
        return [
            (tok.start, tok.length, tok.style.colour) for tok in self._cache_semantic
        ]


# ------------------------------------------------------------------
# Legacy compatibility
# ------------------------------------------------------------------

_legacy_provider = PythonSemanticProvider()


def get_semantic_highlights(text: str) -> List[Tuple[int, int, str]]:
    """Legacy wrapper: return **semantic-only** ``[(start, length, colour), ...]``.

    Existing callers (``PythonLanguageProvider.get_semantic_highlights``
    and ``CodeEditor._apply_semantic_indicators``) use this function
    directly.  It returns only AST-derived spans — never keywords,
    strings, comments, numbers, operators, or decorators.
    """
    return _legacy_provider.get_semantic_ranges(text)
