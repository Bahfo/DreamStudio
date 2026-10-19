"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Provider composition and merge layer for the DreamStudio Problems scanner.
"""

from editor import *

import logging

from editor.analysis.types import Problem, ProblemSeverity
from editor.analysis.walker import ProblemsAnalyzer
from editor.analysis import pyright_provider, ruff_provider

logger = logging.getLogger(__name__)

AST_SOURCE = "python"

_EXTERNAL_SOURCES = (
    ruff_provider.RUFF_SOURCE,
    pyright_provider.BASEDPYRIGHT_SOURCE,
)


@dataclass
class AnalysisOutcome:
    """Merged result of a provider run plus provider-level health."""

    problems: List[Problem] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    groups: Dict[str, List[Problem]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Return ``True`` when no provider reported a failure."""
        return not self.errors


def _ast_problems(path: str, content: str) -> List[Problem]:
    """Run the built-in Python provider over an in-memory buffer."""
    from editor.analysis.walker import analyze_source

    return analyze_source(path, content)


def merge_problems(*groups: Iterable[Problem]) -> List[Problem]:
    """Merge provider outputs, dropping semantically duplicate diagnostics."""
    merged: List[Problem] = []
    index: dict = {}
    ast_syntax_files: set = set()
    ast_long_lines: set = set()

    for group in groups:
        for problem in group or []:
            path = problem.file_path
            try:
                line = int(problem.line or 1)
            except (TypeError, ValueError):
                line = 1
            if problem.source == AST_SOURCE:
                if ruff_provider.is_syntax_problem(problem):
                    ast_syntax_files.add(path)
                if ruff_provider.is_line_length_problem(problem):
                    ast_long_lines.add((path, line))

    for group in groups:
        for problem in group or []:
            path = problem.file_path
            try:
                line = int(problem.line or 1)
            except (TypeError, ValueError):
                line = 1
            key = _identity(problem)
            existing = index.get(key)
            if existing is not None:
                _keep_richer_range(existing, problem)
                continue
            if problem.source in _EXTERNAL_SOURCES:
                if (
                    ruff_provider.is_syntax_problem(problem)
                    and path in ast_syntax_files
                ):
                    continue
                if (
                    ruff_provider.is_line_length_problem(problem)
                    and (
                        path,
                        line,
                    )
                    in ast_long_lines
                ):
                    continue
            index[key] = problem
            merged.append(problem)
    return merged


def _identity(problem: Problem) -> tuple:
    """Return the structured identity used for de-duplication."""
    return (
        problem.file_path,
        int(problem.line or 1),
        int(problem.column or 0),
        problem.code or "",
        problem.severity.value,
        problem.message,
    )


def _keep_richer_range(kept: Problem, candidate: Problem) -> None:
    """Upgrade *kept* with an explicit range when *candidate* has one."""
    kept_end = kept.end_column or 0
    candidate_end = candidate.end_column or 0
    kept_is_vague = kept.end_line is None or kept_end <= kept.column
    candidate_is_precise = (
        candidate.end_line is not None and candidate_end > candidate.column
    )
    if kept_is_vague and candidate_is_precise:
        kept.end_line = candidate.end_line
        kept.end_column = candidate.end_column


def merge_by_path(*groups: Iterable[Problem]) -> Dict[str, List[Problem]]:
    """Merge diagnostics from several providers, keyed by file path."""
    by_path: Dict[str, List[Problem]] = {}
    for group in groups:
        for problem in group or []:
            by_path.setdefault(problem.file_path, []).append(problem)
    return {path: merge_problems(problems) for path, problems in by_path.items()}


def analyze_saved_file(path: str, content: str) -> AnalysisOutcome:
    """Analyze a file as it exists on disk (workspace scope)."""
    errors: List[str] = []
    problems: List[Problem] = []
    try:
        problems = _ast_problems(path, content)
    except Exception as exc:
        errors.append(f"{AST_SOURCE} provider failed for {path}: {exc}")
        logger.warning("AST provider failed for %s: %s", path, exc)
    return AnalysisOutcome(problems, errors)


def analyze_buffer_fast(
    path: str, content: str, root: Optional[str] = None
) -> AnalysisOutcome:
    """Fast active-buffer pass:"""
    return analyze_buffer(path, content, root, include_semantic=False)


def analyze_buffer_semantic(
    path: str, content: str, root: Optional[str] = None
) -> AnalysisOutcome:
    """Semantic active-buffer pass, run after the fast pass has settled."""
    errors: List[str] = []
    notes: List[str] = []
    workspace = root or os.path.dirname(path) or os.getcwd()
    problems = _run_buffer_provider(
        lambda: pyright_provider.BasedPyrightProvider(workspace).analyze_source(
            path, content
        ),
        "pyright",
        errors,
        notes,
    )
    return AnalysisOutcome(problems, errors, notes)


def analyze_buffer(
    path: str,
    content: str,
    root: Optional[str] = None,
    use_ruff: bool = True,
    include_semantic: bool = True,
) -> AnalysisOutcome:
    """Analyze an in-memory editor buffer with every applicable provider."""
    errors: List[str] = []
    notes: List[str] = []
    ast: List[Problem] = []
    try:
        ast = _ast_problems(path, content)
    except Exception as exc:
        errors.append(f"{AST_SOURCE} provider failed for {path}: {exc}")
        logger.warning("AST provider failed for %s: %s", path, exc)

    groups: List[List[Problem]] = [ast]
    workspace = root or os.path.dirname(path) or os.getcwd()

    if use_ruff:
        groups.append(
            _run_buffer_provider(
                lambda: ruff_provider.RuffProvider(workspace).analyze_source(
                    path, content
                ),
                "ruff",
                errors,
                notes,
            )
        )

    if include_semantic:
        semantic = _run_buffer_provider(
            lambda: pyright_provider.BasedPyrightProvider(workspace).analyze_source(
                path, content
            ),
            "pyright",
            errors,
            notes,
        )
        if semantic:
            groups.append(semantic)

    return AnalysisOutcome(merge_problems(*groups), errors, notes)


def _run_buffer_provider(
    factory,
    label: str,
    errors: List[str],
    notes: List[str],
    groups: Optional[dict] = None,
) -> List[Problem]:
    """Run one provider without letting it break the others."""
    try:
        result = factory()
    except Exception as exc:
        errors.append(f"{label}: {exc}")
        logger.warning("%s provider failed: %s", label, exc)
        return []
    if not result.ok:
        errors.append(f"{label}: {result.error}")
        return []
    if result.note:
        note = f"{label}: {result.note}"
        if note not in notes:
            notes.append(note)
    problems = list(result.problems)
    if groups is not None:
        groups[label] = problems
    return problems


def analyze_source(
    path: str, content: str, root: Optional[str] = None, use_ruff: bool = True
) -> AnalysisOutcome:
    """Backward-compatible alias for :func:`analyze_buffer`."""
    return analyze_buffer(path, content, root, use_ruff)


def scan_external_workspace(root: str) -> AnalysisOutcome:
    """Run only the external (Ruff) provider over a workspace."""
    errors: List[str] = []
    notes: List[str] = []
    groups: Dict[str, List[Problem]] = {}
    _run_buffer_provider(
        lambda: ruff_provider.RuffProvider(root).scan_workspace(),
        ruff_provider.RUFF_SOURCE,
        errors,
        notes,
        groups,
    )
    _run_buffer_provider(
        lambda: pyright_provider.BasedPyrightProvider(root).scan_workspace(),
        pyright_provider.BASEDPYRIGHT_SOURCE,
        errors,
        notes,
        groups,
    )

    problems = [problem for items in groups.values() for problem in items]
    return AnalysisOutcome(problems, errors, notes, groups)


def scan_workspace(root: str, use_ruff: bool = True) -> AnalysisOutcome:
    """Scan a whole workspace with every available provider."""
    errors: List[str] = []
    notes: List[str] = []
    ast_by_path: Dict[str, List[Problem]] = {}
    try:
        analyzer = ProblemsAnalyzer(root)
        for problem in analyzer.collect():
            ast_by_path.setdefault(problem.file_path, []).append(problem)
        if analyzer.skipped_files:
            logger.debug("Workspace scan skipped %s file(s)", analyzer.skipped_files)
    except Exception as exc:
        errors.append(f"{AST_SOURCE} provider failed for {root}: {exc}")
        logger.warning("AST workspace provider failed for %s: %s", root, exc)

    external_by_path: Dict[str, List[Problem]] = {}
    if use_ruff:
        for problem in _run_buffer_provider(
            lambda: ruff_provider.RuffProvider(root).scan_workspace(),
            "ruff",
            errors,
            notes,
        ):
            external_by_path.setdefault(problem.file_path, []).append(problem)

    semantic = _run_buffer_provider(
        lambda: pyright_provider.BasedPyrightProvider(root).scan_workspace(),
        "pyright",
        errors,
        notes,
    )
    for problem in semantic:
        external_by_path.setdefault(problem.file_path, []).append(problem)

    merged = merge_by_path(
        [problem for problems in ast_by_path.values() for problem in problems],
        [problem for problems in external_by_path.values() for problem in problems],
    )
    return AnalysisOutcome(
        [problem for problems in merged.values() for problem in problems],
        errors,
        notes,
    )


CATEGORY_SYNTAX = "syntax"
CATEGORY_CHECK = "check"
CATEGORY_UNUSED = "unused"
CATEGORY_NAME = "name"
CATEGORY_TYPE = "type"
CATEGORY_STYLE = "style"
CATEGORY_MARKER = "marker"
CATEGORY_OTHER = "other"

_UNUSED_CODES = frozenset({"F401", "F811", "F841", "F401 ", "ARG001", "ARG002"})
_UNUSED_RULES = ("reportUnused", "unused")
_NAME_CODES = frozenset({"F405", "F821", "F822", "F823", "F831"})
_NAME_RULES = ("reportUndefined", "reportUnbound", "reportUnresolved", "reportMissing")
_TYPE_RULES = (
    "reportArgumentType",
    "reportAssignmentType",
    "reportAttributeAccess",
    "reportCallIssue",
    "reportOperatorIssue",
    "reportIndexIssue",
    "reportReturnType",
    "reportOptionalMember",
    "reportGeneralTypeIssues",
    "reportInvalidTypeForm",
)
_STYLE_CODES = frozenset({"E", "W", "I", "C4", "N", "UP", "SIM", "B", "A", "S", "T20"})
_STYLE_RULES = ("Line too long", "marker found")


def diagnostic_category(problem: Problem) -> str:
    """Classify *problem* into a presentation category."""
    code = (problem.code or "").strip()
    upper = code.upper()
    message = problem.message or ""

    if ruff_provider.is_syntax_problem(problem):
        return CATEGORY_SYNTAX
    if problem.severity == ProblemSeverity.CHECK:
        return CATEGORY_CHECK
    if "marker found" in message:
        return CATEGORY_MARKER
    if upper in _UNUSED_CODES or any(rule in code for rule in _UNUSED_RULES):
        return CATEGORY_UNUSED
    if upper in _NAME_CODES or any(rule in code for rule in _NAME_RULES):
        return CATEGORY_NAME
    if any(rule in code for rule in _TYPE_RULES):
        return CATEGORY_TYPE
    if not code:
        return CATEGORY_STYLE
    if any(message.startswith(text) or text in message for text in _STYLE_RULES):
        return CATEGORY_STYLE
    if upper.startswith(tuple(sorted(_STYLE_CODES))):
        return CATEGORY_STYLE
    return CATEGORY_OTHER


def is_deemphasized(problem: Problem) -> bool:
    """Return ``True`` when *problem* should be rendered dimmed, not flagged."""
    return diagnostic_category(problem) == CATEGORY_UNUSED
