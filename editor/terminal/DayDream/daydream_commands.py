"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Pure DayDream build commands without Tk dependency for reuse and testing.
"""

import os
import shutil
import subprocess


def compile_file(full_path: str, language: str) -> tuple[bool, str]:
    """Compile *full_path* for *language*; returns (ok, output)."""
    if not os.path.exists(full_path):
        return False, "Not found"
    try:
        from editor.debugger.run.python_resolver import resolve_project_python

        py_exe = resolve_project_python(os.path.dirname(full_path))
    except Exception:
        py_exe = "python3"
    compilers = {
        "c": ["gcc", full_path, "-o", full_path[:-2]],
        "cpp": ["g++", full_path, "-o", full_path[:-4]],
        "py": [py_exe, "-m", "py_compile", full_path],
        "java": ["javac", full_path],
    }
    if language not in compilers:
        return False, "Unsupported language"
    try:
        result = subprocess.run(
            compilers[language],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(full_path) or None,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as exc:
        return False, str(exc)


def copy_file(name: str, source: str, dest: str) -> str:
    """Copy file helper without UI dependency."""
    full = os.path.join(source, name)
    shutil.copyfile(full, os.path.join(dest, name))
    return "Copied"


def move_file(name: str, source: str, dest: str) -> str:
    """Move file helper without UI dependency."""
    full = os.path.join(source, name)
    shutil.move(full, os.path.join(dest, name))
    return "Moved"
