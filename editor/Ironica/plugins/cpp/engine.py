"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Fresh libclang completion engine (no reuse of plugins/clang).
"""

from __future__ import annotations

import logging
import clang.cindex as C

# Local Imports and CLang Extension
from clang.cindex import Index, TranslationUnit
from .models import CppContext, CppCompletion
from . import args as cpp_args

logger = logging.getLogger("DreamStudio.Cpp.Engine")
_CACHE_SIZE = 8
_MAX_ITEMS = 200
_KIND = {
    "ENUM_DECL": "enum",
    "CLASS_DECL": "type",
    "STRUCT_DECL": "type",
    "FIELD_DECL": "field",
    "TYPEDEF_DECL": "type",
    "VAR_DECL": "variable",
    "DESTRUCTOR": "method",
    "CXX_METHOD": "method",
    "CONSTRUCTOR": "method",
    "PARM_DECL": "parameter",
    "NAMESPACE": "namespace",
    "TYPE_ALIAS_DECL": "type",
    "MACRO_DEFINITION": "macro",
    "FUNCTION_DECL": "function",
    "MACRO_INSTANTIATION": "macro",
    "ENUM_CONSTANT_DECL": "constant",
}
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
        """Return the shared libclang index for reuse across editors."""
        return self._index

    def _cache_key(self, ctx: CppContext) -> str:
        """Return an isolated TU cache key (unsaved tabs never collide)."""
        if ctx.file_path:
            return ctx.file_path
        if self._owner_id is not None:
            return f"untitled:{self._owner_id}"
    def complete(self, ctx: CppContext) -> list[CppCompletion]:
        """Return sorted/deduped/capped completions or empty list."""
        try:
            tu = self._tu(ctx)
            if tu is None:
                return []
            key = self._cache_key(ctx)
            clang_path = ctx.file_path or cpp_args.unsaved_name()
            res = tu.codeComplete(
                clang_path,
                ctx.line,
                ctx.col,
                unsaved_files=[(clang_path, ctx.source_code)],
                include_brief_comments=True,
            )
        except Exception as exc:
            logger.warning("codeComplete failed: %s", exc)
            return []
        if not res or not res.results:
            return []
        grouped: dict[str, CppCompletion] = {}
        overloads: dict[str, int] = {}
        for item in res.results:
            typed = ""
            sig: list[str] = []
            for ch in item.string:
                if ch.isKindTypedText():
                    typed = ch.spelling
                elif ch.isKindPlaceHolder() or ch.isKindInformative():
                    sig.append(ch.spelling)
            if not typed:
                continue
            kind = _KIND.get(str(item.cursorKind).split(".")[-1], "text")
            if typed in grouped:
                overloads[typed] = overloads.get(typed, 1) + 1
                continue
            grouped[typed] = CppCompletion(
                text=typed,
                insert_text=typed,
                kind=kind,
                signature=" ".join(sig).strip(),
            )
        out: list[CppCompletion] = []
        for text, completion in grouped.items():
            count = overloads.get(text, 1)
            if count > 1:
                signature = completion.signature
                suffix = f"(+{count - 1} overloads)"
                signature = f"{signature} {suffix}".strip() if signature else suffix
                out.append(
                    CppCompletion(
                        text=text,
                        insert_text=completion.insert_text,
                        kind=completion.kind,
                        signature=signature,
                    )
                )
            else:
                out.append(completion)
        out.sort(
            key=lambda c: (_KIND_RANK.get(c.kind, 9), c.text.lower()),
        )
        return out[:_MAX_ITEMS]

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
