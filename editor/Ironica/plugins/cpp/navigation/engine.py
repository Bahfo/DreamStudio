"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Navigation engine for C++ GoTo functionality.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

from clang.cindex import Cursor, CursorKind, TranslationUnit, File

from ..intellisense.engine import CppEngine
from ..models import CppContext

logger = logging.getLogger("DreamStudio.Cpp.Navigation")


@dataclass(frozen=True)
class NavigationResult:
    """A single navigation target."""

    file_path: str
    line: int
    col: int
    display_name: str
    kind: str


@dataclass(frozen=True)
class SymbolContext:
    """Resolved symbol at a cursor position."""

    cursor: Cursor
    tu: TranslationUnit
    file_path: str
    is_definition: bool
    is_declaration: bool
    is_reference: bool
    canonical_cursor: Cursor


class NavigationEngine:
    """Core navigation logic using libclang and workspace index."""

    def __init__(self, cpp_engine: CppEngine) -> None:
        self._engine = cpp_engine

    def _get_cursor_at(
        self, ctx: CppContext
    ) -> Optional[Tuple[Cursor, TranslationUnit, str]]:
        """Get the libclang cursor at the given position."""
        tu = self._engine._tu(ctx)
        if tu is None:
            return None
        clang_path = ctx.file_path or self._engine._cache_key(ctx)
        try:
            # Use UTF-8 byte offset to match libclang's source locations
            offset = self._line_col_to_byte_offset(ctx.source_code, ctx.line, ctx.col)
            location = tu.get_location(clang_path, offset)
            cursor = Cursor.from_location(tu, location)
            if cursor is None or cursor.kind == CursorKind.NO_DECL_FOUND:
                # If no cursor at exact position, try to find include directive on same line
                if self._is_on_include_directive(ctx):
                    inc_cursor = self._find_include_directive_on_line(tu, clang_path, ctx.line, ctx.source_code)
                    if inc_cursor:
                        return inc_cursor, tu, clang_path
                return None
            return cursor, tu, clang_path
        except Exception as exc:
            logger.debug("Failed to get cursor at position: %s", exc)
            return None

    def _is_on_include_directive(self, ctx: CppContext) -> bool:
        """Check if the cursor position is on an include directive line."""
        lines = ctx.source_code.splitlines()
        if ctx.line - 1 < 0 or ctx.line - 1 >= len(lines):
            return False
        line_text = lines[ctx.line - 1].lstrip()
        return line_text.startswith("#include")

    def _find_include_directive_on_line(
        self, tu: TranslationUnit, clang_path: str, line: int, source: str
    ) -> Optional[Cursor]:
        """Find an INCLUSION_DIRECTIVE cursor on the given line."""
        try:
            # Walk the TU to find inclusion directive on this line
            for child in tu.cursor.get_children():
                if child.kind == CursorKind.INCLUSION_DIRECTIVE:
                    loc = child.location
                    if loc.line == line and loc.file and str(loc.file.name) == clang_path:
                        return child
        except Exception as exc:
            logger.debug("Failed to find include directive on line %d: %s", line, exc)
        return None

    @staticmethod
    def _line_col_to_byte_offset(source: str, line: int, col: int) -> int:
        """Convert 1-based line/col to 0-based UTF-8 byte offset."""
        # Source is a Python string (UTF-16 internally), we need byte offset for libclang
        # Split preserving newlines
        lines = source.splitlines(keepends=True)
        line_idx = line - 1
        if line_idx < 0:
            line_idx = 0
        if line_idx >= len(lines):
            line_idx = len(lines) - 1
        # Sum byte lengths of preceding lines
        offset = 0
        for i in range(line_idx):
            offset += len(lines[i].encode("utf-8"))
        # col is 1-based character index, convert to 0-based
        col_idx = col - 1
        if col_idx < 0:
            col_idx = 0
        # Get byte offset within the line
        if col_idx < len(lines[line_idx]):
            line_text = lines[line_idx]
            char_bytes = line_text[:col_idx].encode("utf-8")
            offset += len(char_bytes)
        else:
            offset += len(lines[line_idx].encode("utf-8"))
        return offset

    def _resolve_symbol_context(
        self, cursor: Cursor, tu: TranslationUnit, file_path: str
    ) -> SymbolContext:
        """Resolve the symbol context (definition/declaration/reference)."""
        # Handle include directive specially
        if cursor.kind == CursorKind.INCLUSION_DIRECTIVE:
            return SymbolContext(
                cursor=cursor,
                tu=tu,
                file_path=file_path,
                is_definition=False,
                is_declaration=False,
                is_reference=True,
                canonical_cursor=cursor,
            )

        # Check if cursor is a reference expression kind
        ref_kinds = (
            CursorKind.DECL_REF_EXPR,
            CursorKind.MEMBER_REF_EXPR,
            CursorKind.CALL_EXPR,
            CursorKind.OVERLOADED_DECL_REF,
            CursorKind.TYPE_REF,
            CursorKind.TEMPLATE_REF,
            CursorKind.NAMESPACE_REF,
            CursorKind.VARIABLE_REF,
        )

        is_reference_expr = cursor.kind in ref_kinds

        canonical = cursor.referenced
        if canonical is None:
            canonical = cursor

        # Use canonical cursor for classification
        is_def = canonical.is_definition()
        is_decl = not is_def and canonical.kind in (
            CursorKind.FUNCTION_DECL,
            CursorKind.CXX_METHOD,
            CursorKind.CONSTRUCTOR,
            CursorKind.DESTRUCTOR,
            CursorKind.FIELD_DECL,
            CursorKind.VAR_DECL,
            CursorKind.CLASS_DECL,
            CursorKind.STRUCT_DECL,
            CursorKind.ENUM_DECL,
            CursorKind.TYPEDEF_DECL,
            CursorKind.TYPE_ALIAS_DECL,
            CursorKind.NAMESPACE,
        )
        # Reference if it's a reference expression, or neither def nor decl
        is_ref = is_reference_expr or (not is_def and not is_decl)

        return SymbolContext(
            cursor=cursor,
            tu=tu,
            file_path=file_path,
            is_definition=is_def,
            is_declaration=is_decl,
            is_reference=is_ref,
            canonical_cursor=canonical,
        )

    def _cursor_to_result(
        self, cursor: Cursor, tu: TranslationUnit, file_path: str, kind: str
    ) -> Optional[NavigationResult]:
        """Convert a cursor to a navigation result."""
        try:
            location = cursor.location
            if location.file is None:
                return None
            cursor_file = str(location.file.name)
            line = int(location.line)
            col = int(location.column)
            if line <= 0:
                return None
            display = cursor.spelling or cursor.displayname or "<unknown>"
            return NavigationResult(
                file_path=cursor_file,
                line=line,
                col=max(1, col),
                display_name=display,
                kind=kind,
            )
        except Exception as exc:
            logger.debug("Failed to convert cursor to result: %s", exc)
            return None

    def _inclusion_directive_to_result(
        self, cursor: Cursor, tu: TranslationUnit, file_path: str
    ) -> Optional[NavigationResult]:
        """Convert an INCLUSION_DIRECTIVE cursor to a navigation result."""
        try:
            included_file = cursor.get_included_file()
            if not included_file:
                return None
            included_path = str(included_file.name)
            # Resolve the path using realpath to handle relative paths like /../lib/...
            try:
                real_path = os.path.realpath(included_path)
                if os.path.exists(real_path):
                    included_path = real_path
            except Exception:
                pass
            # If still not found, try to resolve relative to the current file
            if not os.path.exists(included_path):
                base_dir = os.path.dirname(file_path) if file_path else "."
                candidate = os.path.normpath(os.path.join(base_dir, included_path))
                if os.path.exists(candidate):
                    included_path = candidate
            display = cursor.spelling or cursor.displayname or os.path.basename(included_path)
            return NavigationResult(
                file_path=included_path,
                line=1,
                col=1,
                display_name=display,
                kind="include",
            )
        except Exception as exc:
            logger.debug("Failed to convert inclusion directive to result: %s", exc)
            return None

    def _find_definition(
        self, canonical: Cursor, tu: TranslationUnit, file_path: str
    ) -> List[NavigationResult]:
        """Find definition(s) of the canonical cursor."""
        results: List[NavigationResult] = []
        try:
            def_cursor = canonical.get_definition()
            if def_cursor and def_cursor.kind != CursorKind.NO_DECL_FOUND:
                result = self._cursor_to_result(def_cursor, tu, file_path, "definition")
                if result:
                    results.append(result)
        except Exception as exc:
            logger.debug("get_definition failed: %s", exc)
        return results

    def _find_declaration(
        self, canonical: Cursor, tu: TranslationUnit, file_path: str
    ) -> List[NavigationResult]:
        """Find declaration(s) of the canonical cursor."""
        results: List[NavigationResult] = []
        try:
            if canonical.is_definition():
                decl = canonical.referenced
                if decl and decl != canonical and decl.kind != CursorKind.NO_DECL_FOUND:
                    result = self._cursor_to_result(decl, tu, file_path, "declaration")
                    if result:
                        results.append(result)
            else:
                result = self._cursor_to_result(canonical, tu, file_path, "declaration")
                if result:
                    results.append(result)
        except Exception as exc:
            logger.debug("find_declaration failed: %s", exc)
        return results

    def _find_implementations(
        self, canonical: Cursor, tu: TranslationUnit, file_path: str, ctx: CppContext
    ) -> List[NavigationResult]:
        """Find implementations (overrides) of a virtual method."""
        results: List[NavigationResult] = []
        seen: set = set()

        def add_result(cursor: Cursor, kind: str = "implementation"):
            result = self._cursor_to_result(cursor, tu, file_path, kind)
            if result:
                key = (result.file_path, result.line, result.col)
                if key not in seen:
                    seen.add(key)
                    results.append(result)

        try:
            if canonical.kind not in (
                CursorKind.CXX_METHOD,
                CursorKind.FUNCTION_DECL,
                CursorKind.FUNCTION_TEMPLATE,
            ):
                return results

            is_virtual = False
            try:
                is_virtual = canonical.is_virtual_method()
            except Exception:
                pass

            if not is_virtual:
                return results

            # Search within current TU for overrides
            def visit(cursor: Cursor):
                try:
                    if cursor.kind == CursorKind.CXX_METHOD and cursor != canonical:
                        if self._is_override_of(cursor, canonical):
                            add_result(cursor)
                    for child in cursor.get_children():
                        visit(child)
                except Exception:
                    pass

            visit(tu.cursor)

            # Also search workspace index for cross-file overrides
            from ..intellisense.index import get_cpp_indexer

            indexer = get_cpp_indexer()
            solution_root = self._get_solution_root(file_path)
            if solution_root:
                name = canonical.spelling
                if name:
                    symbols = indexer.search(
                        solution_root, name, limit=200, exclude_kinds=set()
                    )
                    for sym in symbols:
                        if sym.kind in ("method", "function") and sym.text == name:
                            try:
                                result = NavigationResult(
                                    file_path=(
                                        sym.signature.split(":")[0]
                                        if ":" in sym.signature
                                        else file_path
                                    ),
                                    line=(
                                        int(sym.signature.split(":")[1])
                                        if ":" in sym.signature
                                        and sym.signature.split(":")[1].isdigit()
                                        else 1
                                    ),
                                    col=1,
                                    display_name=f"{sym.text} (override)",
                                    kind="implementation",
                                )
                                key = (result.file_path, result.line, result.col)
                                if key not in seen:
                                    seen.add(key)
                                    results.append(result)
                            except Exception:
                                continue
        except Exception as exc:
            logger.debug("find_implementations failed: %s", exc)
        return results

    def _find_references_in_tu(
        self, canonical: Cursor, tu: TranslationUnit, file_path: str
    ) -> List[NavigationResult]:
        """Find references within the current translation unit."""
        results: List[NavigationResult] = []
        seen: set = set()

        def visit(cursor: Cursor):
            try:
                if cursor.kind in (
                    CursorKind.DECL_REF_EXPR,
                    CursorKind.MEMBER_REF_EXPR,
                    CursorKind.MEMBER_REF,
                    CursorKind.CALL_EXPR,
                    CursorKind.OVERLOADED_DECL_REF,
                    CursorKind.TYPE_REF,
                ):
                    ref = cursor.referenced
                    if ref and (
                        self._cursors_equivalent(ref, canonical)
                        or self._is_override_of(ref, canonical)
                        or self._is_override_of(canonical, ref)
                    ):
                        result = self._cursor_to_result(
                            cursor, tu, file_path, "reference"
                        )
                        if result:
                            key = (result.file_path, result.line, result.col)
                            if key not in seen:
                                seen.add(key)
                                results.append(result)
            except Exception:
                pass
            try:
                for child in cursor.get_children():
                    visit(child)
            except Exception:
                pass

        try:
            visit(tu.cursor)
        except Exception as exc:
            logger.debug("TU reference search failed: %s", exc)

        return results

    def _cursors_equivalent(self, a: Cursor, b: Cursor) -> bool:
        """Check if two cursors refer to the same entity or override chain."""
        try:
            usr_a = a.get_usr()
            usr_b = b.get_usr()
            if usr_a and usr_a == usr_b:
                return True
        except Exception:
            pass
        try:
            return a.hash == b.hash
        except Exception:
            return False

    def _is_override_of(self, cursor: Cursor, base: Cursor) -> bool:
        """Check if cursor is an override of base virtual method."""
        if cursor.kind != base.kind:
            return False
        if cursor.spelling != base.spelling:
            return False
        if cursor == base:
            return False
        # Both must be virtual methods
        try:
            if not (cursor.is_virtual_method() and base.is_virtual_method()):
                return False
        except Exception:
            return False
        # Must be in different classes
        try:
            cursor_class = cursor.semantic_parent
            base_class = base.semantic_parent
            if not (cursor_class and base_class):
                return False
            if cursor_class == base_class:
                return False
            if cursor_class.spelling == base_class.spelling:
                return False
            if cursor_class.kind not in (
                CursorKind.CLASS_DECL,
                CursorKind.STRUCT_DECL,
            ) or base_class.kind not in (
                CursorKind.CLASS_DECL,
                CursorKind.STRUCT_DECL,
            ):
                return False
            # Check inheritance: cursor_class must inherit from base_class (directly or indirectly)
            # Walk the inheritance chain of cursor_class to find base_class
            return self._class_inherits_from(cursor_class, base_class)
        except Exception:
            return False

    def _class_inherits_from(self, derived: Cursor, base: Cursor) -> bool:
        """Check if derived class inherits from base class (directly or indirectly)."""
        try:
            # Get base specifiers of derived class
            for child in derived.get_children():
                if child.kind == CursorKind.CXX_BASE_SPECIFIER:
                    base_type = child.type
                    if base_type.spelling == base.spelling:
                        return True
                    # Recursively check the base class's bases
                    base_decl = base_type.get_declaration()
                    if base_decl and self._class_inherits_from(base_decl, base):
                        return True
        except Exception:
            pass
        return False

    def _get_solution_root(self, file_path: str) -> Optional[str]:
        """Find the solution root for a file."""
        try:
            from editor.utils.solution.paths import is_solution

            current = os.path.abspath(file_path)
            if os.path.isfile(current):
                current = os.path.dirname(current)
            while True:
                if is_solution(current):
                    return current
                parent = os.path.dirname(current)
                if parent == current:
                    break
                current = parent
        except Exception:
            pass
        return None

    def _find_references_in_workspace(
        self, canonical: Cursor, file_path: str, ctx: CppContext
    ) -> List[NavigationResult]:
        """Find references in the workspace using the indexer."""
        results: List[NavigationResult] = []
        try:
            from ..intellisense.index import get_cpp_indexer, search_for_file

            name = canonical.spelling or canonical.displayname
            if not name:
                return results

            solution_root = self._get_solution_root(file_path)
            if not solution_root:
                return results

            symbols = search_for_file(file_path, name, limit=200)
            for sym in symbols:
                try:
                    file_part = (
                        sym.signature.split(":")[0]
                        if ":" in sym.signature
                        else file_path
                    )
                    line_part = (
                        int(sym.signature.split(":")[1])
                        if ":" in sym.signature
                        and sym.signature.split(":")[1].isdigit()
                        else 1
                    )
                    result = NavigationResult(
                        file_path=file_part,
                        line=line_part,
                        col=1,
                        display_name=f"{sym.text} ({sym.kind})",
                        kind="reference",
                    )
                    results.append(result)
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("Workspace reference search failed: %s", exc)
        return results

    def resolve_at(self, ctx: CppContext) -> Optional[SymbolContext]:
        """Resolve the symbol at the given context position."""
        cursor_data = self._get_cursor_at(ctx)
        if cursor_data is None:
            return None
        cursor, tu, file_path = cursor_data
        return self._resolve_symbol_context(cursor, tu, file_path)

    def get_definition(self, ctx: CppContext) -> List[NavigationResult]:
        """Get definition location(s) for symbol at context."""
        sym = self.resolve_at(ctx)
        if sym is None:
            return []
        if sym.cursor.kind == CursorKind.INCLUSION_DIRECTIVE:
            result = self._inclusion_directive_to_result(sym.cursor, sym.tu, sym.file_path)
            return [result] if result else []
        return self._find_definition(sym.canonical_cursor, sym.tu, sym.file_path)

    def get_declaration(self, ctx: CppContext) -> List[NavigationResult]:
        """Get declaration location(s) for symbol at context."""
        sym = self.resolve_at(ctx)
        if sym is None:
            return []
        if sym.cursor.kind == CursorKind.INCLUSION_DIRECTIVE:
            # For include directives, "declaration" is the same as definition
            result = self._inclusion_directive_to_result(sym.cursor, sym.tu, sym.file_path)
            return [result] if result else []
        return self._find_declaration(sym.canonical_cursor, sym.tu, sym.file_path)

    def get_implementation(self, ctx: CppContext) -> List[NavigationResult]:
        """Get implementation location(s) for symbol at context."""
        sym = self.resolve_at(ctx)
        if sym is None:
            return []
        return self._find_implementations(
            sym.canonical_cursor, sym.tu, sym.file_path, ctx
        )

    def get_references(self, ctx: CppContext) -> List[NavigationResult]:
        """Get all reference locations for symbol at context."""
        sym = self.resolve_at(ctx)
        if sym is None:
            return []
        if sym.cursor.kind == CursorKind.INCLUSION_DIRECTIVE:
            # For include directives, find other inclusions of the same header
            return self._find_include_references(sym.cursor, sym.tu, sym.file_path)

        results: List[NavigationResult] = []
        seen: set = set()

        tu_refs = self._find_references_in_tu(
            sym.canonical_cursor, sym.tu, sym.file_path
        )
        for r in tu_refs:
            key = (r.file_path, r.line, r.col)
            if key not in seen:
                seen.add(key)
                results.append(r)

        ws_refs = self._find_references_in_workspace(
            sym.canonical_cursor, sym.file_path, ctx
        )
        for r in ws_refs:
            key = (r.file_path, r.line, r.col)
            if key not in seen:
                seen.add(key)
                results.append(r)

        return results

    def _find_include_references(
        self, cursor: Cursor, tu: TranslationUnit, file_path: str
    ) -> List[NavigationResult]:
        """Find other inclusions of the same header."""
        results: List[NavigationResult] = []
        seen: set = set()
        try:
            target_name = cursor.spelling
            for child in tu.cursor.get_children():
                if child.kind == CursorKind.INCLUSION_DIRECTIVE:
                    if child.spelling == target_name and child != cursor:
                        result = self._inclusion_directive_to_result(child, tu, file_path)
                        if result:
                            key = (result.file_path, result.line, result.col)
                            if key not in seen:
                                seen.add(key)
                                results.append(result)
        except Exception as exc:
            logger.debug("Include reference search failed: %s", exc)
        return results