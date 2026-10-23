"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Background C++ workspace indexer for the DreamStudio C++ plugin.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from editor.utils.solution.paths import (
    DEFAULT_EXCLUDES,
    cpp_index_dir,
    is_solution,
)

from .symbol_index import (
    FileIndexData,
    IndexedReference,
    IndexedSymbol,
    PREDICATE_BASE_OF,
    PREDICATE_OVERRIDDEN_BY,
    SymbolIndex,
)

logger = logging.getLogger("DreamStudio.Cpp.Indexer")

_INDEX_VERSION = 3
_MAX_FILES = 2000
_MAX_CURSORS_PER_FILE = 3000
_MAX_INDEX_SYMBOLS_PER_FILE = 60000
_MAX_INDEX_REFERENCES_PER_FILE = 60000

_COMPLETION_FUNCTION_KINDS = frozenset(
    {
        "FUNCTION_DECL",
        "FUNCTION_TEMPLATE",
        "CXX_METHOD",
        "CONSTRUCTOR",
        "DESTRUCTOR",
        "CXX_CONSTRUCTOR",
        "CXX_DESTRUCTOR",
        "CXX_CONVERSION",
        "LAMBDA_EXPR",
    }
)

_CONSTRUCTOR_KINDS = frozenset({"CONSTRUCTOR", "CXX_CONSTRUCTOR"})

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

_KIND_BY_CURSOR = {
    "FUNCTION_DECL": "function",
    "FUNCTION_TEMPLATE": "function",
    "CXX_METHOD": "method",
    "CONSTRUCTOR": "method",
    "DESTRUCTOR": "method",
    "CXX_CONSTRUCTOR": "method",
    "CXX_DESTRUCTOR": "method",
    "CXX_CONVERSION": "method",
    "FIELD_DECL": "field",
    "VAR_DECL": "variable",
    "PARM_DECL": "parameter",
    "CLASS_DECL": "type",
    "STRUCT_DECL": "type",
    "CLASS_TEMPLATE": "type",
    "CLASS_TEMPLATE_PARTIAL_SPEC": "type",
    "TYPEDEF_DECL": "type",
    "TYPE_ALIAS_DECL": "type",
    "TYPE_ALIAS_TEMPLATE_DECL": "type",
    "ENUM_DECL": "enum",
    "ENUM_CONSTANT_DECL": "constant",
    "NAMESPACE": "namespace",
    "MACRO_DEFINITION": "macro",
    "MACRO_INSTANTIATION": "macro",
}

NON_GLOBAL_COMPLETION_KINDS: frozenset = frozenset(
    {"field", "method", "parameter"}
)

_indexer_instance = None


def get_cpp_indexer():
    """Return the process-wide :class:`CppIndexer` singleton."""
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = CppIndexer()
    return _indexer_instance


def _cpp_suffixes() -> set:
    """Return indexed C/C++ file suffixes from the language registry."""
    suffixes = {
        ".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx", ".ixx",
    }
    try:
        from editor.Ironica.language_engine import LanguageRegistry

        config = LanguageRegistry.get_config("cpp") or {}
        for extension in config.get("extensions", []):
            suffixes.add(f".{str(extension).lstrip('.').lower()}")
    except Exception:
        pass
    return suffixes


def _solution_root_for(path: str) -> str | None:
    """Return the solution root for *path* via the ``.ds`` marker walk."""
    current = os.path.abspath(path)
    if os.path.isfile(current):
        current = os.path.dirname(current)
    while True:
        if is_solution(current):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _record_name(root: str, path: str) -> str:
    """Return the persisted record filename for *path* under *root*."""
    digest = hashlib.sha1(os.path.abspath(path).encode("utf-8")).hexdigest()
    return os.path.join(cpp_index_dir(root), f"{digest}.json")


class CppIndexer(QObject):
    """Background C++ symbol indexer with Python-like progress signals."""

    indexing_started = pyqtSignal(int)
    indexing_progress = pyqtSignal(int, int)
    indexing_finished = pyqtSignal()

    def __init__(self, parent=None) -> None:
        """Prepare idle indexer state (no threads started)."""
        super().__init__(parent)
        self._lock = threading.Lock()
        self._active = False
        self._pending: str | None = None
        self._generation = 0
        self._memory: dict = {}
        self._sysmemory: dict = {}
        self._save_lock = threading.Lock()
        self._save_pending: set[str] = set()
        self._save_thread: threading.Thread | None = None
        try:
            from . import sysindex as sysindex_support

            self._sysmemory = sysindex_support.load()
        except Exception as exc:
            logger.debug("sysindex preload skipped: %s", exc)

    def run(self, root: str) -> None:
        """Index *root* on a worker thread (latest request wins)."""
        if not root or not os.path.isdir(root):
            return
        with self._lock:
            if self._active:
                self._pending = os.path.abspath(root)
                return
            self._active = True
            self._generation += 1
            generation = self._generation
        thread = threading.Thread(
            name="DreamStudio-CppIndexer",
            target=self._run_guarded,
            args=(os.path.abspath(root), generation),
            daemon=True,
        )
        thread.start()

    def search(
        self,
        root: str,
        prefix: str,
        limit: int = 50,
        exclude_kinds: frozenset | set | None = None,
    ) -> list:
        """Return cached index symbols under *root* matching *prefix*."""
        from ..models import CppCompletion

        needle = (prefix or "").strip().lower()
        if not needle or not root:
            return []
        excluded = (
            NON_GLOBAL_COMPLETION_KINDS
            if exclude_kinds is None
            else frozenset(exclude_kinds)
        )
        rows: list = []
        seen: set = set()
        for symbols in (self._memory.get(os.path.abspath(root)) or {}).values():
            for symbol in symbols:
                name = str(symbol.get("name", ""))
                if not name.lower().startswith(needle):
                    continue
                kind = str(symbol.get("kind", "text"))
                if kind in excluded:
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    CppCompletion(
                        text=name,
                        insert_text=name,
                        kind=kind,
                        signature=str(symbol.get("detail", "")),
                    )
                )
                if len(rows) >= limit:
                    break
            if len(rows) >= limit:
                break
        rows.sort(key=lambda row: row.text.lower())
        return rows[:limit]

    def search_sys(
        self,
        prefix: str,
        limit: int = 50,
        exclude_kinds: frozenset | set | None = None,
    ) -> list:
        """Return preloaded system-index rows matching *prefix*."""
        try:
            from . import sysindex as sysindex_support

            return sysindex_support.search(
                self._sysmemory, prefix, limit,
                exclude_kinds=exclude_kinds,
            )
        except Exception as exc:
            logger.debug("sysindex search failed: %s", exc)
            return []

    def _run_guarded(self, root: str, generation: int) -> None:
        """Run one pass, then pick up a pending root when superseded."""
        try:
            self._run_pass(root, generation)
        except Exception as exc:
            logger.debug("c++ index pass failed: %s", exc)
            try:
                self.indexing_finished.emit()
            except RuntimeError:
                pass
        finally:
            with self._lock:
                pending = self._pending
                self._pending = None
                if pending is None or pending == root:
                    self._active = False
                    return
                self._generation += 1
                generation = self._generation
            self._run_guarded(pending, generation)

    def _run_pass(self, root: str, generation: int) -> None:
        """Refresh the compile DB, then index every C++ file under *root*."""
        self.indexing_started.emit(1)
        self._refresh_compile_db(root)
        if generation != self._generation:
            self.indexing_finished.emit()
            return
        files = self._collect_files(root)
        self.indexing_started.emit(max(1, len(files)))
        cached = self._memory.setdefault(os.path.abspath(root), {})
        symbol_index = self._symbol_index(root)
        done = 0
        for path in files:
            if generation != self._generation:
                break
            try:
                symbols, data = self._index_file(root, path)
                cached[path] = symbols
                if data is not None:
                    if symbol_index is not None:
                        symbol_index.replace_file(data)
                    self._write_completion_record(root, path, symbols)
            except Exception as exc:
                logger.debug("c++ index skipped %s: %s", path, exc)
            done += 1
            try:
                self.indexing_progress.emit(done, len(files))
            except RuntimeError:
                return
        if generation == self._generation and symbol_index is not None:
            if len(files) < _MAX_FILES:
                symbol_index.prune_files({os.path.abspath(path) for path in files})
            symbol_index.mark_ready(generation)
        if generation == self._generation:
            self._refresh_pch(root, files)
        if generation == self._generation:
            self._refresh_sysindex(root, files, generation)
        try:
            self.indexing_finished.emit()
        except RuntimeError:
            pass

    def _refresh_sysindex(self, root: str, files: list, generation: int) -> None:
        """Build the per-machine system index, then preload it."""
        try:
            from . import sysindex as sysindex_support
            from . import args as cpp_args

            base = (
                cpp_args.args_for_file(files[0], "")
                if files
                else ["-x", "c++", "-std=c++20"]
            )
            result = sysindex_support.build(
                files,
                base,
                progress=lambda done, total: self._emit_sysindex_progress(
                    done, total
                ),
                cancelled=lambda: generation != self._generation,
            )
            logger.info("sysindex built: %s", result)
            self._sysmemory = sysindex_support.load()
        except Exception as exc:
            logger.debug("sysindex refresh failed: %s", exc)

    def _emit_sysindex_progress(self, done: int, total: int) -> None:
        """Forward system-index progress to the shared trio."""
        try:
            if done <= 1:
                self.indexing_started.emit(max(1, total))
            self.indexing_progress.emit(done, max(1, total))
        except RuntimeError:
            pass

    def _refresh_pch(self, root: str, files: list) -> None:
        """Build the shared precompiled header for *root* (background)."""
        try:
            from . import pch as pch_support

            pch_support.ensure_for_root(root, files)
        except Exception as exc:
            logger.debug("pch refresh failed: %s", exc)

    def _refresh_compile_db(self, root: str) -> None:
        """Regenerate ``.ds/cpp`` artefacts from every CMake project below *root*.

        Args:
            root: Workspace root to scan for ``CMakeLists.txt`` projects.
        """
        try:
            from editor.Ironica.plugins.cmake.cmake.scanner import scan_project
            from editor.Ironica.plugins.cmake.cmake.generator import generate_many
        except Exception as exc:
            logger.debug("cmake bridge unavailable: %s", exc)
            return
        try:
            solution_root = _solution_root_for(root) or os.path.abspath(root)
            models = []
            for cmake_root in self._cmake_project_roots(root):
                model = scan_project(cmake_root)
                if model.targets or model.include_dirs or model.packages:
                    models.append(model)
                self._refresh_external_build(cmake_root)
            if models:
                result = generate_many(solution_root, models)
                logger.info(
                    "cmake database refreshed: %d entries at %s",
                    result.get("entries", 0),
                    result.get("compile_commands", ""),
                )
        except Exception as exc:
            logger.debug("cmake generate failed: %s", exc)

    def _refresh_external_build(self, cmake_root: str) -> None:
        """Export ``compile_commands.json`` from a configured build tree.

        Args:
            cmake_root: Directory holding the project's ``CMakeLists.txt``.
        """
        try:
            from editor.Ironica.plugins.cmake.cmake import builddb

            build_dir = builddb.find_build_directory(cmake_root)
            if build_dir:
                builddb.ensure_compile_commands(cmake_root, build_dir)
        except Exception as exc:
            logger.debug("cmake build export skipped for %s: %s", cmake_root, exc)

    @staticmethod
    def _cmake_project_roots(root: str) -> list:
        """Return directories under *root* that declare a CMake project.

        Args:
            root: Workspace root to walk.

        Returns:
            Topmost absolute project directories containing ``CMakeLists.txt``
            (bounded); nested ``add_subdirectory`` projects are folded into
            their owning root.
        """
        found: list = []
        try:
            for current, directories, files in os.walk(root):
                directories[:] = [
                    item for item in directories if item not in DEFAULT_EXCLUDES
                ]
                if "CMakeLists.txt" in files:
                    found.append(os.path.abspath(current))
                    if len(found) >= 50:
                        break
        except Exception as exc:
            logger.debug("cmake project discovery failed: %s", exc)
        roots: list = []
        for candidate in sorted(found, key=lambda item: item.count(os.sep)):
            if any(
                candidate.startswith(root_path + os.sep)
                for root_path in roots
            ):
                continue
            roots.append(candidate)
        return roots

    def _collect_files(self, root: str) -> list:
        """List indexable C/C++ files under *root*, honouring excludes."""
        suffixes = _cpp_suffixes()
        found: list = []
        for current, directories, files in os.walk(root):
            directories[:] = [
                item for item in directories if item not in DEFAULT_EXCLUDES
            ]
            for name in files:
                if os.path.splitext(name)[1].lower() in suffixes:
                    found.append(os.path.join(current, name))
                    if len(found) >= _MAX_FILES:
                        return sorted(found)
        return sorted(found)

    def _symbol_index(self, root: str) -> SymbolIndex | None:
        """Return an initialized symbol index for the solution owning *root*."""
        try:
            solution_root = _solution_root_for(root) or os.path.abspath(root)
            symbol_index = SymbolIndex(solution_root)
            if symbol_index.initialize():
                return symbol_index
        except Exception as exc:
            logger.debug("symbol index initialization failed: %s", exc)
        return None

    def note_saved(self, path: str) -> None:
        """Queue one saved C/C++ file for incremental index maintenance."""
        if not path:
            return
        absolute = os.path.abspath(path)
        if os.path.basename(absolute) in {
            "CMakeLists.txt",
            "compile_commands.json",
        }:
            root = _solution_root_for(absolute) or os.path.dirname(absolute)
            self.run(root)
            return
        if os.path.splitext(absolute)[1].lower() not in _cpp_suffixes():
            return
        if not os.path.isfile(absolute):
            return
        with self._save_lock:
            self._save_pending.add(absolute)
            if self._save_thread is not None and self._save_thread.is_alive():
                return
            self._save_thread = threading.Thread(
                name="DreamStudio-CppIndexer-Save",
                target=self._run_saved_files,
                daemon=True,
            )
            self._save_thread.start()

    def _run_saved_files(self) -> None:
        """Drain the incremental save queue on a single worker thread."""
        while True:
            with self._save_lock:
                if not self._save_pending:
                    self._save_thread = None
                    return
                path = self._save_pending.pop()
            try:
                self._index_saved_file(path)
            except Exception as exc:
                logger.debug("incremental index failed for %s: %s", path, exc)

    def _index_saved_file(self, path: str) -> None:
        """Refresh the index and completion cache for one saved file."""
        root = _solution_root_for(path)
        if root is None:
            return
        symbols, data = self._index_file(root, path)
        if data is None:
            return
        symbol_index = self._symbol_index(root)
        if symbol_index is not None:
            symbol_index.replace_file(data)
        self._write_completion_record(root, path, symbols)
        with self._lock:
            self._memory.setdefault(os.path.abspath(root), {})[path] = symbols

    def _write_completion_record(
        self, root: str, path: str, symbols: list
    ) -> None:
        """Persist the lightweight completion record for *path*."""
        try:
            mtime = os.path.getmtime(path)
            record_path = _record_name(root, path)
            os.makedirs(os.path.dirname(record_path), exist_ok=True)
            tmp_path = record_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {"version": _INDEX_VERSION, "mtime": mtime, "symbols": symbols},
                    handle,
                )
            os.replace(tmp_path, record_path)
        except OSError:
            pass

    def _index_file(
        self, root: str, path: str
    ) -> tuple[list, FileIndexData | None]:
        """Parse one file once and return completion plus navigation records."""
        try:
            file_stat = os.stat(path)
        except OSError:
            return [], None
        try:
            from clang.cindex import CursorKind, Index, TranslationUnit
        except Exception as exc:
            logger.debug("libclang unavailable for indexing: %s", exc)
            return [], None
        try:
            from . import args as cpp_args
        except Exception:
            cpp_args = None
        flags = (
            cpp_args.args_for_file(path, "", solution_root=root)
            if cpp_args is not None
            else ["-x", "c++", "-std=c++20"]
        )
        try:
            index = Index.create()
            tu = index.parse(
                path,
                args=flags,
                options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
            )
        except Exception as exc:
            logger.debug("index parse failed %s: %s", path, exc)
            return [], None
        if tu is None:
            return [], None

        absolute = os.path.abspath(path)
        same_file = os.path.normcase(absolute)
        reference_kinds = {
            getattr(CursorKind, name)
            for name in _REFERENCE_KIND_NAMES
            if hasattr(CursorKind, name)
        }
        method_kinds = {
            getattr(CursorKind, name)
            for name in ("CXX_METHOD", "CXX_CONVERSION")
            if hasattr(CursorKind, name)
        }
        class_kinds = {
            getattr(CursorKind, name)
            for name in ("CLASS_DECL", "STRUCT_DECL", "CLASS_TEMPLATE")
            if hasattr(CursorKind, name)
        }
        base_specifier = getattr(CursorKind, "CXX_BASE_SPECIFIER", None)
        completion_symbols: list = []
        completion_seen: set[str] = set()
        symbols: list[IndexedSymbol] = []
        symbol_seen: set[tuple] = set()
        relations: list[tuple[str, str, str]] = []
        relation_seen: set[tuple[str, str, str]] = set()
        references: list[IndexedReference] = []
        reference_seen: set[tuple[str, int, int, str]] = set()

        children: list = []
        try:
            children = list(tu.cursor.get_children())
        except Exception:
            children = []
        stack = [
            (child, "", True)
            for child in reversed(children)
        ]
        while stack:
            cursor, parent_name, completion_scope = stack.pop()
            try:
                location = cursor.location
                location_file = (
                    location.file.name if location and location.file else ""
                )
            except Exception:
                continue
            if not location_file:
                continue
            if os.path.normcase(os.path.abspath(location_file)) != same_file:
                continue
            kind_name = getattr(cursor.kind, "name", "")
            spelling = getattr(cursor, "spelling", "") or ""
            icon = _KIND_BY_CURSOR.get(kind_name)
            try:
                line = int(location.line or 0)
                column = int(location.column or 0)
            except Exception:
                line = 0
                column = 0

            if (
                spelling
                and icon is not None
                and completion_scope
                and len(completion_symbols) < _MAX_CURSORS_PER_FILE
                and spelling not in completion_seen
            ):
                completion_seen.add(spelling)
                detail = parent_name or getattr(cursor, "displayname", "")
                completion_symbols.append(
                    {
                        "name": spelling,
                        "kind": icon,
                        "line": line,
                        "detail": str(detail or "")[:160],
                    }
                )

            usr = self._cursor_usr(cursor)
            if (
                spelling
                and icon is not None
                and usr
                and len(symbols) < _MAX_INDEX_SYMBOLS_PER_FILE
            ):
                key = (usr, same_file, line, column, kind_name)
                if key not in symbol_seen:
                    symbol_seen.add(key)
                    extent = getattr(cursor, "extent", None)
                    end = getattr(extent, "end", None) if extent else None
                    end_line = max(0, int(getattr(end, "line", 1) or 1) - 1)
                    end_col = max(0, int(getattr(end, "column", 1) or 1) - 1)
                    is_virtual = False
                    if kind_name in method_kinds:
                        try:
                            is_virtual = bool(cursor.is_virtual_method())
                        except Exception:
                            is_virtual = False
                    qualname = f"{parent_name}{spelling}".rstrip(":")
                    parent_usr = self._cursor_parent_usr(cursor)
                    symbols.append(
                        IndexedSymbol(
                            usr=usr,
                            cursor_kind=kind_name,
                            kind=icon,
                            name=spelling,
                            qualname=qualname,
                            file=absolute,
                            line=max(0, line - 1),
                            col=max(0, column - 1),
                            end_line=end_line,
                            end_col=end_col,
                            is_definition=self._cursor_is_definition(cursor),
                            is_virtual=is_virtual,
                            is_constructor=kind_name in _CONSTRUCTOR_KINDS,
                            parent_usr=parent_usr,
                        )
                    )

            if cursor.kind in method_kinds and kind_name not in _CONSTRUCTOR_KINDS:
                for base_cursor in self._overridden_cursors(cursor):
                    base_usr = self._cursor_usr(base_cursor)
                    relation = (usr, PREDICATE_OVERRIDDEN_BY, base_usr)
                    if base_usr and usr and relation not in relation_seen:
                        relation_seen.add(relation)
                        relations.append(relation)

            try:
                cursor_children = list(cursor.get_children())
            except Exception:
                cursor_children = []

            if cursor.kind in class_kinds and base_specifier is not None:
                for child in cursor_children:
                    if child.kind != base_specifier:
                        continue
                    base_usr = self._base_usr(child)
                    relation = (usr, PREDICATE_BASE_OF, base_usr)
                    if base_usr and usr and relation not in relation_seen:
                        relation_seen.add(relation)
                        relations.append(relation)

            if (
                cursor.kind in reference_kinds
                and len(references) < _MAX_INDEX_REFERENCES_PER_FILE
            ):
                referenced_usr = self._referenced_usr(cursor)
                key = (
                    referenced_usr,
                    max(0, line - 1),
                    max(0, column - 1),
                    kind_name,
                )
                if referenced_usr and key not in reference_seen:
                    reference_seen.add(key)
                    references.append(
                        IndexedReference(
                            usr=referenced_usr,
                            line=max(0, line - 1),
                            col=max(0, column - 1),
                            kind=kind_name,
                        )
                    )

            child_scope = (
                completion_scope and kind_name not in _COMPLETION_FUNCTION_KINDS
            )
            if kind_name in {
                "NAMESPACE",
                "CLASS_DECL",
                "STRUCT_DECL",
                "CLASS_TEMPLATE",
                "CLASS_TEMPLATE_PARTIAL_SPEC",
                "ENUM_DECL",
            }:
                child_parent = (
                    f"{parent_name}{spelling}::" if spelling else parent_name
                )
            elif spelling and kind_name in _COMPLETION_FUNCTION_KINDS:
                child_parent = f"{parent_name}{spelling}::"
            else:
                child_parent = parent_name
            for child in reversed(cursor_children):
                stack.append((child, child_parent, child_scope))

        digest = hashlib.sha1("\0".join(flags).encode("utf-8")).hexdigest()
        data = FileIndexData(
            path=absolute,
            mtime_ns=file_stat.st_mtime_ns,
            size=file_stat.st_size,
            args_digest=digest,
            symbols=tuple(symbols),
            relations=tuple(relations),
            references=tuple(references),
        )
        return completion_symbols, data

    @staticmethod
    def _cursor_usr(cursor) -> str:
        """Return a cursor USR without propagating libclang failures."""
        try:
            return str(cursor.get_usr() or "")
        except Exception:
            return ""

    @staticmethod
    def _cursor_parent_usr(cursor) -> str:
        """Return the semantic parent USR for *cursor*."""
        try:
            parent = cursor.semantic_parent
            return str(parent.get_usr() or "") if parent is not None else ""
        except Exception:
            return ""

    @staticmethod
    def _cursor_is_definition(cursor) -> bool:
        """Return whether *cursor* is a definition."""
        try:
            return bool(cursor.is_definition())
        except Exception:
            return False

    @staticmethod
    def _overridden_cursors(cursor) -> list:
        """Return base methods overridden by *cursor*."""
        try:
            return list(cursor.get_overridden_cursors())
        except Exception:
            return []

    @staticmethod
    def _referenced_usr(cursor) -> str:
        """Return the USR targeted by a reference cursor."""
        try:
            referenced = cursor.referenced
            return str(referenced.get_usr() or "") if referenced is not None else ""
        except Exception:
            return ""

    @staticmethod
    def _base_usr(specifier) -> str:
        """Return the base-class USR for a base specifier cursor."""
        try:
            referenced = specifier.referenced
            if referenced is not None:
                usr = referenced.get_usr()
                if usr:
                    return str(usr)
        except Exception:
            pass
        try:
            declaration = specifier.type.get_declaration()
            return str(declaration.get_usr() or "") if declaration is not None else ""
        except Exception:
            return ""


def search_for_file(
    file_path: str | None,
    prefix: str,
    limit: int = 50,
    exclude_kinds: frozenset | set | None = None,
) -> list:
    """Search the owning solution's index for *prefix* matches."""
    try:
        if not file_path or not prefix:
            return []
        root = _solution_root_for(file_path)
        if root is None:
            return []
        return get_cpp_indexer().search(
            root, prefix, limit, exclude_kinds=exclude_kinds
        )
    except Exception:
        return []


__all__ = [
    "CppIndexer",
    "NON_GLOBAL_COMPLETION_KINDS",
    "get_cpp_indexer",
    "search_for_file",
]
