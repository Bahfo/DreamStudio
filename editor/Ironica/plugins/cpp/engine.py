"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Fresh libclang completion engine (no reuse of plugins/clang).
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

import clang.cindex as C

# Local Imports and CLang Extension
from clang.cindex import CursorKind, Index, TranslationUnit
from .models import CppContext, CppCompletion
from . import args as cpp_args

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

_KIND_RANK = {
    "method": 0,
    "field": 1,
    "function": 2,
    "type": 3,
    "enum": 3,
    "constant": 4,
    "variable": 5,
    "parameter": 6,
    "namespace": 7,
    "macro": 8,
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
        from .context import classify

        lines = ctx.source_code.splitlines() if ctx.source_code else []
        row = lines[ctx.line - 1] if 0 <= ctx.line - 1 < len(lines) else ""
        kind, prefix_hint = classify(row, ctx.col - 1)
        if kind in ("none", "comment", "preprocessor"):
            return []
        if kind == "directive":
            from .directives import complete_directive

            try:
                return complete_directive(prefix_hint)
            except Exception as exc:
                logger.warning("directive completion failed: %s", exc)
                return []
        if kind == "macro_guard":
            from .macros import complete_guards

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
            from .macros import complete_macro_body

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
            from .includes import complete_include, parse_include

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
        try:
            tu = self._tu_for_completion(ctx)
            if tu is None:
                return []
            clang_path = ctx.file_path or cpp_args.unsaved_name()
            # NOTE: no reparse here — codeComplete consumes the unsaved
            # buffer itself. An explicit reparse costs ~0.8s per keystroke
            # with zero benefit for completion freshness.
            res = tu.codeComplete(
                clang_path,
                ctx.line,
                ctx.col,
                unsaved_files=[(clang_path, ctx.source_code)],
                include_macros=True,
                include_brief_comments=True,
            )
        except Exception as exc:
            logger.warning("codeComplete failed: %s", exc)
            return []
        if not res or not res.results:
            return []
        per_name: dict[str, int] = {}
        out: list[CppCompletion] = []
        for item in res.results:
            name = ""
            placeholders: list[str] = []
            informative: list[str] = []
            for ch in item.string:
                if ch.isKindTypedText():
                    name = ch.spelling
                elif ch.isKindPlaceHolder():
                    placeholders.append(ch.spelling)
                elif ch.isKindInformative():
                    informative.append(ch.spelling)
            if not name:
                continue
            if ctx.prefix and not name.lower().startswith(ctx.prefix.lower()):
                continue
            seen_count = per_name.get(name, 0)
            if seen_count >= _MAX_OVERLOADS_PER_NAME:
                continue
            per_name[name] = seen_count + 1
            try:
                item_kind = _KIND.get(int(item.cursorKind), "text")
            except (TypeError, ValueError):
                item_kind = "text"
            if placeholders:
                call = f"{name}({', '.join(placeholders)})"
                ret = " ".join(informative).strip()
                signature = f"{ret} {call}".strip() if ret else call
            else:
                signature = " ".join(informative).strip()
            out.append(
                CppCompletion(
                    text=name,
                    insert_text=name,
                    kind=item_kind,
                    signature=signature,
                )
            )
        prefix = ""
        match = re.search(r"[A-Za-z_]\w*$", row[: ctx.col - 1])
        if match:
            prefix = match.group(0).lower()
        locals_boost = self._local_names(ctx)
        from . import callsite as _callsite

        try:
            site = _callsite.resolve(
                lines, ctx.line - 1, ctx.col - 1, tu, clang_path,
                hash(ctx.source_code), self._cache_key(ctx),
            )
        except Exception as exc:
            logger.debug("callsite resolution failed: %s", exc)
            site = _callsite.CallSite()
        scored: List[Tuple[int, object]] = []
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
                    cand_type = _callsite.candidate_type(
                        completion.signature)
            else:
                cand_type = _callsite.candidate_type(completion.signature)
            if not cand_type:
                cand_type = declared.get(completion.text, "")
            scored.append(
                (_callsite.type_tier(site.expected, cand_type), completion))
        scored.sort(
            key=lambda pair: (
                pair[0],
                _KIND_RANK.get(pair[1].kind, 9),
                pair[1].text not in locals_boost,
                not pair[1].text.lower().startswith(prefix)
                if prefix else False,
                pair[1].text.lower(),
            ),
        )
        return [completion for _, completion in scored[:_MAX_ITEMS]]

    def prime(self, ctx: CppContext) -> None:
        """Build the translation unit without completing (idle warmup).

        Warms parse caches off the typing path; completion queries that
        arrive later reuse the cached unit instead of paying a cold parse.
        """
        try:
            self._tu_for_completion(ctx)
        except Exception as exc:
            logger.debug("completion warmup failed: %s", exc)

    def _tu_for_completion(self, ctx: CppContext):
        """Return a TU for completion without reparsing (fast path).

        ``codeComplete`` consumes the unsaved buffer itself, so the
        cached TU only needs compatible compile flags — never a fresh
        reparse. Falls back to a full parse on first use or flag change.
        """
        key = self._cache_key(ctx)
        clang_path = ctx.file_path or cpp_args.unsaved_name()
        flags = ctx.compile_args or cpp_args.args_for_file(
            ctx.file_path, ctx.source_code
        )
        hit = self._cache.get(key)
        if hit and hit[2] == tuple(flags):
            return hit[0]
        try:
            tu = self._index.parse(
                clang_path,
                args=flags,
                unsaved_files=[(clang_path, ctx.source_code)],
                options=(
                    TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
                    | TranslationUnit.PARSE_INCOMPLETE
                    | TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION
                ),
            )
        except Exception as exc:
            logger.warning("parse failed: %s", exc)
            return None
        if key in self._cache:
            try:
                self._order.remove(key)
            except ValueError:
                pass
        elif len(self._cache) >= _CACHE_SIZE:
            self._cache.pop(self._order.pop(0), None)
        self._cache[key] = (
            tu,
            ctx.source_code,
            tuple(flags),
            TranslationUnit.PARSE_INCOMPLETE,
        )
        self._order.append(key)
        return tu

    def _tu(self, ctx: CppContext):
        key = self._cache_key(ctx)
        clang_path = ctx.file_path or cpp_args.unsaved_name()
        flags = ctx.compile_args or cpp_args.args_for_file(
            ctx.file_path, ctx.source_code
        )
        opts = (
            TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
            | TranslationUnit.PARSE_INCOMPLETE
            | TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION
        )
        hit = self._cache.get(key)
        if hit and hit[2] == tuple(flags):
            tu, src, _, _ = hit
            if src == ctx.source_code:
                return tu
            try:
                tu.reparse(unsaved_files=[(clang_path, ctx.source_code)])
                self._cache[key] = (tu, ctx.source_code, tuple(flags), opts)
                return tu
            except Exception:
                pass
        try:
            tu = self._index.parse(
                clang_path,
                args=flags,
                unsaved_files=[(clang_path, ctx.source_code)],
                options=opts,
            )
        except Exception as exc:
            logger.warning("parse failed: %s", exc)
            return None
        if key in self._cache:
            try:
                self._order.remove(key)
            except ValueError:
                pass
        elif len(self._cache) >= _CACHE_SIZE:
            self._cache.pop(self._order.pop(0), None)
        self._cache[key] = (tu, ctx.source_code, tuple(flags), opts)
        self._order.append(key)
        return tu
