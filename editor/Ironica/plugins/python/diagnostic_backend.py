"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Python diagnostic backend — wraps the existing AST / Ruff / Pyright providers.
"""

from __future__ import annotations

from typing import List

from editor import *

from editor.analysis import providers
from editor.analysis.backend import DiagnosticBackend
from editor.analysis.types import Problem
from editor.Ironica.language_engine import LanguageRegistry


class PythonDiagnosticBackend:
    """Diagnostic backend for Python files."""

    def supported_extensions(self) -> tuple[str, ...]:
        try:
            config = LanguageRegistry.get_config("python") or {}
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
        return (".py",)

    def analyze_file(self, path: str, content: str, root: str | None) -> List[Problem]:
        outcome = providers.analyze_saved_file(path, content)
        return list(outcome.problems)

    def analyze_buffer(
        self, path: str, content: str, root: str | None
    ) -> List[Problem]:
        outcome = providers.analyze_buffer_fast(path, content, root)
        return list(outcome.problems)

    def analyze_buffer_semantic(
        self, path: str, content: str, root: str | None
    ) -> List[Problem]:
        outcome = providers.analyze_buffer_semantic(path, content, root)
        return list(outcome.problems)

    def scan_workspace(self, root: str) -> List[Problem]:
        outcome = providers.scan_workspace(root, use_ruff=True)
        return list(outcome.problems)


# Auto-register on import
from editor.analysis.router import DiagnosticRouter

DiagnosticRouter.register(PythonDiagnosticBackend())
