-- name: references
-- Return every project-internal reference for a given USR,
-- ordered by file, line, column.
SELECT file, line, col, kind
FROM refs
WHERE usr = ?
ORDER BY file, line, col;
