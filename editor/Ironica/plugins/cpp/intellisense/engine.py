"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Fresh libclang completion engine (no reuse of plugins/clang).
"""

from __future__ import annotations

import logging
import re
import time
from typing import List, Tuple

from clang.cindex import CursorKind, Index, TranslationUnit
from ..models import CppContext, CppCompletion
from . import args as cpp_args
from . import headers as header_resolution

logger = logging.getLogger("DreamStudio.Cpp.Engine")
_CACHE_SIZE = 8
_MAX_ITEMS = 200
_MAX_OVERLOADS_PER_NAME = 8  # Allows up to eight function overloads
_KIND_BY_NAME = {
    "ENUM_DECL": "enum",
    "CLASS_DECL": "type",
    "STRUCT_DECL": "type",
    "FIELD_DECL": "field",
    "TYPEDEF_DECL": "type",
    "VAR_DECL": "variable",
    "DESTRUCTOR": "method",
    "CXX_METHOD": "method",
    "CONSTRUCTOR": "method",
    "CXX_CONSTRUCTOR": "method",
    "CXX_DESTRUCTOR": "method",
    "CXX_CONVERSION": "method",
    "PARM_DECL": "parameter",
    "NAMESPACE": "namespace",
    "TYPE_ALIAS_DECL": "type",
    "TYPE_ALIAS_TEMPLATE_DECL": "type",
    "MACRO_DEFINITION": "macro",
    "MACRO_INSTANTIATION": "macro",
    "FUNCTION_DECL": "function",
    "FUNCTION_TEMPLATE": "function",
    "CLASS_TEMPLATE": "type",
    "CLASS_TEMPLATE_PARTIAL_SPEC": "type",
    "ENUM_CONSTANT_DECL": "constant",
    "CONCEPT_DECL": "keyword",
    "FRIEND_DECL": "keyword",
    "INCLUSION_DIRECTIVE": "import",
}


def _build_kind_map() -> dict:
    """Map libclang cursor-kind codes to completion icons.

    Completion results carry plain integer codes rather than
    ``CursorKind`` members, so name strings never match — build the
    map from live enum values, guarded for version differences.
    """
    icon_by_code: dict = {}
    for name, icon in _KIND_BY_NAME.items():
        member = getattr(CursorKind, name, None)
        if member is None:
            continue
        try:
            icon_by_code[int(member.value)] = icon
        except (TypeError, ValueError):
            continue
    return icon_by_code


_KIND = _build_kind_map()

#: Parse options every translation unit is built with. Sharing one mask keeps
#: the completion and fold/highlight cache entries interchangeable.
_PARSE_OPTIONS = (
    TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    | TranslationUnit.PARSE_INCOMPLETE
    | TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION
)

_KIND_RANK = {
    "method": 0,
    "field": 1,
    "function": 2,
    "path": 2,
    "type": 3,
    "enum": 3,
    "keyword": 3,
    "constant": 4,
    "variable": 5,
    "parameter": 6,
    "namespace": 7,
    "macro": 8,
    "decorator": 8,
    "import": 8,
    "text": 9,
}


class CppEngine:
    """
    Owns one shared Index + bounded TU cache.
    All methods never raise.
    """

    def __init__(self, shared_index=None, owner_id=None) -> None:
        self._index = shared_index if shared_index is not None else Index.create()
        self._owner_id = owner_id
        self._cache: dict[str, tuple] = {}
        self._order: list[str] = []
        self._query_cost_ms = 0.0

    def query_cost_ms(self) -> float:
        """Return the EMA of parse+complete cost in milliseconds.

        Feeds the cost-scaled debounce; decays toward fast queries on its
        own, so fixing flags (or a PCH landing) re-snappens delays with
        no manual reset.

        Returns:
            Smoothed query cost (``0.0`` before any query).
        """
        try:
            return float(self._query_cost_ms)
        except (TypeError, ValueError):
            return 0.0

    @property
    def shared_index(self):
        """
        Return the shared libclang index for reuse across editors.
        """
        return self._index

    def _cache_key(self, ctx: CppContext) -> str:
        """
        Return an isolated TU cache key (unsaved tabs never collide).
        """
        if ctx.file_path:
            return ctx.file_path
        if self._owner_id is not None:
            return f"untitled:{self._owner_id}"
        return cpp_args.unsaved_name()

    _WORD = re.compile(r"[A-Za-z_]\w*")

    def _local_names(self, ctx) -> frozenset:
        """Return in-scope identifier spellings from the buffer (lexical).

        A full AST walk visits ~100k cursors through system headers
        (~2s); this regex pass costs ~1ms and is fresh on every keystroke.
        Words on lines before the cursor approximate scope for ranking.
        """
        try:
            lines = ctx.source_code.splitlines() if ctx.source_code else []
            head = "\n".join(lines[: max(0, ctx.line - 1)])
            head = re.sub(r"//[^\n]*", " ", head)
            head = re.sub(r"/\*.*?\*/", " ", head, flags=re.DOTALL)
            words = {m.group(0) for m in self._WORD.finditer(head)}
            words.discard("include")
            return frozenset(words)
        except Exception:
            return frozenset()

    def complete(self, ctx: CppContext) -> list[CppCompletion]:
        """
        Return ranked completions or empty list; one row per overload.
        """
        from ..autocompletion.context import classify

        lines = ctx.source_code.splitlines() if ctx.source_code else []
        row = lines[ctx.line - 1] if 0 <= ctx.line - 1 < len(lines) else ""
        kind, prefix_hint = classify(row, ctx.col - 1)
        if kind in ("none", "comment", "preprocessor"):
            return []
        if kind == "directive":
            from ..autocompletion.directives import complete_directive

            try:
                return complete_directive(prefix_hint)
            except Exception as exc:
                logger.warning("directive completion failed: %s", exc)
                return []
        if kind == "macro_guard":
            from ..autocompletion.macros import complete_guards

            try:
                return complete_guards(
                    prefix_hint,
                    self._tu_for_completion(ctx),
                    ctx.file_path or cpp_args.unsaved_name(),
                    ctx.source_code,
                )
            except Exception as exc:
                logger.warning("guard completion failed: %s", exc)
                return []
        if kind == "macro_body":
            from ..autocompletion.macros import complete_macro_body

            try:
                return complete_macro_body(
                    ctx.prefix,
                    row,
                    self._tu_for_completion(ctx),
                    ctx.file_path or cpp_args.unsaved_name(),
                )
            except Exception as exc:
                logger.warning("macro-body completion failed: %s", exc)
                return []
        if kind == "include":
            from ..autocompletion.includes import complete_include, parse_include

            try:
                parsed = parse_include(row, ctx.col - 1)
                if not parsed:
                    return []
                open_char, partial = parsed
                return complete_include(
                    partial,
                    open_char,
                    file_path=ctx.file_path,
                    compile_args=list(ctx.compile_args or []),
                )
            except Exception as exc:
                logger.warning("include completion failed: %s", exc)
                return []
        out: list[CppCompletion] = []
        tu = None
        clang_path = ctx.file_path or cpp_args.unsaved_name()
        want = ctx.prefix or ""
        include_macros = not want or want[:1].isupper()
        for _ in range(4):
            try:
                tu, res, clang_path = self._request_completion(
                    ctx, include_macros=include_macros
                )
            except Exception as exc:
                logger.warning("codeComplete failed: %s", exc)
                return []
            out = self._shape_results(ctx, res)
            if out:
                break
            missing = self.missing_includes(ctx)
            if not missing or not header_resolution.resolve_missing(
                missing, ctx.file_path, list(ctx.compile_args or [])
            ):
                break
        if not out:
            return []
        prefix = ""
        match = re.search(r"[A-Za-z_]\w*$", row[: ctx.col - 1])
        if match:
            prefix = match.group(0).lower()
        locals_boost = self._local_names(ctx)
        from ..autocompletion import callsite as _callsite

        try:
            site = _callsite.resolve(
                lines,
                ctx.line - 1,
                ctx.col - 1,
                tu,
                clang_path,
                hash(ctx.source_code),
                self._cache_key(ctx),
            )
        except Exception as exc:
            logger.debug("callsite resolution failed: %s", exc)
            site = _callsite.CallSite()
        scored: List[Tuple[int, object]] = []
        declared = {}
        if site.expected:
            declared = _callsite.buffer_declared_types(ctx.source_code)
        for completion in out:
            if not site.expected:
                scored.append((0, completion))
                continue
            if site.kind == "call_arg":
                params = _callsite.signature_params(completion.signature)
                if 0 <= site.arg_index < len(params):
                    cand_type = _callsite.param_type(params[site.arg_index])
                else:
                    cand_type = _callsite.candidate_type(completion.signature)
            else:
                cand_type = _callsite.candidate_type(completion.signature)
            if not cand_type:
                cand_type = declared.get(completion.text, "")
            scored.append((_callsite.type_tier(site.expected, cand_type), completion))
        typed_prefix = ctx.prefix or ""
        scored.sort(
            key=lambda pair: (
                pair[0],
                not (typed_prefix and pair[1].text.startswith(typed_prefix)),
                _KIND_RANK.get(pair[1].kind, 9),
                pair[1].text not in locals_boost,
                not pair[1].text.lower().startswith(prefix) if prefix else False,
                pair[1].text.lower(),
            ),
        )
        return [completion for _, completion in scored[:_MAX_ITEMS]]

    def _request_completion(self, ctx: CppContext, include_macros: bool = True):
        """Run ``codeComplete`` for *ctx* on its cached TU.

        Args:
            ctx: Completion context to complete.
            include_macros: Whether libclang should include macro rows.
                Disabled for lowercase prefixes (macros are overwhelmingly
                ``UPPER_SNAKE``), halving row counts on big TUs.

        Returns:
            Tuple of ``(tu, result_or_None, clang_path)``. The TU may be
            ``None`` when parsing failed; the result may be ``None``.
        """
        started = time.perf_counter()
        tu = self._tu_for_completion(ctx)
        if tu is None:
            return None, None, ctx.file_path or cpp_args.unsaved_name()
        clang_path = ctx.file_path or cpp_args.unsaved_name()
        # NOTE: no reparse here — codeComplete consumes the unsaved
        # buffer itself. An explicit reparse costs ~0.8s per keystroke
        # with zero benefit for completion freshness.
        res = tu.codeComplete(
            clang_path,
            ctx.line,
            ctx.col,
            unsaved_files=[(clang_path, ctx.source_code)],
            include_macros=include_macros,
            include_brief_comments=True,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        try:
            previous = float(self._query_cost_ms)
            self._query_cost_ms = previous * 0.7 + elapsed_ms * 0.3
        except (TypeError, ValueError):
            self._query_cost_ms = elapsed_ms
        return tu, res, clang_path

    def _shape_results(self, ctx: CppContext, res) -> list:
        """Shape raw code-complete results into prefix-filtered rows.

        Args:
            ctx: Completion context carrying the prefix filter.
            res: Raw ``codeComplete`` result (or ``None``).

        Returns:
            Ordered ``CppCompletion`` rows (possibly empty).
        """
        out: list[CppCompletion] = []
        if not res or not res.results:
            return out
        per_name: dict[str, int] = {}
        want_prefix = (ctx.prefix or "").lower()
        for item in res.results:
            chunks = list(item.string)
            typed = ""
            for chunk in chunks:
                if chunk.isKindTypedText():
                    typed = chunk.spelling
                    break
            if not typed:
                continue
            if want_prefix and not typed.lower().startswith(want_prefix):
                continue
            placeholders: list[str] = []
            informative: list[str] = []
            for chunk in chunks:
                if chunk.isKindTypedText():
                    continue
                elif chunk.isKindPlaceHolder():
                    placeholders.append(chunk.spelling)
                elif chunk.isKindInformative():
                    informative.append(chunk.spelling)
            seen_count = per_name.get(typed, 0)
            if seen_count >= _MAX_OVERLOADS_PER_NAME:
                continue
            per_name[typed] = seen_count + 1
            try:
                item_kind = _KIND.get(int(item.cursorKind), "text")
            except (TypeError, ValueError):
                item_kind = "text"
            if placeholders:
                call = f"{typed}({', '.join(placeholders)})"
                ret = " ".join(informative).strip()
                signature = f"{ret} {call}".strip() if ret else call
            else:
                signature = " ".join(informative).strip()
            out.append(
                CppCompletion(
                    text=typed,
                    insert_text=typed,
                    kind=item_kind,
                    signature=signature,
                )
            )
        return out

    def prime(self, ctx: CppContext) -> None:
        """Build the translation unit without completing (idle warmup).

        Warms parse caches off the typing path; completion queries that
        arrive later reuse the cached unit instead of paying a cold parse.
        """
        try:
            self._tu_for_completion(ctx)
        except Exception as exc:
            logger.debug("completion warmup failed: %s", exc)

    def missing_includes(self, ctx: CppContext) -> list:
        """Return header names the TU reports as not found, sorted.

        Parses ``'X' file not found`` diagnostics off the cached unit so
        the UI can tell the user *why* completion is empty instead of
        failing silently.

        Args:
            ctx: Completion context to inspect.

        Returns:
            Sorted unique header names (possibly empty) — never raises.
        """
        try:
            tu = self._tu_for_completion(ctx)
            if tu is None:
                return []
            missing: set = set()
            for diagnostic in getattr(tu, "diagnostics", []) or []:
                spelling = getattr(diagnostic, "spelling", "") or ""
                match = re.search(r"'([^']+)' file not found", spelling)
                if match:
                    missing.add(match.group(1))
            return sorted(missing)
        except Exception as exc:
            logger.debug("include diagnostics failed: %s", exc)
            return []

    def flags_for(self, ctx: CppContext) -> tuple:
        """Return the exact flags a TU for *ctx* would be built with.

        Pure computation (no parsing): defaults, database overlays,
        resolved header extras and the ``-include-pch`` flag when valid.

        Args:
            ctx: Completion context to compute flags for.

        Returns:
            Ordered flag tuple.
        """
        flags = ctx.compile_args or cpp_args.args_for_file(
            ctx.file_path, ctx.source_code
        )
        return tuple(list(flags) + header_resolution.extra_flags_for(ctx.file_path))

    def _store_tu(
        self, key: str, tu, source: str, flags: tuple, opts: int
    ) -> None:
        """Insert *tu* into the bounded cache, evicting the oldest entry.

        Both the completion and the fold/highlight paths land here so they
        share one key space; if they ever disagreed on the flag tuple the
        two would invalidate each other's unit on every request.

        Args:
            key: Cache key the unit belongs to.
            tu: Parsed translation unit to cache.
            source: Buffer text the unit was parsed from.
            flags: Flag tuple the unit was parsed with.
            opts: Parse options the unit was parsed with.
        """
        # NOTE: prune first — if _order ever drifts from _cache, evicting
        # _order[0] alone would pop a key with no entry and let _cache
        # grow past _CACHE_SIZE without bound.
        self._order = [k for k in self._order if k in self._cache and k != key]
        while len(self._cache) >= _CACHE_SIZE:
            evicted = self._order.pop(0) if self._order else None
            if evicted is None:
                self._cache.clear()
                break
            self._cache.pop(evicted, None)
        self._cache[key] = (tu, source, flags, opts)
        self._order.append(key)

    def _tu_for_completion(self, ctx: CppContext):
        """Return a TU for completion without reparsing (fast path).

        ``codeComplete`` consumes the unsaved buffer itself, so the
        cached TU only needs compatible compile flags — never a fresh
        reparse. Falls back to a full parse on first use or flag change.
        """
        key = self._cache_key(ctx)
        clang_path = ctx.file_path or cpp_args.unsaved_name()
        flags = tuple(self.flags_for(ctx))
        hit = self._cache.get(key)
        if hit and hit[2] == flags:
            return hit[0]
        try:
            tu = self._index.parse(
                clang_path,
                args=list(flags),
                unsaved_files=[(clang_path, ctx.source_code)],
                options=_PARSE_OPTIONS,
            )
        except Exception as exc:
            logger.warning("parse failed: %s", exc)
            return None
        self._store_tu(key, tu, ctx.source_code, flags, _PARSE_OPTIONS)
        return tu

    def _tu(self, ctx: CppContext):
        """Return a TU matching *ctx*'s current buffer, reparsing if needed.

        Unlike :meth:`_tu_for_completion` this reuses the cached unit only
        when the buffer text is unchanged; an edit triggers ``reparse``
        before falling back to a full parse. Flags come from
        :meth:`flags_for` — the same computation the completion path uses
        — so the two share cache entries instead of evicting each other.

        Args:
            ctx: Context carrying the source, position and file identity.

        Returns:
            Parsed translation unit, or ``None`` when parsing failed.
        """
        key = self._cache_key(ctx)
        clang_path = ctx.file_path or cpp_args.unsaved_name()
        flags = tuple(self.flags_for(ctx))
        hit = self._cache.get(key)
        if hit and hit[2] == flags:
            tu, src, _, _ = hit
            if src == ctx.source_code:
                return tu
            try:
                tu.reparse(unsaved_files=[(clang_path, ctx.source_code)])
                self._store_tu(
                    key, tu, ctx.source_code, flags, _PARSE_OPTIONS
                )
                return tu
            except Exception:
                pass
        try:
            tu = self._index.parse(
                clang_path,
                args=list(flags),
                unsaved_files=[(clang_path, ctx.source_code)],
                options=_PARSE_OPTIONS,
            )
        except Exception as exc:
            logger.warning("parse failed: %s", exc)
            return None
        self._store_tu(key, tu, ctx.source_code, flags, _PARSE_OPTIONS)
        return tu
