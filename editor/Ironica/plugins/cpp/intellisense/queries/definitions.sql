-- name: definitions
-- Return every definition (is_definition = 1) for a given USR,
-- ordered by file, line, column.
SELECT usr, cursor_kind, kind, name, qualname, file,
       line, col, end_line, end_col, is_definition,
       is_virtual, is_constructor, parent_usr
FROM symbols
WHERE usr = ?
  AND is_definition = 1
ORDER BY file, line, col;
