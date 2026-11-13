"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Diagnostic backend protocol and router for the DreamStudio Problems panel.
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable
from pathlib import Path

from editor.analysis.types import Problem


@runtime_checkable
class DiagnosticBackend(Protocol):
    """Contract for language-specific diagnostic providers.

    Each language plugin implements this protocol and registers an
    instance with :class:`DiagnosticRouter`.  The Problems widget then
    routes files to the correct backend by extension.
    """

    def supported_extensions(self) -> tuple[str, ...]:
        """Return the file suffixes this backend can analyze (e.g. ``(".py",)``)."""
        ...

    def analyze_file(self, path: str, content: str, root: str | None) -> List[Problem]:
        """Analyze a file as it exists on disk."""
        ...

    def analyze_buffer(
        self, path: str, content: str, root: str | None
    ) -> List[Problem]:
        """Analyze an in-memory editor buffer."""
        ...

    def scan_workspace(self, root: str) -> List[Problem]:
        """Scan an entire workspace and return all problems found."""
        ...


class DiagnosticRouter:
    """Routes file paths to the correct :class:`DiagnosticBackend` by extension."""

    _backends: dict[str, "DiagnosticBackend"] = {}

    @classmethod
    def register(cls, backend: "DiagnosticBackend") -> None:
        """Register *backend* for all its supported extensions."""
        for ext in backend.supported_extensions():
            cls._backends[ext.lower()] = backend

    @classmethod
    def backend_for(cls, path: str) -> "DiagnosticBackend | None":
        """Return the backend that handles *path*, or ``None``."""
        return cls._backends.get(Path(path).suffix.lower())

    @classmethod
    def supported_suffixes(cls) -> tuple[str, ...]:
        """Return every extension handled by a registered backend."""
        return tuple(cls._backends.keys())

    @classmethod
    def analyze_file(
        cls, path: str, content: str, root: str | None = None
    ) -> List[Problem]:
        """Dispatch to the backend for *path*."""
        backend = cls.backend_for(path)
        if backend is None:
            return []
        return backend.analyze_file(path, content, root)

    @classmethod
    def analyze_buffer(
        cls, path: str, content: str, root: str | None = None
    ) -> List[Problem]:
        """Dispatch to the backend for *path* (buffer variant)."""
        backend = cls.backend_for(path)
        if backend is None:
            return []
        return backend.analyze_buffer(path, content, root)

    @classmethod
    def scan_workspace(cls, root: str) -> List[Problem]:
        """Run every registered backend's workspace scan."""
        problems: List[Problem] = []
        seen: set = set()
        for backend in set(cls._backends.values()):
            if id(backend) in seen:
                continue
            seen.add(id(backend))
            try:
                problems.extend(backend.scan_workspace(root))
            except Exception:
                continue
        return problems
