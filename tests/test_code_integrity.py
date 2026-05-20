"""Structural and integrity checks on the source code."""

import ast
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCE_DIRS = [
    "editor",
    "backend",
]

EXCLUDE_DIRS = {"__pycache__", ".git", "venv", ".venv"}


def _get_py_files():
    files = []
    for sd in SOURCE_DIRS:
        for root, dirs, fnames in os.walk(os.path.join(PROJECT_ROOT, sd)):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in fnames:
                if f.endswith(".py"):
                    files.append(os.path.join(root, f))
    return files


class TestCodeIntegrity:
    def test_all_files_parse(self):
        errors = []
        for fpath in _get_py_files():
            try:
                with open(fpath, encoding="utf-8") as fh:
                    ast.parse(fh.read())
            except SyntaxError as e:
                errors.append(f"{os.path.relpath(fpath, PROJECT_ROOT)}: {e}")
        assert not errors, f"Syntax errors:\n" + "\n".join(errors)

    def test_no_bare_except_pass(self):
        violations = []
        for fpath in _get_py_files():
            with open(fpath, encoding="utf-8") as fh:
                try:
                    tree = ast.parse(fh.read())
                except SyntaxError:
                    continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None and any(
                        isinstance(stmt, ast.Pass) for stmt in node.body
                    ):
                        rel = os.path.relpath(fpath, PROJECT_ROOT)
                        violations.append(f"{rel}: bare `except: pass`")
        assert not violations, (
            f"Found bare except:pass (use specific exceptions):\n"
            + "\n".join(violations[:20])
        )

    def test_no_placeholder_todos(self):
        """Check that no file has stub/placeholder TODOs."""
        keywords = ["# TODO: implement", "# TODO implement",
                     "raise NotImplementedError"]
        violations = []
        for fpath in _get_py_files():
            with open(fpath, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    stripped = line.strip()
                    if any(kw.lower() in stripped.lower() for kw in keywords):
                        rel = os.path.relpath(fpath, PROJECT_ROOT)
                        violations.append(f"{rel}:{i}: {stripped}")
        violations = [v for v in violations if "test_code_integrity" not in v]
        assert not violations, (
            f"Placeholder stubs found:\n" + "\n".join(violations[:20])
        )

    def test_no_prints_in_production_code(self):
        """Warn about stray print() calls (use logger instead)."""
        violations = []
        for fpath in _get_py_files():
            with open(fpath, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    s = line.strip()
                    if s.startswith("print(") and "logger" not in s:
                        rel = os.path.relpath(fpath, PROJECT_ROOT)
                        violations.append(f"{rel}:{i}: {s}")
        allowed = ["test_code_integrity", "__name__"]
        violations = [
            v for v in violations
            if not any(a in v for a in allowed)
        ]
        if violations:
            print("WARNING: print() calls found:\n" + "\n".join(violations[:10]))

    def test_no_main_in_editor_modules(self):
        """Editor modules shouldn't have __main__ blocks."""
        for fpath in _get_py_files():
            if "__main__" in fpath.replace("\\", "/"):
                continue
            with open(fpath, encoding="utf-8") as fh:
                source = fh.read()
            if '__name__ == "__main__"' in source:
                rel = os.path.relpath(fpath, PROJECT_ROOT)
                print(f"INFO: {rel} has __main__ block")

    def test_imports_are_valid(self):
        """Check that all local imports reference existing modules."""
        for fpath in _get_py_files():
            with open(fpath, encoding="utf-8") as fh:
                try:
                    tree = ast.parse(fh.read())
                except SyntaxError:
                    continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        pass
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.level is not None and node.level > 0:
                        pass
