"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Pure DayDream build commands without Tk dependency for reuse and testing.
"""

import os
import shutil
import subprocess


def compile_file(
    full_path: str, language: str, timeout: float = 120.0
) -> tuple[bool, str]:
    """Compile *full_path* for *language*; returns (ok, output)."""
    if not full_path or not os.path.isfile(full_path):
        return False, "Not found"
    if language not in ("c", "cpp", "py", "java"):
        return False, "Unsupported language"
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
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Compile timed out after {timeout}s"
    except Exception as exc:
        return False, str(exc)


def copy_file(name: str, source: str, dest: str) -> str:
    """Copy file helper without UI dependency."""
    if not name or not source or not dest:
        raise ValueError("name, source and dest are required.")
    full = os.path.join(source, name)
    if not os.path.isfile(full):
        raise FileNotFoundError(f"Source file not found: {full}")
    os.makedirs(dest, exist_ok=True)
    shutil.copyfile(full, os.path.join(dest, name))
    return "Copied"


def move_file(name: str, source: str, dest: str) -> str:
    """Move file helper without UI dependency."""
    if not name or not source or not dest:
        raise ValueError("name, source and dest are required.")
    full = os.path.join(source, name)
    if not os.path.isfile(full) and not os.path.isdir(full):
        raise FileNotFoundError(f"Source not found: {full}")
    os.makedirs(dest, exist_ok=True)
    shutil.move(full, os.path.join(dest, name))
    return "Moved"
