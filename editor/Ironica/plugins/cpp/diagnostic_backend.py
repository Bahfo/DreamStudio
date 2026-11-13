"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

C++ diagnostic backend — uses libclang to produce Problems.
"""

from __future__ import annotations

from typing import List

from editor import *

from editor.analysis.backend import DiagnosticBackend
from editor.analysis.types import Problem, ProblemSeverity
from editor.Ironica.language_engine import LanguageRegistry
from editor.Ironica.plugins.cpp.intellisense import args as cpp_args

_CLANG_SEVERITY_MAP = {
    0: None,  # Ignored — skip
    1: ProblemSeverity.INFO,  # Note
    2: ProblemSeverity.WARNING,  # Warning
    3: ProblemSeverity.ERROR,  # Error
    4: ProblemSeverity.ERROR,  # Fatal
}


class CppDiagnosticBackend:
    """Diagnostic backend for C/C++ files."""

    def supported_extensions(self) -> tuple[str, ...]:
        try:
            config = LanguageRegistry.get_config("cpp") or {}
            extensions = config.get("extensions", [])
            if extensions:
                return tuple(
                    sorted(
                        {
                            f".{str(ext).lstrip('.').lower()}"
                            for ext in extensions
                            if str(ext)
                        }
                    )
                )
        except Exception:
            pass
        return (".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hxx", ".hh")

    def _analyze(self, path: str, content: str) -> List[Problem]:
        problems: List[Problem] = []
        try:
            from clang.cindex import Index, TranslationUnit
            import re

            a = cpp_args.args_for_file(path, content)
            tu = Index.create().parse(
                path, args=a, options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
            )

            # Resolve missing headers (mirrors NavigationEngine._active_translation_unit)
            missing = set()
            for diag in getattr(tu, "diagnostics", []) or []:
                spelling = getattr(diag, "spelling", "") or ""
                m = re.search(r"'([^']+)' file not found", spelling)
                if m:
                    missing.add(m.group(1))

            if missing:
                try:
                    from editor.Ironica.plugins.cpp.intellisense import (
                        headers as header_resolution,
                    )

                    if header_resolution.resolve_missing(list(missing), path, list(a)):
                        a = cpp_args.args_for_file(path, content)
                        tu = Index.create().parse(
                            path,
                            args=a,
                            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
                        )
                except Exception:
                    pass

            for diag in tu.diagnostics:
                sev = int(getattr(diag, "severity", 0))
                problem_severity = _CLANG_SEVERITY_MAP.get(sev)
                if problem_severity is None:
                    continue
                location = getattr(diag, "location", None)
                line = int(getattr(location, "line", 1) or 1) if location else 1
                col = int(getattr(location, "column", 1) or 1) if location else 1
                spelling = getattr(diag, "spelling", "") or ""
                if not spelling:
                    continue
                # Compute the token length at the error location for proper underlining
                end_col = col
                try:
                    for tok in tu.get_tokens(extent=tu.cursor.extent):
                        if (
                            tok.location.line == line
                            and tok.location.column
                            <= col
                            < tok.location.column + len(tok.spelling)
                        ):
                            end_col = tok.location.column + len(tok.spelling)
                            break
                except Exception:
                    pass
                if end_col <= col:
                    end_col = col + 1
                problems.append(
                    Problem(
                        file_path=path,
                        line=line,
                        column=col,
                        end_line=line,
                        end_column=end_col,
                        severity=problem_severity,
                        message=spelling,
                        code="",
                        source="clang",
                    )
                )
        except Exception:
            pass
        return problems

    def analyze_file(self, path: str, content: str, root: str | None) -> List[Problem]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            pass
        return self._analyze(path, content)

    def analyze_buffer(
        self, path: str, content: str, root: str | None
    ) -> List[Problem]:
        return self._analyze(path, content)

    def scan_workspace(self, root: str) -> List[Problem]:
        problems: List[Problem] = []
        try:
            from editor.Ironica.plugins.cpp.navigation.engine import NavigationEngine

            # Use the same project-file discovery as the navigation engine,
            # which respects .git, .ds, venv, node_modules, etc.
            source_path = root
            project_files = NavigationEngine._find_project_files(source_path)
            for file_path in project_files:
                try:
                    content = open(
                        file_path, "r", encoding="utf-8", errors="replace"
                    ).read()
                    problems.extend(self._analyze(file_path, content))
                except Exception:
                    continue
        except Exception:
            pass
        return problems


from editor.analysis.router import DiagnosticRouter

DiagnosticRouter.register(CppDiagnosticBackend())
