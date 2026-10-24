-- Schema for the C++ symbol index (symbols.sqlite)
-- Run this once to create the tables; subsequent runs use CREATE TABLE IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    mtime_ns INTEGER NOT NULL,
    size INTEGER NOT NULL,
    args_digest TEXT NOT NULL DEFAULT '',
    generation INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS symbols (
    usr TEXT NOT NULL,
    cursor_kind TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    qualname TEXT NOT NULL,
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    col INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    end_col INTEGER NOT NULL,
    is_definition INTEGER NOT NULL,
    is_virtual INTEGER NOT NULL,
    is_constructor INTEGER NOT NULL,
    parent_usr TEXT NOT NULL,
    PRIMARY KEY (usr, file, line, col, cursor_kind)
);

CREATE INDEX IF NOT EXISTS symbols_usr ON symbols (usr);
CREATE INDEX IF NOT EXISTS symbols_file ON symbols (file);
CREATE INDEX IF NOT EXISTS symbols_name ON symbols (name);

CREATE TABLE IF NOT EXISTS relations (
    subject_usr TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_usr TEXT NOT NULL,
    origin_file TEXT NOT NULL,
    PRIMARY KEY (subject_usr, predicate, object_usr, origin_file)
);

CREATE INDEX IF NOT EXISTS relations_object
    ON relations (predicate, object_usr);

CREATE TABLE IF NOT EXISTS refs (
    usr TEXT NOT NULL,
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    col INTEGER NOT NULL,
    kind TEXT NOT NULL,
    PRIMARY KEY (usr, file, line, col, kind)
);

CREATE INDEX IF NOT EXISTS refs_usr ON refs (usr);
