"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Per-machine system-header symbol index for the C++ plugin.

Workspace files change constantly, but third-party headers (SDL, OpenSSL,
Eigen, …) do not. This module collects the project's transitive include
graph, parses each header once per machine with the existing cursor walk,
and persists records under ``~/.dreamstudio/cpp-sysindex/``. Completion
serves matching rows in milliseconds while the semantic engine converges
behind them. A failed or partial build simply contributes no rows.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os

from editor import *

logger = logging.getLogger("DreamStudio.Cpp.SysIndex")

_MANIFEST_FILENAME = "manifest.json"
_MAX_HEADERS = 2000
_INDEX_VERSION = 3


def _store_root() -> str:
    """Return the per-machine system-index directory (uncreated)."""
    return os.path.join(
        Path.home(), ".dreamstudio", "cpp-sysindex", _roots_hash()
    )


def _roots_hash() -> str:
    """Hash the compiler include roots so toolchain changes rebuild."""
    try:
        from ..autocompletion.includes import system_include_dirs

        roots = sorted(system_include_dirs())
    except Exception:
        roots = []
    digest = hashlib.sha1()
    digest.update(json.dumps(roots, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()[:16]


def _record_name(header: str) -> str:
    """Return the persisted record filename for an absolute *header*."""
    digest = hashlib.sha1(os.path.abspath(header).encode("utf-8")).hexdigest()
    return os.path.join(_store_root(), f"{digest}.json")


def collect_graph(seed_files: list, base_flags: list) -> list:
    """Collect the transitive include graph for *seed_files*.

    Each harvested header is resolved with the shared locator (explicit
    ``-I`` dirs, system roots, bounded project walk) and its own
    includes are followed to a fixpoint. Never raises.

    Args:
        seed_files: Absolute workspace source paths to start from.
        base_flags: Flags already in effect (their ``-I`` dirs seed it).

    Returns:
        Sorted absolute header paths (capped).
    """
    try:
        from . import headers as header_resolution
        from . import pch as pch_support
    except Exception as exc:
        logger.debug("sysindex graph skipped: %s", exc)
        return []
    try:
        search_dirs = header_resolution._known_include_dirs(base_flags or [])
        anchor = os.path.commonpath(
            [os.path.abspath(path) for path in seed_files if path]
        )
        if os.path.isfile(anchor):
            anchor = os.path.dirname(anchor)
    except Exception:
        search_dirs = []
        anchor = ""
    try:
        pending = []
        for path in seed_files:
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    head = handle.read(32768)
            except OSError:
                continue
            pending.extend(pch_support._INCLUDE_RE.findall(head))
    except Exception:
        return []
    found: dict = {}
    queue = list(pending)
    while queue and len(found) < _MAX_HEADERS:
        open_char, name = queue.pop(0)
        name = str(name).strip()
        if not name or name in found:
            continue
        if open_char == '"' and anchor:
            candidate = name if os.path.isabs(name) else os.path.join(anchor, name)
            if os.path.isfile(candidate):
                found[name] = os.path.abspath(candidate)
                queue.extend(_header_includes(os.path.abspath(candidate)))
                continue
        located = header_resolution.locate_header(name, search_dirs, anchor)
        if not located:
            found[name] = ""
            continue
        for directory in located:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate):
                found[name] = os.path.abspath(candidate)
                queue.extend(_header_includes(os.path.abspath(candidate)))
                break
        else:
            found[name] = ""
    return sorted(path for path in found.values() if path)


def _header_includes(header: str) -> list:
    """Return raw ``(open_char, name)`` includes from a header's head."""
    try:
        from . import pch as pch_support

        with open(header, encoding="utf-8", errors="replace") as handle:
            head = handle.read(32768)
        return pch_support._INCLUDE_RE.findall(head)
    except OSError:
        return []


def _walk_header(header: str, base_flags: list) -> list:
    """Cursor-walk one header with *base_flags* into symbol dicts.

    Args:
        header: Absolute header path to parse.
        base_flags: Flags for the parse.

    Returns:
        Symbol dicts (possibly empty) — never raises.
    """
    try:
        import clang.cindex as cindex
        from clang.cindex import Index, TranslationUnit

        from .index import _KIND_BY_CURSOR, _MAX_CURSORS_PER_FILE
    except Exception as exc:
        logger.debug("sysindex walk skipped: %s", exc)
        return []
    _ = cindex
    try:
        tu = Index.create().parse(
            header,
            args=list(base_flags or []),
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
        )
    except Exception as exc:
        logger.debug("sysindex parse failed %s: %s", header, exc)
        return []
    symbols: list = []
    seen: set = set()

    def _record(cursor, parent_name: str = "") -> None:
        """Record one cursor, recursing into namespaces and records."""
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
        if os.path.abspath(location_file or "") != os.path.abspath(header):
            return
        spelling = getattr(cursor, "spelling", "") or ""
        if spelling and spelling not in seen:
            from clang.cindex import CursorKind

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
            from clang.cindex import CursorKind

            if cursor.kind in (
                CursorKind.NAMESPACE,
                CursorKind.CLASS_DECL,
                CursorKind.STRUCT_DECL,
                CursorKind.CLASS_TEMPLATE,
                CursorKind.ENUM_DECL,
            ):
                scope = f"{parent_name}{spelling}::" if spelling else parent_name
                for child in cursor.get_children():
                    _record(child, scope)
            elif cursor.kind == CursorKind.LINKAGE_SPEC:
                # System headers wrap declarations in extern "C" blocks;
                # their children live in the enclosing scope.
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
        logger.debug("sysindex walk failed %s: %s", header, exc)
    return symbols


def build(
    seed_files: list,
    base_flags: list,
    progress=None,
    cancelled=None,
) -> dict:
    """Build system-index records for the graph under *seed_files*.

    Parses only headers whose mtime changed since their record. Never
    raises; partial progress persists.

    Args:
        seed_files: Absolute workspace source paths to start from.
        base_flags: Flags for header parses.
        progress: Optional ``(done, total)`` callable per header.
        cancelled: Optional callable returning ``True`` to abort.

    Returns:
        ``{"headers": N, "parsed": M}`` counts.
    """
    store = _store_root()
    try:
        os.makedirs(store, exist_ok=True)
    except OSError as exc:
        logger.debug("sysindex store skipped: %s", exc)
        return {"headers": 0, "parsed": 0}
    graph = collect_graph(seed_files, base_flags)
    parsed = 0
    for position, header in enumerate(graph, 1):
        if cancelled is not None and cancelled():
            break
        try:
            record_path = _record_name(header)
            mtime = os.path.getmtime(header)
            if os.path.isfile(record_path):
                with open(record_path, encoding="utf-8") as handle:
                    record = json.load(handle)
                if (
                    isinstance(record, dict)
                    and record.get("version") == _INDEX_VERSION
                    and record.get("mtime") == mtime
                    and isinstance(record.get("symbols"), list)
                ):
                    if progress is not None:
                        progress(position, len(graph))
                    continue
            symbols = _walk_header(header, base_flags)
            tmp_path = record_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "version": _INDEX_VERSION,
                        "header": header,
                        "mtime": mtime,
                        "symbols": symbols,
                    },
                    handle,
                )
            os.replace(tmp_path, record_path)
            parsed += 1
        except (OSError, ValueError) as exc:
            logger.debug("sysindex record skipped %s: %s", header, exc)
        if progress is not None:
            try:
                progress(position, len(graph))
            except Exception:
                pass
    try:
        manifest_path = os.path.join(store, _MANIFEST_FILENAME)
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump({"version": _INDEX_VERSION, "headers": sorted(graph)}, handle)
    except OSError as exc:
        logger.debug("sysindex manifest skipped: %s", exc)
    return {"headers": len(graph), "parsed": parsed}


def load() -> dict:
    """Load every persisted record into ``{header: [symbols]}``.

    Returns:
        In-memory map of ``header path -> [symbols]`` (possibly empty).
    """
    memory: dict = {}
    try:
        store = _store_root()
        if not os.path.isdir(store):
            return memory
        for name in sorted(os.listdir(store)):
            if not name.endswith(".json") or name == _MANIFEST_FILENAME:
                continue
            try:
                with open(os.path.join(store, name), encoding="utf-8") as handle:
                    record = json.load(handle)
                symbols = record.get("symbols") if isinstance(record, dict) else None
                if isinstance(symbols, list):
                    header = (
                        record.get("header")
                        if isinstance(record, dict) and record.get("header")
                        else name
                    )
                    memory[header] = symbols
            except (OSError, ValueError):
                continue
    except Exception as exc:
        logger.debug("sysindex load failed: %s", exc)
    return memory


def search(
    memory: dict,
    prefix: str,
    limit: int = 50,
    exclude_kinds: frozenset | set | None = None,
) -> list:
    """Return index rows from *memory* matching *prefix*.

    Args:
        memory: Preloaded ``{key: [symbol dicts]}`` map.
        prefix: Case-insensitive name prefix.
        limit: Maximum rows returned.
        exclude_kinds: Kinds skipped as never valid bare identifiers.
            Defaults to the shared non-global set from ``index``.

    Returns:
        List of ``CppCompletion`` rows (possibly empty).
    """
    from ..models import CppCompletion

    needle = (prefix or "").strip().lower()
    if not needle or not memory:
        return []
    if exclude_kinds is None:
        try:
            from .index import NON_GLOBAL_COMPLETION_KINDS as _excluded
        except Exception:
            _excluded = frozenset({"field", "method", "parameter"})
        excluded = _excluded
    else:
        excluded = frozenset(exclude_kinds)
    rows: list = []
    seen: set = set()
    for symbols in memory.values():
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


__all__ = ["build", "collect_graph", "load", "search"]
