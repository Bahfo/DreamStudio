from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shlex
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Sequence

from clang import cindex
from clang.cindex import Cursor, CursorKind, Index, TranslationUnit

from ..intellisense import args as cpp_args
from ..intellisense.engine import CppEngine
from ..intellisense.symbol_index import SymbolIndex
from ..models import CppContext

logger = logging.getLogger("DreamStudio.CPP.Navigation")


@dataclass(frozen=True)
class NavigationResult:
    file_path: str
    line: int
    col: int
    display_name: str
    kind: str


@dataclass(frozen=True)
class SymbolContext:
    cursor: Cursor
    tu: TranslationUnit
    file_path: str
    is_definition: bool
    is_declaration: bool
    is_reference: bool
    canonical_cursor: Cursor


_REFERENCE_KIND_NAMES = (
    "DECL_REF_EXPR",
    "MEMBER_REF_EXPR",
    "MEMBER_REF",
    "CALL_EXPR",
    "OVERLOADED_DECL_REF",
    "TYPE_REF",
    "TEMPLATE_REF",
    "NAMESPACE_REF",
    "VARIABLE_REF",
    "MACRO_INSTANTIATION",
)
_REFERENCE_KINDS = {
    getattr(CursorKind, name)
    for name in _REFERENCE_KIND_NAMES
    if hasattr(CursorKind, name)
}
_DECLARATION_KIND_NAMES = (
    "FUNCTION_DECL",
    "CXX_METHOD",
    "CONSTRUCTOR",
    "DESTRUCTOR",
    "FUNCTION_TEMPLATE",
    "FIELD_DECL",
    "VAR_DECL",
    "PARM_DECL",
    "CLASS_DECL",
    "STRUCT_DECL",
    "CLASS_TEMPLATE",
    "ENUM_DECL",
    "ENUM_CONSTANT_DECL",
    "TYPEDEF_DECL",
    "TYPE_ALIAS_DECL",
    "NAMESPACE",
    "MACRO_DEFINITION",
)
_DECLARATION_KINDS = {
    getattr(CursorKind, name)
    for name in _DECLARATION_KIND_NAMES
    if hasattr(CursorKind, name)
}


class NavigationEngine:
    """Adapt the IDE's editor context to libclang navigation results."""

    def __init__(self, cpp_engine: CppEngine) -> None:
        self._engine = cpp_engine
        self._database_cache: dict[str, dict[str, tuple[str, list[str]]]] = {}
        self._database_path_cache: dict[str, str] = {}
        self._unit_cache: dict[
            tuple[str, tuple[str, ...], int, tuple[str, int, str]],
            tuple[Index, TranslationUnit],
        ] = {}
        self._symbol_index = None  # type: SymbolIndex | None
        self._unsaved_buffers: tuple[tuple[str, str], ...] = ()

    def set_symbol_index(self, symbol_index: SymbolIndex) -> None:
        """
        Attach a SymbolIndex for fast navigation queries.

        Args:
            symbol_index: Index facade owned by the current solution.
        """
        self._symbol_index = symbol_index

    def set_unsaved_buffers(self, buffers: Sequence[tuple[str, str]]) -> None:
        """
        Attach the GUI-thread snapshot of modified editor buffers.

        Args:
            buffers: ``(absolute_path, buffer_text)`` pairs captured before
                the navigation request was handed to the worker thread.
        """
        self._unsaved_buffers = tuple(
            (str(path), str(source)) for path, source in buffers if path
        )

    def _unsaved_snapshot(
        self, active_path: str, active_source: str
    ) -> list[tuple[str, str]]:
        """
        Return unsaved buffers with the active editor taking precedence.

        Args:
            active_path: Normalised path of the file being navigated.
            active_source: Current text of the active editor buffer.

        Returns:
            One entry per file, ordered by normalised path, with no duplicates.
        """
        merged: dict[str, tuple[str, str]] = {}
        for path, source in self._unsaved_buffers:
            if not path:
                continue
            merged[self._buffer_identity(path)] = (path, source)
        if active_path:
            merged[self._buffer_identity(active_path)] = (
                active_path,
                active_source or "",
            )
        return [merged[key] for key in sorted(merged)]

    @staticmethod
    def _buffer_identity(path: str) -> str:
        """Return a canonical identity used to de-duplicate buffers."""
        try:
            return os.path.normcase(os.path.normpath(os.path.realpath(path)))
        except (OSError, TypeError, ValueError):
            return str(path)

    @staticmethod
    def _unsaved_digest(unsaved: Sequence[tuple[str, str]]) -> str:
        """Return a stable digest identifying *unsaved* inputs."""
        digest = hashlib.blake2b(digest_size=16)
        for path, source in unsaved:
            digest.update(path.encode("utf-8", "surrogatepass"))
            digest.update(b"\0")
            digest.update(source.encode("utf-8", "surrogatepass"))
            digest.update(b"\0")
        return digest.hexdigest()

    def _active_translation_unit(
        self, ctx: CppContext
    ) -> tuple[Optional[TranslationUnit], str]:
        path_value = getattr(ctx, "file_path", None)
        path = self._normalise_path(path_value)
        source = getattr(ctx, "source_code", "") or ""
        attempted_unsaved = False

        if path and self._has_extra_unsaved(path):
            attempted_unsaved = True
            tu = self._parse_active_with_unsaved(ctx, path, source)
        else:
            try:
                tu = self._engine._tu(ctx)
            except Exception:
                logger.debug(
                    "Could not obtain the active translation unit", exc_info=True
                )
                tu = None

        if not path_value and tu is not None:
            path_value = getattr(tu, "spelling", "")
        if not path:
            path = self._normalise_path(path_value)
        if not path:
            try:
                path = self._normalise_path(self._engine._cache_key(ctx))
            except Exception:
                path = ""

        if tu is None and path and not attempted_unsaved:
            command = self._compile_commands(path).get(path)
            if command is not None:
                _, working_directory, arguments = command
                tu = self._parse_translation_unit(
                    path, working_directory, arguments, ctx, path
                )
            else:
                arguments = cpp_args.args_for_file(path, "")
                tu = self._parse_translation_unit(
                    path, os.path.dirname(path), arguments, ctx, path
                )

        if tu is not None and path:
            missing = self._missing_includes(tu)
            if missing:
                arguments = list(getattr(ctx, "compile_args", []) or [])
                if not arguments:
                    arguments = cpp_args.args_for_file(
                        path, getattr(ctx, "source_code", "") or ""
                    )
                if self._resolve_missing(path, missing, arguments):
                    reparsed = self._parse_translation_unit(
                        path, os.path.dirname(path), arguments, ctx, path
                    )
                    if reparsed is not None:
                        tu = reparsed

        return (tu, path) if tu is not None and path else (None, path)

    def _has_extra_unsaved(self, active_path: str) -> bool:
        """Return ``True`` when another open buffer differs from *active_path*."""
        identity = self._buffer_identity(active_path)
        return any(
            self._buffer_identity(path) != identity
            for path, _ in self._unsaved_buffers
            if path
        )

    def _parse_active_with_unsaved(
        self, ctx: CppContext, active_path: str, active_source: str
    ) -> Optional[TranslationUnit]:
        """Parse the active file with every snapshot buffer visible to libclang."""
        command = self._compile_commands(active_path).get(active_path)
        if command is not None:
            _, working_directory, arguments = command
        else:
            working_directory = os.path.dirname(active_path)
            arguments = list(getattr(ctx, "compile_args", []) or [])
            if not arguments:
                arguments = cpp_args.args_for_file(active_path, active_source)
        return self._parse_translation_unit(
            active_path, working_directory, arguments, ctx, active_path
        )

    @staticmethod
    def _normalise_path(path: str | os.PathLike[str] | None) -> str:
        if not path:
            return ""
        try:
            return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))
        except (OSError, TypeError, ValueError):
            return ""

    @staticmethod
    def _valid(cursor: Optional[Cursor]) -> bool:
        if cursor is None:
            return False
        try:
            return cursor.kind not in {
                getattr(CursorKind, "NO_DECL_FOUND", None),
                getattr(CursorKind, "INVALID_FILE", None),
                getattr(CursorKind, "INVALID_CODE", None),
                getattr(CursorKind, "INVALID", None),
            }
        except Exception:
            return False

    @staticmethod
    def _line_col_to_byte_offset(source: str, line: int, col: int) -> int:
        """Convert the context's one-based line/column to a UTF-8 byte offset."""
        if int(line) < 1:
            return -1
        lines = source.splitlines(keepends=True)
        if not lines:
            return 0
        if source.endswith(("\n", "\r")):
            lines.append("")

        line_index = int(line) - 1
        if line_index >= len(lines):
            return -1
        line_text = lines[line_index].rstrip("\r\n")
        character_column = min(max(int(col) - 1, 0), len(line_text))
        prefix = "".join(lines[:line_index]) + line_text[:character_column]
        return len(prefix.encode("utf-8"))

    @staticmethod
    def _token_for_offset(tu: TranslationUnit, cursor: Cursor, offset: int):
        try:
            for token in tu.get_tokens(extent=cursor.extent):
                start = int(token.extent.start.offset)
                end = int(token.extent.end.offset)
                if start <= offset < end:
                    return token
        except Exception:
            return None
        return None

    def _include_cursor_at_offset(
        self, tu: TranslationUnit, path: str, offset: int
    ) -> Optional[Cursor]:
        include_kind = getattr(CursorKind, "INCLUSION_DIRECTIVE", None)
        try:
            for cursor in tu.cursor.get_children():
                if cursor.kind != include_kind or cursor.location.file is None:
                    continue
                if self._normalise_path(cursor.location.file.name) != path:
                    continue
                for token in tu.get_tokens(extent=cursor.extent):
                    start = int(token.extent.start.offset)
                    end = int(token.extent.end.offset)
                    if start <= offset < end:
                        return cursor
        except Exception:
            logger.debug("Could not resolve an include token", exc_info=True)
        return None

    def _cursor_at(
        self, ctx: CppContext
    ) -> Optional[tuple[Cursor, TranslationUnit, str]]:
        tu, path = self._active_translation_unit(ctx)
        if tu is None:
            return None

        source = getattr(ctx, "source_code", "") or ""
        offset = self._line_col_to_byte_offset(source, ctx.line, ctx.col)

        for probe in (offset, offset - 1):
            if probe < 0:
                continue
            try:
                location = tu.get_location(path, probe)
                cursor = Cursor.from_location(tu, location)
            except Exception:
                cursor = None

            if not self._valid(cursor):
                include_cursor = self._include_cursor_at_offset(tu, path, probe)
                if include_cursor is not None:
                    return include_cursor, tu, path
                continue

            token = self._token_for_offset(tu, cursor, probe)
            if token is None:
                if cursor.kind == getattr(CursorKind, "TRANSLATION_UNIT", None):
                    include_cursor = self._include_cursor_at_offset(tu, path, probe)
                    if include_cursor is not None:
                        return include_cursor, tu, path
                continue

            is_include = cursor.kind == getattr(CursorKind, "INCLUSION_DIRECTIVE", None)
            if is_include:
                return cursor, tu, path
            is_translation_unit = cursor.kind == getattr(
                CursorKind, "TRANSLATION_UNIT", None
            )
            is_include_name = is_include and token.kind in {
                getattr(cindex.TokenKind, "LITERAL", None),
                getattr(cindex.TokenKind, "IDENTIFIER", None),
            }
            is_identifier = token.kind == getattr(cindex.TokenKind, "IDENTIFIER", None)
            if (
                is_include_name
                or token.kind == getattr(cindex.TokenKind, "LITERAL", None)
                or (is_translation_unit and is_identifier)
            ):
                include_cursor = self._include_cursor_at_offset(tu, path, probe)
                if include_cursor is not None:
                    return include_cursor, tu, path
            if not is_include_name and not is_identifier:
                referenced = self._safe_cursor(cursor, "referenced")
                operator_name = (
                    getattr(cursor, "spelling", "")
                    or getattr(referenced, "spelling", "")
                    or ""
                )
                if not operator_name.startswith("operator"):
                    continue

            if is_include:
                return cursor, tu, path

            try:
                token_cursor = Cursor.from_location(tu, token.location)
            except Exception:
                token_cursor = cursor
            if self._valid(token_cursor):
                return token_cursor, tu, path
            return cursor, tu, path

        return None

    def resolve_at(self, ctx: CppContext) -> Optional[SymbolContext]:
        found = self._cursor_at(ctx)
        if found is None:
            return None

        cursor, tu, path = found
        if cursor.kind == getattr(CursorKind, "INCLUSION_DIRECTIVE", None):
            return SymbolContext(cursor, tu, path, False, False, True, cursor)

        referenced = self._safe_cursor(cursor, "referenced")
        target = referenced if self._valid(referenced) else cursor
        canonical = self._safe_cursor(target, "canonical")
        if not self._valid(canonical):
            canonical = target

        try:
            is_definition = bool(target.is_definition())
        except Exception:
            is_definition = False

        try:
            is_reference = cursor.kind in _REFERENCE_KINDS or cursor != target
        except Exception:
            is_reference = cursor.kind in _REFERENCE_KINDS

        return SymbolContext(
            cursor=cursor,
            tu=tu,
            file_path=path,
            is_definition=is_definition,
            is_declaration=target.kind in _DECLARATION_KINDS,
            is_reference=is_reference,
            canonical_cursor=canonical,
        )

    @staticmethod
    def _safe_cursor(cursor: Cursor, attribute: str) -> Optional[Cursor]:
        try:
            return getattr(cursor, attribute)
        except Exception:
            return None

    @staticmethod
    def _get_definition_cursor(cursor: Cursor) -> Optional[Cursor]:
        try:
            return cursor.get_definition()
        except Exception:
            return None

    @staticmethod
    def _usr(cursor: Optional[Cursor]) -> str:
        if cursor is None:
            return ""
        try:
            return cursor.get_usr() or ""
        except Exception:
            return ""

    def _result(self, cursor: Cursor, kind: str) -> Optional[NavigationResult]:
        if not self._valid(cursor):
            return None
        try:
            location = cursor.location
            if location.file is None or location.line < 1 or location.column < 1:
                return None
            path = self._normalise_path(location.file.name)
            if not path:
                return None
            return NavigationResult(
                file_path=path,
                line=int(location.line) - 1,
                col=int(location.column) - 1,
                display_name=cursor.spelling
                or cursor.displayname
                or token_spelling(cursor),
                kind=kind,
            )
        except Exception:
            logger.debug(
                "Could not convert a libclang location to a navigation result",
                exc_info=True,
            )
            return None

    def _include_result(self, cursor: Cursor) -> list[NavigationResult]:
        try:
            included_file = cursor.get_included_file()
        except Exception:
            included_file = None
        if included_file is None:
            return []
        path = self._normalise_path(included_file.name)
        if not path:
            return []
        return [NavigationResult(path, 0, 0, Path(path).name, "include")]

    def _query_symbol_index(self, usr: str, action: str) -> list[NavigationResult]:
        """Query the SymbolIndex for navigation results if available and ready."""
        if self._symbol_index is None or not self._symbol_index.is_ready():
            return []
        try:
            if action == "definition":
                symbols = self._symbol_index.definitions(usr)
            elif action == "declaration":
                symbols = self._symbol_index.declarations(usr)
            elif action == "implementation":
                symbols = list(self._symbol_index.definitions(usr))
                seen = {(item.file, item.line, item.col) for item in symbols}
                for override in self._symbol_index.overrides(usr):
                    key = (override.file, override.line, override.col)
                    if key not in seen:
                        seen.add(key)
                        symbols.append(override)
            elif action == "reference":
                refs = self._symbol_index.reference_locations(usr)
                return [
                    NavigationResult(path, line, col, "reference", "reference")
                    for path, line, col in refs
                ]
            else:
                return []

            return [
                NavigationResult(s.file, s.line, s.col, s.name, action) for s in symbols
            ]
        except Exception as exc:
            logger.debug("SymbolIndex query failed for %s: %s", action, exc)
            return []

    def get_definition(self, ctx: CppContext) -> list[NavigationResult]:
        symbol = self.resolve_at(ctx)
        if symbol is None:
            return []
        if symbol.cursor.kind == getattr(CursorKind, "INCLUSION_DIRECTIVE", None):
            return self._include_result(symbol.cursor)

        target_usr = self._usr(symbol.canonical_cursor) or self._usr(symbol.cursor)
        if target_usr:
            idx_results = self._query_symbol_index(target_usr, "definition")
            if idx_results:
                return idx_results

        direct = self._get_definition_cursor(symbol.canonical_cursor)
        if self._valid(direct):
            result = self._result(direct, "definition")
            if result:
                return [result]

        return self._find_in_units(
            ctx, symbol, "definition", deadline=time.monotonic() + 4.0
        )

    def get_declaration(self, ctx: CppContext) -> list[NavigationResult]:
        symbol = self.resolve_at(ctx)
        if symbol is None:
            return []
        if symbol.cursor.kind == getattr(CursorKind, "INCLUSION_DIRECTIVE", None):
            return self._include_result(symbol.cursor)

        target_usr = self._usr(symbol.canonical_cursor) or self._usr(symbol.cursor)
        if target_usr:
            idx_results = self._query_symbol_index(target_usr, "declaration")
            if idx_results:
                return idx_results

        direct = symbol.canonical_cursor
        if self._valid(direct) and not self._is_definition(direct):
            result = self._result(direct, "declaration")
            if result:
                return [result]

        return self._find_in_units(
            ctx, symbol, "declaration", deadline=time.monotonic() + 4.0
        )

    def get_implementation(self, ctx: CppContext) -> list[NavigationResult]:
        symbol = self.resolve_at(ctx)
        if symbol is None or symbol.cursor.kind == getattr(
            CursorKind, "INCLUSION_DIRECTIVE", None
        ):
            return []

        target_usr = self._usr(symbol.canonical_cursor) or self._usr(symbol.cursor)
        if target_usr:
            idx_results = self._query_symbol_index(target_usr, "implementation")
            if idx_results:
                return idx_results

        return self._find_in_units(
            ctx, symbol, "implementation", deadline=time.monotonic() + 4.0
        )

    def get_references(self, ctx: CppContext) -> list[NavigationResult]:
        symbol = self.resolve_at(ctx)
        if symbol is None or symbol.cursor.kind == getattr(
            CursorKind, "INCLUSION_DIRECTIVE", None
        ):
            return []

        target_usr = self._usr(symbol.canonical_cursor) or self._usr(symbol.cursor)
        if target_usr:
            idx_results = self._query_symbol_index(target_usr, "reference")
            if idx_results:
                return idx_results

        return self._find_in_units(
            ctx, symbol, "reference", deadline=time.monotonic() + 4.0
        )

    @staticmethod
    def _is_definition(cursor: Cursor) -> bool:
        try:
            return bool(cursor.is_definition())
        except Exception:
            return False

    @staticmethod
    def _cursors(tu: TranslationUnit) -> Iterator[Cursor]:
        try:
            yield from tu.cursor.walk_preorder()
        except Exception:
            return

    def _find_in_units(
        self,
        ctx: CppContext,
        symbol: SymbolContext,
        mode: str,
        deadline: float | None = None,
    ) -> list[NavigationResult]:
        target = symbol.canonical_cursor
        target_usr = self._usr(target) or self._usr(symbol.cursor)
        if not target_usr:
            return []

        active_path = symbol.file_path
        results: list[NavigationResult] = []
        seen: set[tuple[str, int, int]] = set()
        active_tu = symbol.tu

        def append(cursor: Cursor, kind: str) -> None:
            result = self._result(cursor, kind)
            if not result:
                return
            key = (result.file_path, result.line, result.col)
            if key not in seen:
                seen.add(key)
                results.append(result)

        def check_deadline() -> bool:
            return deadline is not None and time.monotonic() >= deadline

        for cursor in self._cursors(active_tu):
            if check_deadline():
                break
            if mode == "reference":
                referenced = self._safe_cursor(cursor, "referenced")
                matches = self._usr(referenced) == target_usr
                if matches:
                    append(cursor, "reference")
                continue

            if self._usr(cursor) != target_usr:
                continue
            definition = self._is_definition(cursor)
            if mode == "definition" and definition:
                append(cursor, "definition")
            elif mode == "declaration" and not definition:
                append(cursor, "declaration")
            elif mode == "implementation" and definition:
                append(cursor, "implementation")

        if mode != "reference" and results:
            other_file_results = [
                item for item in results if item.file_path != active_path
            ]
            if other_file_results:
                return other_file_results
            if mode == "definition" and any(
                self._is_definition(cursor) for cursor in (target,)
            ):
                return results

        for candidate_path, working_directory, arguments in self._compile_commands(
            active_path
        ).values():
            if check_deadline():
                break
            if self._normalise_path(candidate_path) == active_path:
                continue
            tu = self._parse_translation_unit(
                candidate_path, working_directory, arguments, ctx, active_path
            )
            if tu is None:
                continue

            for cursor in self._cursors(tu):
                if check_deadline():
                    break
                if mode == "reference":
                    referenced = self._safe_cursor(cursor, "referenced")
                    if self._usr(referenced) == target_usr:
                        append(cursor, "reference")
                    continue

                candidate_usr = self._usr(cursor)
                definition = self._is_definition(cursor)
                if candidate_usr == target_usr:
                    if mode == "definition" and definition:
                        append(cursor, "definition")
                    elif mode == "declaration" and not definition:
                        append(cursor, "declaration")
                    elif mode == "implementation" and definition:
                        append(cursor, "implementation")

                if mode == "implementation" and definition:
                    overridden = self._safe_overridden(cursor)
                    if target_usr in {
                        self._usr(item) for item in overridden
                    } or self._overrides_target(cursor, target):
                        append(cursor, "implementation")

            if mode in {"definition", "declaration"} and any(
                item.file_path != active_path for item in results
            ):
                return [item for item in results if item.file_path != active_path]

        # Fallback: search in project source files when compile_commands.json is not available
        project_files = self._find_project_files(active_path)
        for candidate_path in project_files:
            if check_deadline():
                break
            if self._normalise_path(candidate_path) == active_path:
                continue
            tu = self._parse_project_file(candidate_path, ctx, active_path)
            if tu is None:
                continue

            for cursor in self._cursors(tu):
                if check_deadline():
                    break
                if mode == "reference":
                    referenced = self._safe_cursor(cursor, "referenced")
                    if self._usr(referenced) == target_usr:
                        append(cursor, "reference")
                    continue

                candidate_usr = self._usr(cursor)
                definition = self._is_definition(cursor)
                if candidate_usr == target_usr:
                    if mode == "definition" and definition:
                        append(cursor, "definition")
                    elif mode == "declaration" and not definition:
                        append(cursor, "declaration")
                    elif mode == "implementation" and definition:
                        append(cursor, "implementation")

                if mode == "implementation" and definition:
                    overridden = self._safe_overridden(cursor)
                    if target_usr in {
                        self._usr(item) for item in overridden
                    } or self._overrides_target(cursor, target):
                        append(cursor, "implementation")

            if mode in {"definition", "declaration"} and any(
                item.file_path != active_path for item in results
            ):
                return [item for item in results if item.file_path != active_path]

        return results

    @staticmethod
    def _safe_overridden(cursor: Cursor) -> tuple[Cursor, ...]:
        try:
            return tuple(cursor.get_overridden_cursors())
        except Exception:
            return ()

    @staticmethod
    def _safe_base_classes(cursor: Cursor) -> list:
        try:
            bases = []
            for child in cursor.get_children():
                if child.kind != getattr(CursorKind, "CXX_BASE_SPECIFIER", None):
                    continue
                base = NavigationEngine._safe_cursor(child, "referenced")
                if base is None or not NavigationEngine._valid(base):
                    base = child.type.get_declaration()
                if base is not None and NavigationEngine._valid(base):
                    bases.append(base)
            return bases
        except Exception:
            return []

    def _class_derives_from(self, cursor: Cursor, target_usr: str) -> bool:
        """Return whether *cursor*'s class inherits from *target_usr*."""
        if not target_usr:
            return False
        pending = [cursor]
        seen: set = set()
        while pending and len(seen) < 64:
            current = pending.pop()
            current_usr = self._usr(current)
            if not current_usr or current_usr in seen:
                continue
            seen.add(current_usr)
            for base in self._safe_base_classes(current):
                if self._usr(base) == target_usr:
                    return True
                pending.append(base)
        return False

    def _overrides_target(self, candidate: Cursor, target: Cursor) -> bool:
        """Fallback override check when libclang reports no overridden cursors."""
        try:
            method_kinds = {
                getattr(CursorKind, "CXX_METHOD", None),
                getattr(CursorKind, "FUNCTION_TEMPLATE", None),
            }
            if target.kind not in method_kinds or candidate.kind not in method_kinds:
                return False
            if not target.is_virtual_method():
                return False
            if not self._method_signature_matches(candidate, target):
                return False
            parent = candidate.semantic_parent
            target_parent = target.semantic_parent
            if parent is None or target_parent is None:
                return False
            return self._class_derives_from(parent, self._usr(target_parent))
        except Exception:
            return False

    @staticmethod
    def _method_signature_matches(candidate: Cursor, target: Cursor) -> bool:
        """Return whether two method cursors share name and signature."""
        try:
            if candidate.spelling != target.spelling:
                return False
            if candidate.is_static_method() != target.is_static_method():
                return False
            if candidate.is_const_method() != target.is_const_method():
                return False
            candidate_args = candidate.type.argument_types()
            target_args = target.type.argument_types()
            return [item.spelling for item in candidate_args] == [
                item.spelling for item in target_args
            ]
        except Exception:
            return False

    def _find_project_files(self, source_path: str) -> list[str]:
        """Find C++ files in the owning project for a last-resort symbol scan.

        Args:
            source_path: File whose project should be scanned.

        Returns:
            Normalised paths of indexable C/C++ files (bounded).
        """
        if not source_path:
            return []
        try:
            excluded = self._excluded_directories()
            root = Path(source_path).parent
            cmake_root = None
            try:
                from editor.Ironica.plugins.cmake.cmake.scanner import (
                    find_cmake_root,
                )

                cmake_root = find_cmake_root(source_path)
            except Exception:
                cmake_root = None
            if cmake_root:
                root = Path(cmake_root)
            else:
                for parent in (root, *root.parents):
                    if (
                        (parent / "compile_commands.json").is_file()
                        or (parent / ".ds").is_dir()
                        or (parent / ".git").is_dir()
                    ):
                        root = parent
                        break

            suffixes = {
                ".c",
                ".cc",
                ".cpp",
                ".cxx",
                ".c++",
                ".h",
                ".hh",
                ".hpp",
                ".hxx",
                ".inl",
                ".ipp",
                ".tpp",
            }
            files: list[str] = []
            for current, dirs, filenames in os.walk(root, followlinks=False):
                dirs[:] = [name for name in dirs if name not in excluded]
                for filename in filenames:
                    if os.path.splitext(filename)[1].lower() in suffixes:
                        files.append(
                            self._normalise_path(os.path.join(current, filename))
                        )
                        if len(files) >= 400:
                            return sorted(files)
            return sorted(files)
        except Exception:
            return []

    @staticmethod
    def _excluded_directories() -> frozenset:
        """Return directory names skipped while scanning for project files."""
        try:
            from editor.utils.solution.paths import DEFAULT_EXCLUDES

            return frozenset(DEFAULT_EXCLUDES)
        except Exception:
            return frozenset({".git", ".ds", "__pycache__", "node_modules"})

    def _parse_project_file(
        self,
        source_path: str,
        ctx: CppContext,
        active_path: str,
    ) -> Optional[TranslationUnit]:
        """Parse a project file using the same flags as the active file."""
        active_source = getattr(ctx, "source_code", "") or ""
        try:
            mtime = os.stat(source_path).st_mtime_ns
        except OSError:
            if source_path != active_path or not active_source:
                return None
            mtime = 0

        # Use the same flags as the active context
        flags = tuple(cpp_args.args_for_file(source_path, ""))
        unsaved_files = self._unsaved_snapshot(active_path, active_source)
        buffer_key = (
            active_path,
            hash(active_source),
            self._unsaved_digest(unsaved_files),
        )
        key = (
            source_path,
            flags + ("-working-directory=" + os.path.dirname(source_path),),
            mtime,
            buffer_key,
        )
        cached = self._unit_cache.get(key)
        if cached is not None:
            return cached[1]

        index = Index.create()
        parse_args = ["-working-directory=" + os.path.dirname(source_path), *flags]

        tu = self._parse_index(index, source_path, parse_args, unsaved_files)
        if tu is None:
            return None

        if len(self._unit_cache) >= 16:
            self._unit_cache.pop(next(iter(self._unit_cache)))
        self._unit_cache[key] = (index, tu)
        return tu

    def _compile_commands(
        self, source_path: str
    ) -> dict[str, tuple[str, str, list[str]]]:
        database_path = self._find_compilation_database(source_path)
        if not database_path:
            return {}

        cached = self._database_cache.get(database_path)
        if cached is not None:
            return {
                path: (path, directory, arguments)
                for path, (directory, arguments) in cached.items()
            }

        try:
            with open(database_path, "r", encoding="utf-8") as stream:
                entries = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError):
            logger.debug(
                "Could not read compilation database %s", database_path, exc_info=True
            )
            return {}

        commands: dict[str, tuple[str, list[str]]] = {}
        if not isinstance(entries, list):
            return {}

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            directory = entry.get("directory")
            source = entry.get("file")
            if (
                not isinstance(directory, str)
                or not isinstance(source, str)
                or not source
            ):
                continue
            working_directory = self._normalise_path(directory)
            source_file = (
                source
                if os.path.isabs(source)
                else os.path.join(working_directory, source)
            )
            source_file = self._normalise_path(source_file)
            raw_arguments = entry.get("arguments")
            if not isinstance(raw_arguments, list):
                command = entry.get("command")
                if not isinstance(command, str):
                    continue
                try:
                    raw_arguments = shlex.split(command, posix=os.name != "nt")
                except ValueError:
                    continue
            arguments = self._clean_arguments(
                raw_arguments, source_file, working_directory
            )
            commands.setdefault(source_file, (working_directory, arguments))

        self._database_cache[database_path] = commands
        return {
            path: (path, directory, arguments)
            for path, (directory, arguments) in commands.items()
        }

    def _find_compilation_database(self, source_path: str) -> str:
        if not source_path:
            return ""
        if source_path in self._database_path_cache:
            return self._database_path_cache[source_path]

        source_directory = Path(source_path).parent
        inspected: set[Path] = set()
        candidates: list[Path] = []
        for parent in (source_directory, *source_directory.parents):
            direct = parent / "compile_commands.json"
            if direct not in inspected:
                inspected.add(direct)
                if direct.is_file():
                    candidates.append(direct)
            try:
                for child in parent.iterdir():
                    if not child.is_dir():
                        continue
                    candidate = child / "compile_commands.json"
                    if candidate in inspected:
                        continue
                    inspected.add(candidate)
                    if candidate.is_file():
                        candidates.append(candidate)
            except OSError:
                continue

        for extra in self._extra_databases(source_path):
            candidate = Path(extra)
            if candidate not in inspected and candidate.is_file():
                inspected.add(candidate)
                candidates.append(candidate)

        best_path = ""
        best_score = (-1, -1)
        for candidate in candidates:
            try:
                with candidate.open("r", encoding="utf-8") as stream:
                    entries = json.load(stream)
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(entries, list) or not entries:
                continue

            score = (-1, -1)
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                directory = entry.get("directory")
                source = entry.get("file")
                if (
                    not isinstance(directory, str)
                    or not isinstance(source, str)
                    or not source
                ):
                    continue
                if not isinstance(entry.get("arguments"), list) and not isinstance(
                    entry.get("command"), str
                ):
                    continue
                command_directory = self._normalise_path(directory)
                command_source = (
                    source
                    if os.path.isabs(source)
                    else os.path.join(command_directory, source)
                )
                command_source = self._normalise_path(command_source)
                try:
                    common = os.path.commonpath((source_path, command_source))
                    common_depth = len(Path(common).parts)
                except (OSError, ValueError):
                    common_depth = 0
                exact_match = int(command_source == source_path)
                candidate_score = (exact_match, common_depth)
                if candidate_score > score:
                    score = candidate_score

            if score > best_score:
                best_score = score
                best_path = self._normalise_path(candidate)

        self._database_path_cache[source_path] = best_path
        return best_path

    @staticmethod
    def _extra_databases(source_path: str) -> list[str]:
        """Return solution-generated and CMake build databases for *source_path*.

        Args:
            source_path: File whose databases should be discovered.

        Returns:
            Existing ``compile_commands.json`` paths outside the ancestor walk.
        """
        extras: list[str] = []
        try:
            from editor.utils.solution.paths import (
                compile_commands_path,
                is_solution,
            )

            current = Path(source_path).parent
            for parent in (current, *current.parents):
                if is_solution(str(parent)):
                    candidate = compile_commands_path(str(parent))
                    if os.path.isfile(candidate):
                        extras.append(candidate)
                    break
        except Exception:
            pass
        try:
            from editor.Ironica.plugins.cmake.cmake import builddb
            from editor.Ironica.plugins.cmake.cmake.scanner import find_cmake_root

            cmake_root = find_cmake_root(source_path)
            if cmake_root:
                build_dir = builddb.find_build_directory(cmake_root)
                if build_dir:
                    candidate = os.path.join(build_dir, "compile_commands.json")
                    if os.path.isfile(candidate):
                        extras.append(candidate)
        except Exception:
            pass
        return extras

    @staticmethod
    def _clean_arguments(
        raw_arguments: Sequence[str], source_path: str, working_directory: str
    ) -> list[str]:
        arguments = [str(value) for value in raw_arguments]
        while arguments and Path(arguments[0]).name.lower() in {
            "ccache",
            "sccache",
            "distcc",
            "icecc",
        }:
            arguments.pop(0)
        if arguments and not arguments[0].startswith("-"):
            arguments.pop(0)

        drop_single = {"-c", "-S", "-E", "-MD", "-MMD", "-MP", "-MG"}
        drop_value = {
            "-o",
            "-MF",
            "-MT",
            "-MQ",
            "-MJ",
            "-serialize-diagnostics",
            "--serialize-diagnostics",
        }
        cleaned: list[str] = []
        skip_next = False

        for argument in arguments:
            if skip_next:
                skip_next = False
                continue
            if argument in drop_single:
                continue
            if argument in drop_value:
                skip_next = True
                continue
            if argument.startswith(("-MF", "-MT", "-MQ", "-MJ")) and len(argument) > 3:
                continue
            if (
                argument.startswith("-o")
                and len(argument) > 2
                and not argument.startswith(
                    ("-openmp", "-object", "-opaque", "-opt", "-order-file")
                )
            ):
                continue
            if not argument.startswith("-"):
                candidate = (
                    argument
                    if os.path.isabs(argument)
                    else os.path.join(working_directory, argument)
                )
                if NavigationEngine._normalise_path(candidate) == source_path:
                    continue
            cleaned.append(argument)

        return cleaned

    def _parse_translation_unit(
        self,
        source_path: str,
        working_directory: str,
        arguments: Sequence[str],
        ctx: CppContext,
        active_path: str,
    ) -> Optional[TranslationUnit]:
        active_source = getattr(ctx, "source_code", "") or ""
        try:
            mtime = os.stat(source_path).st_mtime_ns
        except OSError:
            if source_path != active_path or not active_source:
                return None
            mtime = 0

        extra = self._header_extra_flags(active_path)
        unsaved_files = self._unsaved_snapshot(active_path, active_source)
        buffer_key = (
            active_path,
            hash(active_source),
            self._unsaved_digest(unsaved_files),
        )
        key = (
            source_path,
            tuple(arguments)
            + tuple(extra)
            + ("-working-directory=" + working_directory,),
            mtime,
            buffer_key,
        )
        cached = self._unit_cache.get(key)
        if cached is not None:
            return cached[1]

        index = Index.create()
        parse_args = [
            "-working-directory=" + working_directory,
            *arguments,
            *extra,
        ]

        tu = self._parse_index(index, source_path, parse_args, unsaved_files)
        if tu is None:
            return None

        missing = self._missing_includes(tu)
        if missing and self._resolve_missing(active_path, missing, arguments):
            refreshed = self._header_extra_flags(active_path)
            if refreshed != extra:
                extra = refreshed
                tu = self._parse_index(
                    index,
                    source_path,
                    [
                        "-working-directory=" + working_directory,
                        *arguments,
                        *extra,
                    ],
                    unsaved_files,
                )

        if len(self._unit_cache) >= 16:
            self._unit_cache.pop(next(iter(self._unit_cache)))
        self._unit_cache[key] = (index, tu)
        return tu

    @staticmethod
    def _strip_pch(arguments: Sequence[str]) -> list[str]:
        """Return *arguments* with any ``-include-pch`` pair removed."""
        stripped: list[str] = []
        index = 0
        while index < len(arguments):
            argument = arguments[index]
            if argument == "-include-pch":
                index += 2
                continue
            if argument.startswith("-include-pch"):
                index += 1
                continue
            stripped.append(argument)
            index += 1
        return stripped

    def _parse_index(
        self,
        index: Index,
        source_path: str,
        parse_args: Sequence[str],
        unsaved_files: Sequence[tuple[str, str]],
    ) -> Optional[TranslationUnit]:
        """Parse *source_path*, retrying without a stale precompiled header."""
        try:
            return index.parse(
                source_path,
                args=list(parse_args),
                unsaved_files=list(unsaved_files),
                options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
            )
        except Exception:
            has_pch = any(
                argument == "-include-pch" or argument.startswith("-include-pch")
                for argument in parse_args
            )
            if not has_pch:
                logger.debug(
                    "Could not parse translation unit %s",
                    source_path,
                    exc_info=True,
                )
                return None
        try:
            return index.parse(
                source_path,
                args=self._strip_pch(parse_args),
                unsaved_files=list(unsaved_files),
                options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
            )
        except Exception:
            logger.debug(
                "Could not parse translation unit %s without PCH",
                source_path,
                exc_info=True,
            )
            return None

    @staticmethod
    def _header_extra_flags(active_path: str) -> list[str]:
        """Return include flags discovered by the C++ header resolver."""
        try:
            from ..intellisense import headers as header_resolution

            return list(header_resolution.extra_flags_for(active_path))
        except Exception:
            return []

    @staticmethod
    def _missing_includes(tu: TranslationUnit) -> list[str]:
        """Return header names the TU reports as not found."""
        missing: set = set()
        try:
            for diagnostic in getattr(tu, "diagnostics", []) or []:
                spelling = getattr(diagnostic, "spelling", "") or ""
                match = re.search(r"'([^']+)' file not found", spelling)
                if match:
                    missing.add(match.group(1))
        except Exception:
            return []
        return sorted(missing)

    def _resolve_missing(
        self, active_path: str, missing: list[str], arguments: Sequence[str]
    ) -> bool:
        """Ask the header resolver to locate *missing* includes."""
        try:
            from ..intellisense import headers as header_resolution

            return bool(
                header_resolution.resolve_missing(missing, active_path, list(arguments))
            )
        except Exception:
            return False


def token_spelling(cursor: Cursor) -> str:
    try:
        return cursor.spelling or cursor.displayname or ""
    except Exception:
        return ""
