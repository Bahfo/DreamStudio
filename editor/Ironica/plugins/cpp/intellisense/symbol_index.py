"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
SQLite-backed C++ symbol and relation index for DreamStudio navigation.
"""

from __future__ import annotations

import functools
import os
import sqlite3
import time
from dataclasses import dataclass, field

from editor.utils.solution.paths import cpp_symbol_index_path, is_solution

def _load_sql(filename: str) -> str:
    """Read a .sql file relative to this module's directory."""
    base = os.path.dirname(__file__)  # editor/Ironica/plugins/cpp/intellisense
    path = os.path.join(base, "queries", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


SCHEMA_VERSION = 1
_SCHEMA = _load_sql('schema.sql')

PREDICATE_BASE_OF = "base_of"
PREDICATE_OVERRIDDEN_BY = "overridden_by"



@dataclass(frozen=True)
class IndexedSymbol:
    """One declaration or definition location stored in the index."""

    usr: str
    cursor_kind: str
    kind: str
    name: str
    qualname: str
    file: str
    line: int
    col: int
    end_line: int
    end_col: int
    is_definition: bool
    is_virtual: bool
    is_constructor: bool
    parent_usr: str


@dataclass(frozen=True)
class IndexedReference:
    """One project reference to a symbol, relative to its owning file."""

    usr: str
    line: int
    col: int
    kind: str


@dataclass(frozen=True)
class FileIndexData:
    """Complete index payload for one translation unit."""

    path: str
    mtime_ns: int
    size: int
    args_digest: str
    symbols: tuple[IndexedSymbol, ...] = field(default_factory=tuple)
    relations: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    references: tuple[IndexedReference, ...] = field(default_factory=tuple)


class SymbolIndex:
    """Read/write facade over ``.ds/cpp/index/symbols.sqlite``."""

    def __init__(self, root: str) -> None:
        """Bind this index to workspace *root*."""
        self.root = os.path.abspath(root)
        self.path = cpp_symbol_index_path(self.root)

    def exists(self) -> bool:
        """Return ``True`` when the database file is present."""
        return os.path.isfile(self.path)

    def initialize(self, recreate: bool = False) -> bool:
        """Create the schema when needed and return readiness."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if recreate:
            self._remove_files()
        try:
            connection = self._connect(writer=True, create=True)
            try:
                connection.executescript(_SCHEMA)
                row = connection.execute(
                    "SELECT value FROM meta WHERE key = 'schema_version'"
                ).fetchone()
                if row is not None and int(row[0]) != SCHEMA_VERSION:
                    raise ValueError("stale symbol-index schema")
                if row is None:
                    connection.execute(
                        "INSERT INTO meta (key, value) VALUES (?, ?)",
                        ("schema_version", str(SCHEMA_VERSION)),
                    )
                    connection.commit()
            finally:
                connection.close()
            return True
        except (sqlite3.DatabaseError, ValueError, OSError):
            self._remove_files()
            if recreate:
                return False
            return self.initialize(recreate=True)

    def is_ready(self) -> bool:
        """Return ``True`` when a completed pass populated this index."""
        connection = self._read_connect()
        if connection is None:
            return False
        try:
            row = connection.execute(
                "SELECT value FROM meta WHERE key = 'ready'"
            ).fetchone()
            return row is not None and str(row[0]) == "1"
        except sqlite3.DatabaseError:
            return False
        finally:
            connection.close()

    def generation(self) -> int:
        """Return the last completed generation, or ``0``."""
        connection = self._read_connect()
        if connection is None:
            return 0
        try:
            row = connection.execute(
                "SELECT value FROM meta WHERE key = 'generation'"
            ).fetchone()
            return int(row[0]) if row is not None else 0
        except (sqlite3.DatabaseError, ValueError):
            return 0
        finally:
            connection.close()

    def mark_ready(self, generation: int, compile_db_digest: str = "") -> None:
        """Mark a completed full pass so readers may trust the index."""
        connection = self._connect(writer=True)
        if connection is None:
            return
        try:
            entries = {
                "ready": "1",
                "generation": str(generation),
                "compile_db_digest": compile_db_digest,
                "updated_at": str(int(time.time() * 1000)),
            }
            connection.executemany(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                entries.items(),
            )
            connection.commit()
        except sqlite3.DatabaseError:
            connection.rollback()
        finally:
            connection.close()

    def replace_file(self, data: FileIndexData) -> bool:
        """Atomically replace all records owned by ``data.path``."""
        connection = self._connect(writer=True)
        if connection is None:
            return False
        try:
            path = os.path.abspath(data.path)
            connection.execute("DELETE FROM symbols WHERE file = ?", (path,))
            connection.execute("DELETE FROM relations WHERE origin_file = ?", (path,))
            connection.execute("DELETE FROM refs WHERE file = ?", (path,))
            connection.executemany(
                "INSERT OR REPLACE INTO symbols VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        symbol.usr,
                        symbol.cursor_kind,
                        symbol.kind,
                        symbol.name,
                        symbol.qualname,
                        symbol.file,
                        symbol.line,
                        symbol.col,
                        symbol.end_line,
                        symbol.end_col,
                        int(symbol.is_definition),
                        int(symbol.is_virtual),
                        int(symbol.is_constructor),
                        symbol.parent_usr,
                    )
                    for symbol in data.symbols
                ],
            )
            connection.executemany(
                "INSERT OR REPLACE INTO relations "
                "(subject_usr, predicate, object_usr, origin_file) "
                "VALUES (?, ?, ?, ?)",
                [
                    (subject, predicate, obj, path)
                    for subject, predicate, obj in data.relations
                ],
            )
            connection.executemany(
                "INSERT OR REPLACE INTO refs (usr, file, line, col, kind) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (reference.usr, path, reference.line, reference.col, reference.kind)
                    for reference in data.references
                ],
            )
            connection.execute(
                "INSERT OR REPLACE INTO files "
                "(path, mtime_ns, size, args_digest, generation) "
                "VALUES (?, ?, ?, ?, 0)",
                (path, data.mtime_ns, data.size, data.args_digest),
            )
            connection.commit()
            return True
        except sqlite3.DatabaseError:
            connection.rollback()
            return False
        finally:
            connection.close()

    def remove_file(self, path: str) -> None:
        """Remove all records owned by *path*."""
        connection = self._connect(writer=True)
        if connection is None:
            return
        try:
            absolute = os.path.abspath(path)
            connection.execute("DELETE FROM symbols WHERE file = ?", (absolute,))
            connection.execute(
                "DELETE FROM relations WHERE origin_file = ?", (absolute,)
            )
            connection.execute("DELETE FROM refs WHERE file = ?", (absolute,))
            connection.execute("DELETE FROM files WHERE path = ?", (absolute,))
            connection.commit()
        except sqlite3.DatabaseError:
            connection.rollback()
        finally:
            connection.close()

    def prune_files(self, keep_paths: set[str]) -> int:
        """Remove records for files no longer present in *keep_paths*."""
        connection = self._connect(writer=True)
        if connection is None:
            return 0
        removed = 0
        try:
            existing = [
                str(row[0]) for row in connection.execute("SELECT path FROM files")
            ]
            stale = [path for path in existing if path not in keep_paths]
            for path in stale:
                connection.execute("DELETE FROM symbols WHERE file = ?", (path,))
                connection.execute(
                    "DELETE FROM relations WHERE origin_file = ?", (path,)
                )
                connection.execute("DELETE FROM refs WHERE file = ?", (path,))
                connection.execute("DELETE FROM files WHERE path = ?", (path,))
                removed += 1
            connection.commit()
        except sqlite3.DatabaseError:
            connection.rollback()
            return 0
        finally:
            connection.close()
        return removed

    def definitions(self, usr: str) -> list[IndexedSymbol]:
        """Return definition locations for *usr*."""
        return self._locations(usr, definition=True)

    def declarations(self, usr: str) -> list[IndexedSymbol]:
        """Return declaration locations for *usr*."""
        return self._locations(usr, definition=False)

    def overrides(self, usr: str) -> list[IndexedSymbol]:
        """Return definitions of methods overriding *usr*."""
        subjects = self._relation_objects(usr, PREDICATE_OVERRIDDEN_BY)
        return self._locations_for_usrs(subjects, definitions_first=True)

    def derived_types(self, usr: str) -> list[IndexedSymbol]:
        """Return definitions of classes derived from *usr*."""
        subjects = self._relation_objects(usr, PREDICATE_BASE_OF)
        return self._locations_for_usrs(subjects, definitions_first=True)

    def references(self, usr: str) -> list[IndexedReference]:
        """Return stored project references to *usr*."""
        connection = self._read_connect()
        if connection is None:
            return []
        try:
            rows = connection.execute(
                "SELECT file, line, col, kind FROM refs "
                "WHERE usr = ? ORDER BY file, line, col",
                (usr,),
            )
            return [
                IndexedReference(
                    usr=usr,
                    line=int(row[1]),
                    col=int(row[2]),
                    kind=str(row[3]),
                )
                for row in rows
            ]
        except sqlite3.DatabaseError:
            return []
        finally:
            connection.close()

    def reference_locations(self, usr: str) -> list[tuple[str, int, int]]:
        """Return ``(file, line, col)`` tuples for references to *usr*."""
        connection = self._read_connect()
        if connection is None:
            return []
        try:
            rows = connection.execute(
                "SELECT file, line, col FROM refs "
                "WHERE usr = ? ORDER BY file, line, col",
                (usr,),
            )
            return [(str(row[0]), int(row[1]), int(row[2])) for row in rows]
        except sqlite3.DatabaseError:
            return []
        finally:
            connection.close()

    def counts(self) -> dict[str, int]:
        """Return row counts useful for diagnostics and tests."""
        connection = self._read_connect()
        if connection is None:
            return {}
        try:
            return {
                table: int(
                    connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                )
                for table in ("files", "symbols", "relations", "refs")
            }
        except sqlite3.DatabaseError:
            return {}
        finally:
            connection.close()

    def _locations(self, usr: str, definition: bool) -> list[IndexedSymbol]:
        """Return indexed locations for *usr* filtered by definition state."""
        connection = self._read_connect()
        if connection is None:
            return []
        try:
            rows = connection.execute(
                "SELECT usr, cursor_kind, kind, name, qualname, file, line, col, "
                "end_line, end_col, is_definition, is_virtual, is_constructor, "
                "parent_usr FROM symbols "
                "WHERE usr = ? AND is_definition = ? "
                "ORDER BY file, line, col",
                (usr, int(definition)),
            )
            return [self._symbol_from_row(row) for row in rows]
        except sqlite3.DatabaseError:
            return []
        finally:
            connection.close()

    def _locations_for_usrs(
        self, usrs: list[str], definitions_first: bool = False
    ) -> list[IndexedSymbol]:
        """Return locations for multiple USRs in one bounded query."""
        if not usrs:
            return []
        connection = self._read_connect()
        if connection is None:
            return []
        rows: list[IndexedSymbol] = []
        try:
            unique = list(dict.fromkeys(usrs))
            for start in range(0, len(unique), 400):
                chunk = unique[start : start + 400]
                placeholders = ", ".join("?" for _ in chunk)
                order = (
                    "ORDER BY is_definition DESC, file, line, col"
                    if definitions_first
                    else "ORDER BY file, line, col"
                )
                cursor = connection.execute(
                    "SELECT usr, cursor_kind, kind, name, qualname, file, line, "
                    "col, end_line, end_col, is_definition, is_virtual, "
                    "is_constructor, parent_usr FROM symbols "
                    f"WHERE usr IN ({placeholders}) {order}",
                    chunk,
                )
                rows.extend(self._symbol_from_row(row) for row in cursor)
            return rows
        except sqlite3.DatabaseError:
            return []
        finally:
            connection.close()

    def _relation_objects(self, usr: str, predicate: str) -> list[str]:
        """Return object USRs for one relation predicate."""
        connection = self._read_connect()
        if connection is None:
            return []
        try:
            rows = connection.execute(
                "SELECT DISTINCT object_usr FROM relations "
                "WHERE subject_usr = ? AND predicate = ?",
                (usr, predicate),
            )
            return [str(row[0]) for row in rows]
        except sqlite3.DatabaseError:
            return []
        finally:
            connection.close()

    @staticmethod
    def _symbol_from_row(row) -> IndexedSymbol:
        """Convert one SQLite row into an :class:`IndexedSymbol`."""
        return IndexedSymbol(
            usr=str(row[0]),
            cursor_kind=str(row[1]),
            kind=str(row[2]),
            name=str(row[3]),
            qualname=str(row[4]),
            file=str(row[5]),
            line=int(row[6]),
            col=int(row[7]),
            end_line=int(row[8]),
            end_col=int(row[9]),
            is_definition=bool(row[10]),
            is_virtual=bool(row[11]),
            is_constructor=bool(row[12]),
            parent_usr=str(row[13]),
        )

    def _read_connect(self) -> sqlite3.Connection | None:
        """Open a read-only connection, or return ``None`` when absent."""
        if not self.exists():
            return None
        try:
            connection = sqlite3.connect(self.path, timeout=5.0)
            connection.execute("PRAGMA busy_timeout = 5000")
            return connection
        except sqlite3.DatabaseError:
            return None

    def _connect(
        self, writer: bool = False, create: bool = False
    ) -> sqlite3.Connection | None:
        """Open a configured database connection."""
        if not self.exists():
            if not writer or not create:
                return None
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            connection = sqlite3.connect(self.path, timeout=10.0)
            connection.execute("PRAGMA busy_timeout = 10000")
            if writer:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("PRAGMA synchronous = NORMAL")
            return connection
        except sqlite3.DatabaseError:
            return None

    def _remove_files(self) -> None:
        """Delete the database and its WAL sidecars."""
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except OSError:
                pass


def solution_root_for_path(path: str) -> str | None:
    """Return the nearest ancestor carrying a DreamStudio solution marker."""
    if not path:
        return None
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


@functools.lru_cache(maxsize=32)
def symbol_index_for_root(root: str) -> SymbolIndex:
    """Return a cached index facade for workspace *root*."""
    return SymbolIndex(root)


def symbol_index_for_path(path: str) -> SymbolIndex | None:
    """Return an existing index for the solution owning *path*."""
    root = solution_root_for_path(path)
    if root is None:
        return None
    index = symbol_index_for_root(root)
    return index if index.exists() else None


__all__ = [
    "FileIndexData",
    "IndexedReference",
    "IndexedSymbol",
    "PREDICATE_BASE_OF",
    "PREDICATE_OVERRIDDEN_BY",
    "SCHEMA_VERSION",
    "SymbolIndex",
    "solution_root_for_path",
    "symbol_index_for_path",
    "symbol_index_for_root",
]
