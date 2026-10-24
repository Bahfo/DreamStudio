-- name: overrides
-- Return every method that overrides the given USR (virtual methods).
-- Joins relations (subject_usr -> object_usr via overridden_by) with symbols.
SELECT DISTINCT s.usr, s.cursor_kind, s.kind, s.name, s.qualname, s.file,
       s.line, s.col, s.end_line, s.end_col, s.is_definition,
       s.is_virtual, s.is_constructor, s.parent_usr
FROM symbols s
JOIN relations r ON s.usr = r.subject_usr
WHERE r.object_usr = ?
  AND r.predicate = ?
  AND s.is_definition = 1
ORDER BY s.file, s.line, s.col;
