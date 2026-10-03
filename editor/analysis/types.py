"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Isolated problem data model for DreamStudio.

This module defines the single data contract between analysis backends
(``walker``, linters, spell checkers, language servers …) and the UI
(``ProblemsWidget``). The widget knows only this model — never the walker
— so new providers can be added without touching any UI code.
"""

from editor import *


class ProblemSeverity(str, Enum):
    """Severity of a single diagnostic.

    Attributes:
        ERROR: Blocking problem (red) — ``assets/system/problem.png``.
        WARNING: Non-blocking warning (yellow) — ``assets/system/warning.png``.
        TYPO: Spelling / style hint (blue) — ``assets/system/spell_check.png``.
        INFO: Informational note (teal) — ``assets/system/info.png``.
    """

    ERROR = "error"
    WARNING = "warning"
    TYPO = "typo"
    INFO = "info"

    @classmethod
    def coerce(cls, value: object) -> "ProblemSeverity":
        """Coerce *value* (str / enum / None) to a severity.

        Unknown values fall back to ``ERROR`` so the UI always has an icon.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if member.value == normalized:
                    return member
            # Common aliases from linters / VS Code.
            if normalized in {"err", "e", "problem", "fatal"}:
                return cls.ERROR
            if normalized in {"warn", "w"}:
                return cls.WARNING
            if normalized in {"information", "informational", "note"}:
                return cls.INFO
            if normalized in {"spell", "spelling", "hint", "typo", "style"}:
                return cls.TYPO
            if normalized == "info":
                return cls.WARNING
        return cls.ERROR


@dataclass
class Problem:
    """Single diagnostic to be shown in the Problems view.

    The widget requires exactly these five pieces of information; everything
    else is optional metadata that providers may attach without breaking the
    UI contract.

    Attributes:
        file_path: Absolute or workspace-relative path to the offending file.
        severity: ``ProblemSeverity`` controlling the icon and grouping.
        message: Human-readable explanation shown to the user.
        line: 1-based line number.
        column: 1-based column / offset (0 when unknown).
        source: Provider name (e.g. ``"python"``, ``"ruff"``, ``"pyright"``).
        code: Optional diagnostic code (e.g. ``"E001"``, ``"F821"``,
            ``"reportUndefinedVariable"``).
        end_line: 1-based last line of the diagnostic range. Defaults to
            ``line`` when a provider does not report an end position.
        end_column: 1-based last column of the diagnostic range. Defaults to
            ``column + 1`` (a single character) when unknown.
    """

    file_path: str
    severity: ProblemSeverity
    message: str
    line: int = 1
    column: int = 1
    source: str = ""
    code: Optional[str] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    def __post_init__(self) -> None:
        self.severity = ProblemSeverity.coerce(self.severity)
        # Clamp to sensible 1-based values; keep 0 as "unknown".
        try:
            self.line = int(self.line) if self.line is not None else 1
        except (TypeError, ValueError):
            self.line = 1
        try:
            self.column = int(self.column) if self.column is not None else 1
        except (TypeError, ValueError):
            self.column = 1
        if self.line < 1:
            self.line = 1
        if self.column < 0:
            self.column = 0
        if self.end_line is not None:
            try:
                self.end_line = int(self.end_line)
            except (TypeError, ValueError):
                self.end_line = None
            if self.end_line is not None and self.end_line < self.line:
                self.end_line = self.line
        if self.end_column is not None:
            try:
                self.end_column = int(self.end_column)
            except (TypeError, ValueError):
                self.end_column = None
            if self.end_column is not None and self.end_column < 0:
                self.end_column = 0
        self.file_path = str(self.file_path) if self.file_path else ""
        self.message = str(self.message) if self.message else ""
        self.source = str(self.source) if self.source else ""
        if self.code is not None:
            self.code = str(self.code)

    @property
    def is_error(self) -> bool:
        """Return ``True`` when this is an error-level diagnostic."""
        return self.severity == ProblemSeverity.ERROR

    @property
    def is_warning(self) -> bool:
        """Return ``True`` when this is a warning-level diagnostic."""
        return self.severity == ProblemSeverity.WARNING

    @property
    def is_typo(self) -> bool:
        """Return ``True`` when this is a typo / spell diagnostic."""
        return self.severity == ProblemSeverity.TYPO

    @property
    def is_info(self) -> bool:
        """Return ``True`` when this is an informational diagnostic."""
        return self.severity == ProblemSeverity.INFO

    @property
    def range_1based(self) -> tuple:
        """Return the ``(line, column, end_line, end_column)`` range.

        Missing end positions are normalized so downstream renderers always
        receive a usable, non-degenerate range.
        """
        end_line = self.end_line or self.line
        end_column = self.end_column
        if end_column is None or (end_line == self.line and end_column <= self.column):
            end_column = self.column + 1
        return self.line, self.column, end_line, end_column

    @property
    def range_0based(self) -> tuple:
        """Return the range with 0-based coordinates for editor painting."""
        line, column, end_line, end_column = self.range_1based
        return (
            max(0, line - 1),
            max(0, column - 1),
            max(0, end_line - 1),
            max(0, end_column - 1),
        )

    @property
    def range_length(self) -> int:
        """Return the number of characters covered by the range."""
        _line, _column, end_line, end_column = self.range_1based
        return max(1, end_column - _column)

    def to_dict(self) -> dict:
        """Serialise to a plain dict (useful for IPC / logging)."""
        return {
            "file_path": self.file_path,
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "source": self.source,
            "code": self.code,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Problem":
        """Create a ``Problem`` from a loose dict.

        Accepts both the new canonical keys (``file_path``, ``severity``,
        ``message``, ``line``, ``column``) and legacy walker keys
        (``error_msg``, ``error_line``, ``error_offset``).
        """
        if not isinstance(data, dict):
            raise TypeError(f"expected dict, got {type(data).__name__}")
        file_path = data.get("file_path") or data.get("file") or data.get("path") or ""
        severity = (
            data.get("severity") or data.get("type") or data.get("kind") or "error"
        )
        message = (
            data.get("message")
            or data.get("error_msg")
            or data.get("msg")
            or data.get("text")
            or ""
        )
        line = data.get("line", data.get("error_line", 1))
        column = data.get("column", data.get("col", data.get("error_offset", 1)))
        source = data.get("source", "")
        code = data.get("code")
        end_line = data.get("end_line", data.get("endLine"))
        end_column = data.get("end_column", data.get("endColumn"))
        return cls(
            file_path=str(file_path),
            severity=ProblemSeverity.coerce(severity),
            message=str(message),
            line=int(line) if line not in (None, "") else 1,
            column=int(column) if column not in (None, "") else 1,
            source=str(source) if source else "",
            code=str(code) if code is not None else None,
            end_line=int(end_line) if end_line not in (None, "") else None,
            end_column=int(end_column) if end_column not in (None, "") else None,
        )


@dataclass
class ProviderResult:
    """Outcome of one external provider run.

    Attributes:
        problems: Diagnostics produced by the provider (possibly empty).
        error: Failure description, or ``None`` on success. A non-empty
            ``error`` always means "no usable data", never "clean scan".
        note: Non-fatal information (for example "this build has no stdin
            mode"), which callers surface without failing the analysis.
    """

    problems: List[Problem] = field(default_factory=list)
    error: Optional[str] = None
    note: Optional[str] = None

    @property
    def ok(self) -> bool:
        """Return ``True`` when the provider produced usable data."""
        return self.error is None


class ProblemProvider(ABC):
    """Abstract plugin contract for any analysis backend.

    Implementations (Python walker, spell checker, linter, LSP client …)
    only need to return ``List[Problem]`` — the UI never imports them.
    """

    @abstractmethod
    def collect(self) -> List[Problem]:
        """Return all diagnostics for the provider's current scope."""
        raise NotImplementedError
