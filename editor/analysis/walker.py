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

from editor.analysis.types import Problem, ProblemProvider, ProblemSeverity


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

    def collect(self) -> List[Problem]:
        """Walk the codebase and return isolated :class:`Problem` items.

        Returns:
            List of diagnostics grouped later by the UI. The method is
            idempotent — repeated calls re-scan from scratch.
        """
        self._problems = []
        self.dictionary_of_errors = {"errors": [], "warnings": []}
        for root, dirs, files in os.walk(self.codebase_path, followlinks=False):
            # Skip symlinked directories to avoid cycles
            dirs[:] = [
                directory
                for directory in dirs
                if directory not in {"venv", ".venv", "__pycache__", ".git"}
                and not os.path.islink(os.path.join(root, directory))
            ]
            for file in files:
                file_path = os.path.join(root, file)
                # Skip symlinked files and non-regular files
                if os.path.islink(file_path):
                    continue
                if pathlib.Path(file_path).suffix in self.required_extensions:
                    # Skip huge files to avoid OOM
                    try:
                        if os.path.getsize(file_path) > 5 * 1024 * 1024:
                            continue
                    except OSError:
                        continue
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            ast.parse(content)
                    except SyntaxError as e:
                        problem = Problem(
                            file_path=file_path,
                            severity=ProblemSeverity.ERROR,
                            message=e.msg or "Syntax error",
                            line=e.lineno or 1,
                            column=e.offset or 1,
                            source="python",
                        )
                        self._problems.append(problem)
                        self.dictionary_of_errors["errors"].append(
                            {
                                "file_path": file_path,
                                "error_line": e.lineno,
                                "error_offset": e.offset,
                                "error_msg": e.msg,
                                "severity": ProblemSeverity.ERROR.value,
                                "message": e.msg,
                                "line": e.lineno,
                                "column": e.offset,
                            }
                        )
                    except (OSError, UnicodeDecodeError) as e:
                        logger.debug("Walker skip %s: %s", file_path, e)
                    except Exception as e:
                        logger.debug("Walker parse error %s: %s", file_path, e)
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
            Dict with ``{"errors": [...], "warnings": [...]}``. Each entry
            contains both legacy keys (``error_msg`` …) and canonical keys
            (``severity``, ``message``, ``line``, ``column``) so either
            consumer can read it. New code should use :meth:`collect`.
        """
        if not self._problems and not self.dictionary_of_errors["errors"]:
            self.collect()
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
        problems: List[Problem] = []
        for err in result.get("errors", []):
            problems.append(Problem.from_dict(err))
        for warn in result.get("warnings", []):
            data = dict(warn)
            data.setdefault("severity", ProblemSeverity.WARNING.value)
            problems.append(Problem.from_dict(data))
        return problems
