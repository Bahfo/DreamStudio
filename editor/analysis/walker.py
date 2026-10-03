"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Errors analysis module walker for Python files written using `ast` and `os`.
This error walker scans whole directories and files for problems. It returns
a detailed dictionary of file path of error, line number, and a description
of the error provided by `ast` syntax errors.

The walker is a ``ProblemProvider`` plugin: it emits the isolated
``Problem`` model so the UI widget never needs to import this module.
"""

from editor import *

import io
import logging
import re
import tokenize

from editor.analysis.types import Problem, ProblemProvider, ProblemSeverity
from editor.utils.solution.paths import DEFAULT_EXCLUDES

logger = logging.getLogger(__name__)

#: Comment markers that become WARNING diagnostics (yellow squiggle).
_STYLE_MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK|BUG)\b", re.IGNORECASE)

#: Lines longer than this become TYPO/style diagnostics (blue squiggle).
_MAX_LINE_LENGTH = 120

#: Cap for extra (non-error) diagnostics per file so noisy files cannot
#: flood the Problems tab; syntax errors are never capped.
_MAX_EXTRA_PER_FILE = 30

#: Files at or above this size are treated as "major" and indexed first.
_MAJOR_FILE_BYTES = 20 * 1024

#: A file touched within this window is also treated as "major".
_MAJOR_RECENCY_SECONDS = 3600

#: Hard ceiling per file so one huge module cannot stall a worker thread.
_MAX_FILE_BYTES = 5 * 1024 * 1024


def analyze_source(file_path: str, content: str) -> List[Problem]:
    """Analyze already-loaded *content* for *file_path*.

    Shared by the workspace walker and by the live-buffer worker so the
    typing path never touches the disk and both paths emit identical
    diagnostics.

    Args:
        file_path: Path reported on every emitted diagnostic.
        content: Full source text of the file.

    A syntax error never short-circuits the pipeline: the parse diagnostic is
    reported *and* every recoverable style hint is still emitted, so a file
    that is temporarily invalid while typing keeps showing its other problems.

    Returns:
        List of :class:`Problem` items: an optional syntax ERROR followed by
        the recoverable style hints (overlong lines, marker comments).
    """
    if len(content.encode("utf-8", "ignore")) > _MAX_FILE_BYTES:
        return []
    problems: List[Problem] = []
    try:
        ast.parse(content)
    except SyntaxError as exc:
        problems.append(
            Problem(
                file_path=file_path,
                severity=ProblemSeverity.ERROR,
                message=exc.msg or "Syntax error",
                line=exc.lineno or 1,
                column=exc.offset or 1,
                source="python",
            )
        )
    except (ValueError, MemoryError, RecursionError) as exc:
        problems.append(
            Problem(
                file_path=file_path,
                severity=ProblemSeverity.ERROR,
                message=f"Could not parse file: {exc}",
                line=1,
                column=1,
                source="python",
            )
        )
    problems.extend(_StyleHints(file_path, content).problems())
    return problems


class _StyleHints:
    """Emit cheap WARNING/TYPO diagnostics from an already-read buffer.

    No extra I/O: reuses the source text to flag overlong lines (TYPO) and
    ``TODO``-style comment markers (WARNING). Diagnostics are capped per
    file so a noisy module cannot flood the Problems tab.

    Attributes:
        file_path: Path reported on every diagnostic.
        content: Source text to inspect.
    """

    def __init__(self, file_path: str, content: str) -> None:
        self.file_path = file_path
        self.content = content
        self._problems: List[Problem] = []

    def problems(self) -> List[Problem]:
        """Return collected style diagnostics.

        Returns:
            List of TYPO/WARNING :class:`Problem` items, capped per file.
        """
        extra = 0
        try:
            for lineno, line in enumerate(self.content.splitlines(), 1):
                if extra >= _MAX_EXTRA_PER_FILE:
                    return list(self._problems)
                if len(line) > _MAX_LINE_LENGTH:
                    self._problems.append(
                        Problem(
                            file_path=self.file_path,
                            severity=ProblemSeverity.TYPO,
                            message=f"Line too long ({len(line)} > {_MAX_LINE_LENGTH})",
                            line=lineno,
                            column=_MAX_LINE_LENGTH + 1,
                            end_line=lineno,
                            end_column=len(line.rstrip()) + 1,
                            source="python",
                        )
                    )
                    extra += 1
            try:
                tokens = tokenize.generate_tokens(io.StringIO(self.content).readline)
                for tok in tokens:
                    if extra >= _MAX_EXTRA_PER_FILE:
                        return list(self._problems)
                    if tok.type != tokenize.COMMENT:
                        continue
                    match = _STYLE_MARKER_RE.search(tok.string)
                    if match is None:
                        continue
                    self._problems.append(
                        Problem(
                            file_path=self.file_path,
                            severity=ProblemSeverity.WARNING,
                            message=f"{match.group(1).upper()} marker found",
                            line=tok.start[0],
                            column=tok.start[1] + match.start() + 1,
                            end_line=tok.start[0],
                            end_column=tok.start[1] + match.end() + 1,
                            source="python",
                        )
                    )
                    extra += 1
            except (tokenize.TokenError, SyntaxError, IndentationError):
                pass
        except Exception as exc:
            logger.warning("Style-hint scan failed %s: %s", self.file_path, exc)
        return list(self._problems)


def index_python_files(
    root: str, known: Optional[dict] = None
) -> tuple[List[tuple], int]:
    """List analyzable Python files under *root*, "major" files first.

    Only ``stat`` calls happen here — no file is opened — so indexing is
    cheap enough to repeat continuously for change detection.

    Args:
        root: Directory to walk.
        known: Optional ``{path: (mtime, size)}`` map of already indexed
            files. When given, only new or modified files are returned.

    Returns:
        Tuple of ``(entries, skipped)`` where each entry is
        ``(path, mtime, size)`` sorted so large/recently edited files come
        first, and ``skipped`` counts unreadable or oversized files.
    """
    entries: List[tuple] = []
    skipped = 0
    now = time.time()
    try:
        for dirpath, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [
                directory
                for directory in dirs
                if directory not in DEFAULT_EXCLUDES
                and not os.path.islink(os.path.join(dirpath, directory))
            ]
            for name in files:
                if not name.endswith((".py", ".pyi")):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    stat = os.stat(path)
                except OSError as exc:
                    skipped += 1
                    logger.debug("Index skip %s: %s", path, exc)
                    continue
                if stat.st_size > _MAX_FILE_BYTES:
                    skipped += 1
                    continue
                stamp = (stat.st_mtime, stat.st_size)
                if known is not None and known.get(path) == stamp:
                    continue
                entries.append(
                    (path, stamp[0], stamp[1], now - stamp[0] < _MAJOR_RECENCY_SECONDS)
                )
    except OSError as exc:
        logger.warning("Index walk failed for %s: %s", root, exc)
    entries.sort(key=lambda item: (not item[3], -item[2], -item[1], item[0]))
    return [(path, mtime, size) for path, mtime, size, _recent in entries], skipped


class ProblemsAnalyzer(ProblemProvider):
    """Walk a codebase and emit :class:`Problem` diagnostics.

    This is the built-in Python syntax provider. Additional providers
    (linters, spell checkers, language servers) implement the same
    ``ProblemProvider`` contract and feed the same widget with no UI
    changes.

    Attributes:
        codebase_path: Root directory to scan.
        required_extensions: File suffixes considered for analysis.
    """

    def __init__(self, codebase_path: str):
        self.codebase_path = codebase_path
        self.required_extensions = [".py", ".pyi"]
        self.dictionary_of_errors: dict = {"errors": [], "warnings": []}
        self._problems: List[Problem] = []
        self.skipped_files: int = 0

    def collect(self) -> List[Problem]:
        """Walk the codebase and return isolated :class:`Problem` items.

        Returns:
            List of diagnostics grouped later by the UI. The method is
            idempotent — repeated calls re-scan from scratch.
        """
        self._problems = []
        self.skipped_files = 0
        self.dictionary_of_errors = {"errors": [], "warnings": []}
        entries, skipped = index_python_files(self.codebase_path)
        self.skipped_files += skipped
        for file_path, _mtime, _size in entries:
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
            except (OSError, UnicodeDecodeError) as exc:
                self.skipped_files += 1
                logger.warning("Walker skip %s: %s", file_path, exc)
                continue
            except Exception as exc:
                self.skipped_files += 1
                logger.warning("Walker read error %s: %s", file_path, exc)
                continue
            self._problems.extend(analyze_source(file_path, content))
        return list(self._problems)

    def return_analysis_result(self) -> None:
        """Legacy entry point — populates ``dictionary_of_errors``.

        Prefer :meth:`collect` for new code. Kept for backward
        compatibility with older callers.
        """
        self.collect()

    def return_errors(self) -> dict:
        """Legacy entry point returning the old dict shape.

        Returns:
            Dict with ``{"errors": [...], "warnings": [...]}`` derived from
            the last :meth:`collect` for backward compatibility.
        """
        if not self._problems:
            self.collect()
        errors = []
        for problem in self._problems:
            errors.append(
                {
                    "file_path": problem.file_path,
                    "error_line": problem.line,
                    "error_offset": problem.column,
                    "error_msg": problem.message,
                    "severity": problem.severity.value,
                    "message": problem.message,
                    "line": problem.line,
                    "column": problem.column,
                }
            )
        self.dictionary_of_errors = {"errors": errors, "warnings": []}
        return self.dictionary_of_errors

    def to_problems(self, result: Optional[dict] = None) -> List[Problem]:
        """Convert a legacy result dict to :class:`Problem` objects.

        Args:
            result: Legacy dict from :meth:`return_errors`. When ``None``
                the last :meth:`collect` result is used.

        Returns:
            Isolated problem list ready for ``ProblemsWidget.set_problems``.
        """
        if result is None:
            return list(self._problems)
        from editor.debugger.problems_widget import _normalize_problems

        return _normalize_problems(
            result.get("errors", []) + result.get("warnings", [])
        )
