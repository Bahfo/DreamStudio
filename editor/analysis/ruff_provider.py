"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Ruff diagnostics provider for the DreamStudio Problems scanner.
"""

from editor import *

import json
import logging
import shutil
import subprocess

from editor.analysis.types import (
    Problem,
    ProblemProvider,
    ProblemSeverity,
    ProviderResult,
)

logger = logging.getLogger(__name__)

RUFF_PATH_ENV = "DREAMSTUDIO_RUFF"

RUFF_SOURCE = "ruff"

WORKSPACE_TIMEOUT_SECONDS = 120

STDIN_TIMEOUT_SECONDS = 15

_SUCCESS_CODES = (0, 1)

_ERROR_PREFIXES = ("E9", "F")

_WARNING_PREFIXES = ("E", "W")

_CHECK_CODES = frozenset(
    {
        "E722",
        "E731",
        "E741",
        "BLE001",
        "S110",
        "S112",
        "TRY002",
        "TRY300",
        "TRY301",
        "TRY400",
    }
)

_CHECK_MESSAGE_MARKERS = (
    "bare `except`",
    "bare except",
    "blind except",
    "blind `except`",
)

_LINE_LENGTH_CODES = ("E501",)

_SYNTAX_CODES = ("E999", "INVALID-SYNTAX")

_SYNTAX_MESSAGE_MARKERS = ("syntaxerror", "invalid syntax", "expected ", "unterminated")

#: Non-fatal note emitted when the optional Ruff tool is not installed.
_RUFF_MISSING = "not installed (ruff executable not found)"
_RUFF_TIMEOUT = "ruff timed out"
_RUFF_BAD_OUTPUT = "ruff returned invalid JSON output"


def ruff_command(executable: Optional[list] = None) -> Optional[list]:
    """Return the Ruff argv prefix to use, or ``None`` when unavailable."""
    if executable:
        return list(executable)

    override = os.environ.get(RUFF_PATH_ENV, "").strip()
    if override:
        resolved = shutil.which(override) or override
        if resolved and (os.path.isfile(resolved) or shutil.which(override)):
            return [resolved]

    on_path = shutil.which("ruff")
    if on_path:
        return [on_path]

    try:
        import importlib.util

        if importlib.util.find_spec("ruff") is not None:
            return [sys.executable, "-m", "ruff"]
    except Exception:
        pass
    return None


def find_ruff(root: Optional[str] = None) -> Optional[list]:
    """Discover the Ruff argv prefix for *root*."""
    if root:
        for relative in (
            os.path.join(".venv", "bin", "ruff"),
            os.path.join("venv", "bin", "ruff"),
            os.path.join(".venv", "Scripts", "ruff.exe"),
            os.path.join("venv", "Scripts", "ruff.exe"),
        ):
            candidate = os.path.join(root, relative)
            if os.path.isfile(candidate):
                return [candidate]
    return ruff_command()


def is_syntax_problem(problem: Problem) -> bool:
    """Return ``True`` when *problem* reports a parse failure."""
    if problem.source != RUFF_SOURCE:
        code = (problem.code or "").upper()
        if code in _SYNTAX_CODES:
            return True
        if code:
            return False
        return problem.severity == ProblemSeverity.ERROR
    code = (problem.code or "").upper()
    if code:
        return code in _SYNTAX_CODES
    message = (problem.message or "").lower()
    return any(marker in message for marker in _SYNTAX_MESSAGE_MARKERS)


def is_line_length_problem(problem: Problem) -> bool:
    """Return ``True`` when *problem* is a line-length diagnostic."""
    code = (problem.code or "").upper()
    if code:
        return code in _LINE_LENGTH_CODES
    return "line too long" in (problem.message or "").lower()


def map_severity(code: Optional[str], message: str) -> ProblemSeverity:
    """Map a Ruff rule code to the IDE severity system."""
    normalized = (code or "").strip().upper()
    lowered = (message or "").lower()
    says_check = any(marker in lowered for marker in _CHECK_MESSAGE_MARKERS)
    if normalized in _SYNTAX_CODES:
        return ProblemSeverity.ERROR
    if normalized in _CHECK_CODES:
        return ProblemSeverity.CHECK
    if not normalized:
        return ProblemSeverity.CHECK if says_check else ProblemSeverity.ERROR
    if any(normalized.startswith(prefix) for prefix in _ERROR_PREFIXES):
        return ProblemSeverity.ERROR
    if any(normalized.startswith(prefix) for prefix in _WARNING_PREFIXES):
        return ProblemSeverity.WARNING
    if "syntaxerror" in lowered or any(
        marker in lowered for marker in _SYNTAX_MESSAGE_MARKERS
    ):
        return ProblemSeverity.ERROR
    if says_check:
        return ProblemSeverity.CHECK
    return ProblemSeverity.TYPO


class RuffProvider(ProblemProvider):
    """Read-only ``ruff check`` provider emitting isolated problems."""

    def __init__(self, root: str, executable: Optional[list] = None) -> None:
        self.root = os.path.abspath(root or "") or os.getcwd()
        self.executable = executable
        self.last_error: Optional[str] = None
        self.last_note: Optional[str] = None


    def collect(self) -> List[Problem]:
        """Scan the whole workspace with Ruff."""
        return self.scan_workspace().problems

    def scan_workspace(self) -> ProviderResult:
        """Run Ruff over the workspace and normalize its JSON output."""
        command = self.executable or find_ruff(self.root)
        if not command:
            self.last_error = None
            self.last_note = _RUFF_MISSING
            logger.info("Ruff not installed; workspace scan limited to %s", self.root)
            return ProviderResult([], None, _RUFF_MISSING)
        self.last_note = None
        argv = [
            *command,
            "check",
            "--no-cache",
            "--output-format",
            "json",
            ".",
        ]
        return self._run(argv, stdin_text=None)

    def analyze_source(self, path: str, content: str) -> ProviderResult:
        """Analyze an unsaved buffer through Ruff's stdin mode."""
        command = self.executable or find_ruff(self.root)
        if not command:
            self.last_error = None
            self.last_note = _RUFF_MISSING
            return ProviderResult([], None, _RUFF_MISSING)
        self.last_note = None
        argv = [
            *command,
            "check",
            "--no-cache",
            "--output-format",
            "json",
            "--stdin-filename",
            path,
            "-",
        ]
        return self._run(argv, stdin_text=content)


    def _run(self, argv: List[str], stdin_text: Optional[str]) -> ProviderResult:
        """Execute Ruff read-only and normalize the result."""
        timeout = (
            STDIN_TIMEOUT_SECONDS
            if stdin_text is not None
            else WORKSPACE_TIMEOUT_SECONDS
        )
        try:
            completed = subprocess.run(
                argv,
                cwd=self.root,
                input=stdin_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.last_error = f"{_RUFF_TIMEOUT} after {timeout}s"
            logger.warning("Ruff timed out (%s): %s", self.root, timeout)
            return ProviderResult([], self.last_error)
        except (OSError, ValueError) as exc:
            self.last_error = f"ruff failed to run: {exc}"
            logger.warning("Ruff execution failed for %s: %s", self.root, exc)
            return ProviderResult([], self.last_error)

        if completed.returncode not in _SUCCESS_CODES:
            detail = (completed.stderr or "").strip().splitlines()
            message = detail[-1] if detail else f"exit code {completed.returncode}"
            self.last_error = f"ruff failed (exit {completed.returncode}): {message}"
            logger.warning("Ruff run failed for %s: %s", self.root, self.last_error)
            return ProviderResult([], self.last_error)

        try:
            payload = json.loads(completed.stdout or "[]")
        except (ValueError, TypeError) as exc:
            self.last_error = f"{_RUFF_BAD_OUTPUT}: {exc}"
            logger.warning("Ruff output not JSON for %s: %s", self.root, exc)
            return ProviderResult([], self.last_error)

        if not isinstance(payload, list):
            self.last_error = f"{_RUFF_BAD_OUTPUT}: expected a JSON list"
            logger.warning("Ruff payload is not a list for %s", self.root)
            return ProviderResult([], self.last_error)

        problems = self.normalize(payload)
        self.last_error = None
        return ProviderResult(problems)

    def normalize(self, payload: List[dict]) -> List[Problem]:
        """Convert Ruff JSON diagnostics into :class:`Problem` items."""
        problems: List[Problem] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            filename = str(item.get("filename") or "")
            if not filename:
                continue
            location = item.get("location") or {}
            if not isinstance(location, dict):
                location = {}
            end_location = item.get("end_location") or {}
            if not isinstance(end_location, dict):
                end_location = {}
            try:
                line = max(1, int(location.get("row") or 1))
            except (TypeError, ValueError):
                line = 1
            try:
                column = max(0, int(location.get("column") or 1))
            except (TypeError, ValueError):
                column = 1
            try:
                end_line = max(1, int(end_location.get("row") or line))
            except (TypeError, ValueError):
                end_line = line
            try:
                end_column = max(0, int(end_location.get("column") or column + 1))
            except (TypeError, ValueError):
                end_column = column + 1
            message = str(item.get("message") or "Ruff diagnostic")
            code = item.get("code")
            problems.append(
                Problem(
                    file_path=os.path.abspath(
                        filename
                        if os.path.isabs(filename)
                        else os.path.join(self.root, filename)
                    ),
                    severity=map_severity(code, message),
                    message=message,
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    source=RUFF_SOURCE,
                    code=str(code) if code else None,
                )
            )
        return problems
