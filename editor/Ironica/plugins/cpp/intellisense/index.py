"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Background C++ workspace indexer for the DreamStudio C++ plugin.

Walks workspace C/C++ files on a worker thread, cursor-walks one
translation unit per file for top-level symbols, and persists per-file
records under ``.ds/cpp/index/`` keyed by modification time. Completion
uses :func:`search_for_file` as a fallback when the semantic TU yields
nothing. Progress mirrors the Python trio (``started/progress/finished``)
so the status-bar coordinator shows both languages side by side.

On every run the indexer first refreshes the generated compile database
from ``CMakeLists.txt`` (via the cmake plugin) so third-party includes
resolve before any file is parsed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading

from editor import *

from editor.utils.solution.paths import (
    DEFAULT_EXCLUDES,
    cpp_index_dir,
    is_solution,
)

logger = logging.getLogger("DreamStudio.Cpp.Indexer")

_INDEX_VERSION = 2
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

_indexer_instance = None


def get_cpp_indexer():
    """Return the process-wide :class:`CppIndexer` singleton.

    Returns:
        Shared indexer instance (created on first call).
    """
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
        """Prepare idle indexer state (no threads started).

        Args:
            parent: Optional parent object.
        """
        super().__init__(parent)
        self._lock = threading.Lock()
        self._active = False
        self._pending: str | None = None
        self._generation = 0
        self._memory: dict = {}

    def run(self, root: str) -> None:
        """Index *root* on a worker thread (latest request wins).

        Args:
            root: Workspace root to index.
        """
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

    def search(self, root: str, prefix: str, limit: int = 50) -> list:
        """Return cached index symbols under *root* matching *prefix*.

        Args:
            root: Solution root whose memory cache is searched.
            prefix: Case-insensitive name prefix.
            limit: Maximum rows returned.

        Returns:
            List of ``CppCompletion`` rows (possibly empty).
        """
        from ..models import CppCompletion

        needle = (prefix or "").strip().lower()
        if not needle or not root:
            return []
        rows: list = []
        for symbols in (self._memory.get(os.path.abspath(root)) or {}).values():
            for symbol in symbols:
                name = str(symbol.get("name", ""))
                if name.lower().startswith(needle):
                    rows.append(
                        CppCompletion(
                            text=name,
                            insert_text=name,
                            kind=str(symbol.get("kind", "text")),
                            signature=str(symbol.get("detail", "")),
                        )
                    )
                if len(rows) >= limit:
                    break
            if len(rows) >= limit:
                break
        rows.sort(key=lambda row: row.text.lower())
        return rows[:limit]

    def _run_guarded(self, root: str, generation: int) -> None:
        """Run one pass, then pick up a pending root when superseded.

        Args:
            root: Workspace root to index.
            generation: Run generation used to drop stale passes.
        """
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
        """Refresh the compile DB, then index every C++ file under *root*.

        Args:
            root: Workspace root to index.
            generation: Run generation used to drop stale passes.
        """
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
        try:
            self.indexing_finished.emit()
        except RuntimeError:
            pass

    def _refresh_pch(self, root: str, files: list) -> None:
        """Build the shared precompiled header for *root* (background).

        Runs after symbol indexing so keystrokes never wait on it; a
        failed or skipped build simply leaves completion unaccelerated.

        Args:
            root: Workspace root owning ``.ds/cpp/stable.pch``.
            files: Workspace source files harvested for includes.
        """
        try:
            from . import pch as pch_support

            pch_support.ensure_for_root(root, files)
        except Exception as exc:
            logger.debug("pch refresh failed: %s", exc)

    def _refresh_compile_db(self, root: str) -> None:
        """Regenerate ``.ds/cpp`` artefacts from ``CMakeLists.txt``.

        Args:
            root: Workspace root that may hold a CMake project.
        """
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
        """List indexable C/C++ files under *root*, honouring excludes.

        Args:
            root: Workspace root to walk.

        Returns:
            Sorted absolute paths (capped).
        """
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
        """Return cached-or-fresh index symbols for *path*.

        Args:
            root: Solution root owning the persisted record.
            path: Absolute source path to describe.

        Returns:
            List of symbol dicts.
        """
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
        """Cursor-walk one file's TU for top-level + member symbols.

        Args:
            path: Absolute source path to parse.

        Returns:
            Symbol dicts with ``name``, ``kind``, ``line`` and ``detail``.
        """
        try:
            import clang.cindex as cindex
            from clang.cindex import CursorKind, Index, TranslationUnit
        except Exception as exc:
            logger.debug("libclang unavailable for indexing: %s", exc)
            return []
        try:
            from . import args as cpp_args
        except Exception:
            cpp_args = None  # type: ignore[assignment]
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
                ):
                    scope = f"{parent_name}{spelling}::" if spelling else parent_name
                    for child in cursor.get_children():
                        _record(child, scope)
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


def search_for_file(file_path: str | None, prefix: str, limit: int = 50) -> list:
    """Search the owning solution's index for *prefix* matches.

    Args:
        file_path: File requesting completion (locates the solution).
        prefix: Case-insensitive name prefix.
        limit: Maximum rows returned.

    Returns:
        List of ``CppCompletion`` rows (possibly empty) — never raises.
    """
    try:
        if not file_path or not prefix:
            return []
        root = _solution_root_for(file_path)
        if root is None:
            return []
        return get_cpp_indexer().search(root, prefix, limit)
    except Exception:
        return []


__all__ = ["CppIndexer", "get_cpp_indexer", "search_for_file"]
