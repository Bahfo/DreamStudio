"""
Tests for the C++ diagnostic backend's workspace scanning.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from editor.Ironica.plugins.cpp.diagnostic_backend import CppDiagnosticBackend


@pytest.fixture(autouse=True)
def _clear_router():
    """Ensure a clean router state."""
    from editor.analysis.router import DiagnosticRouter

    saved = dict(DiagnosticRouter._backends)
    DiagnosticRouter._backends.clear()
    DiagnosticRouter.register(CppDiagnosticBackend())
    yield
    DiagnosticRouter._backends.clear()
    DiagnosticRouter._backends.update(saved)


def test_scan_workspace_excludes_venv(tmp_path: Path):
    """scan_workspace must not include files under venv/ or .venv/."""
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "venv" / "lib").mkdir(parents=True)
    (project / ".venv" / "lib").mkdir(parents=True)

    (project / "src" / "main.cpp").write_text("int main() { return 0; }\n")
    (project / "venv" / "lib" / "bad.cpp").write_text("int x = ;\n")
    (project / ".venv" / "lib" / "bad2.cpp").write_text("int y = ;\n")

    backend = CppDiagnosticBackend()
    problems = backend.scan_workspace(str(project))

    file_paths = {p.file_path for p in problems}
    assert not any("venv" in fp for fp in file_paths)
    assert not any(".venv" in fp for fp in file_paths)


def test_scan_workspace_excludes_node_modules(tmp_path: Path):
    """scan_workspace must not include files under node_modules/."""
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "node_modules" / "pkg").mkdir(parents=True)

    (project / "src" / "main.cpp").write_text("int main() { return 0; }\n")
    (project / "node_modules" / "pkg" / "bad.cpp").write_text("int x = ;\n")

    backend = CppDiagnosticBackend()
    problems = backend.scan_workspace(str(project))

    file_paths = {p.file_path for p in problems}
    assert not any("node_modules" in fp for fp in file_paths)


def test_scan_workspace_only_cpp_files(tmp_path: Path):
    """scan_workspace should only analyze C++ files."""
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)

    (project / "src" / "main.cpp").write_text("int main() { return 0; }\n")
    (project / "src" / "readme.md").write_text("# Hello\n")
    (project / "src" / "script.py").write_text("x = 1\n")

    backend = CppDiagnosticBackend()
    problems = backend.scan_workspace(str(project))

    file_paths = {p.file_path for p in problems}
    assert all(
        any(fp.endswith(ext) for ext in (".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hxx", ".hh"))
        for fp in file_paths
    )


def test_scan_workspace_respects_git_dir(tmp_path: Path):
    """scan_workspace must not include files under .git/."""
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / ".git" / "hooks").mkdir(parents=True)

    (project / "src" / "main.cpp").write_text("int main() { return 0; }\n")
    (project / ".git" / "hooks" / "bad.cpp").write_text("int x = ;\n")

    backend = CppDiagnosticBackend()
    problems = backend.scan_workspace(str(project))

    file_paths = {p.file_path for p in problems}
    assert not any(".git" in fp for fp in file_paths)


def test_scan_workspace_finds_compile_errors(tmp_path: Path):
    """scan_workspace should find C++ compilation errors."""
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)

    (project / "src" / "bad.cpp").write_text("int x = ;\n")

    backend = CppDiagnosticBackend()
    problems = backend.scan_workspace(str(project))

    assert len(problems) > 0
    assert any("expected" in p.message.lower() or "error" in p.message.lower() for p in problems)


def test_scan_workspace_empty_dir(tmp_path: Path):
    """scan_workspace on an empty directory returns no problems."""
    project = tmp_path / "empty"
    project.mkdir()

    backend = CppDiagnosticBackend()
    problems = backend.scan_workspace(str(project))

    assert problems == []
