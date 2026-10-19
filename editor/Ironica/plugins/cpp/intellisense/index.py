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

logger = logging.getLogger("DreamStudio.Cpp.Indexer")

_INDEX_VERSION = 3
_MAX_FILES = 2000
_MAX_CURSORS_PER_FILE = 3000

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
        done = 0
        for path in files:
            if generation != self._generation:
                break
            try:
                cached[path] = self._symbols_for(root, path)
            except Exception as exc:
                logger.debug("c++ index skipped %s: %s", path, exc)
            done += 1
            try:
                self.indexing_progress.emit(done, len(files))
            except RuntimeError:
                return
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
        """Regenerate ``.ds/cpp`` artefacts from ``CMakeLists.txt``."""
        try:
            from editor.Ironica.plugins.cmake.cmake.scanner import (
                find_cmake_root,
                scan_project,
            )
            from editor.Ironica.plugins.cmake.cmake.generator import generate
        except Exception as exc:
            logger.debug("cmake bridge unavailable: %s", exc)
            return
        try:
            solution_root = _solution_root_for(root) or os.path.abspath(root)
            cmake_root = find_cmake_root(root)
            if cmake_root is None:
                return
            model = scan_project(cmake_root)
            if not model.targets and not model.packages:
                return
            generate(solution_root, model)
        except Exception as exc:
            logger.debug("cmake generate failed: %s", exc)

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

    def _symbols_for(self, root: str, path: str) -> list:
        """Return cached-or-fresh index symbols for *path*."""
        record_path = _record_name(root, path)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return []
        try:
            if os.path.isfile(record_path):
                with open(record_path, encoding="utf-8") as handle:
                    record = json.load(handle)
                if (
                    isinstance(record, dict)
                    and record.get("version") == _INDEX_VERSION
                    and record.get("mtime") == mtime
                    and isinstance(record.get("symbols"), list)
                ):
                    return record["symbols"]
        except Exception:
            pass
        symbols = self._walk_file(path)
        try:
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
        return symbols

    def _walk_file(self, path: str) -> list:
        """Cursor-walk one file's TU for top-level + member symbols."""
        try:
            import clang.cindex as cindex
            from clang.cindex import CursorKind, Index, TranslationUnit
        except Exception as exc:
            logger.debug("libclang unavailable for indexing: %s", exc)
            return []
        try:
            from . import args as cpp_args
        except Exception:
            cpp_args = None
        try:
            flags = (
                cpp_args.args_for_file(path, "")
                if cpp_args is not None
                else ["-x", "c++", "-std=c++20"]
            )
            index = Index.create()
            tu = index.parse(
                path,
                args=flags,
                options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
            )
        except Exception as exc:
            logger.debug("index parse failed %s: %s", path, exc)
            return []
        _ = cindex
        symbols: list = []
        seen: set = set()

        def _record(cursor, parent_name: str = "") -> None:
            """Record one cursor and recurse into namespaces and records."""
            if len(symbols) >= _MAX_CURSORS_PER_FILE:
                return
            try:
                location_file = (
                    cursor.location.file.name
                    if cursor.location and cursor.location.file
                    else ""
                )
            except Exception:
                return
            if os.path.abspath(location_file or "") != os.path.abspath(path):
                return
            spelling = getattr(cursor, "spelling", "") or ""
            if spelling and spelling not in seen:
                kind_name = getattr(cursor.kind, "name", "")
                icon = _KIND_BY_CURSOR.get(kind_name)
                if icon is not None:
                    seen.add(spelling)
                    try:
                        line = int(cursor.location.line or 0)
                    except Exception:
                        line = 0
                    detail = parent_name or getattr(cursor, "displayname", "")
                    symbols.append(
                        {
                            "name": spelling,
                            "kind": icon,
                            "line": line,
                            "detail": str(detail or "")[:160],
                        }
                    )
            try:
                kind = cursor.kind
                if kind in (
                    CursorKind.NAMESPACE,
                    CursorKind.CLASS_DECL,
                    CursorKind.STRUCT_DECL,
                    CursorKind.CLASS_TEMPLATE,
                    CursorKind.ENUM_DECL,
                ):
                    scope = f"{parent_name}{spelling}::" if spelling else parent_name
                    for child in cursor.get_children():
                        _record(child, scope)
                elif kind == CursorKind.LINKAGE_SPEC:
                    for child in cursor.get_children():
                        _record(child, parent_name)
            except Exception:
                pass

        try:
            for child in tu.cursor.get_children():
                _record(child)
                if len(symbols) >= _MAX_CURSORS_PER_FILE:
                    break
        except Exception as exc:
            logger.debug("index walk failed %s: %s", path, exc)
        return symbols


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
