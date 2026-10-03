"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Resolve the Python interpreter belonging to the active workspace (cwd)
instead of the IDE's own interpreter, with a global-Python fallback.
"""

import os
import shutil
import sys

VENV_DIR_NAMES = ("venv", ".venv")
GLOBAL_CANDIDATES = ("python3", "python")


def find_venv_python(workspace_dir: str | None) -> str | None:
    """Return the workspace venv interpreter when one exists.

    Args:
        workspace_dir: Absolute path of the active project/cwd. May be
            None or empty, in which case no venv is reported.

    Returns:
        Absolute path to the venv Python executable, or None when no
        workspace venv was found.
    """
    if not workspace_dir:
        return None
    base = os.path.abspath(workspace_dir)
    if not os.path.isdir(base):
        return None
    for venv_name in VENV_DIR_NAMES:
        venv_root = os.path.join(base, venv_name)
        if not os.path.isdir(venv_root):
            continue
        if os.name == "nt":
            candidate = os.path.join(venv_root, "Scripts", "python.exe")
            if os.path.isfile(candidate):
                return candidate
        else:
            for exe_name in ("python", "python3"):
                candidate = os.path.join(venv_root, "bin", exe_name)
                if os.path.isfile(candidate):
                    return candidate
    return None


def find_global_python() -> str:
    """Return a system-wide Python interpreter, never the IDE venv.

    Returns:
        Path or command name of a global Python interpreter. Falls back
        to the base-prefix interpreter and finally ``sys.executable``.
    """
    base_exe = getattr(sys, "_base_executable", None)
    if base_exe and os.path.isfile(str(base_exe)):
        if os.path.abspath(str(base_exe)) != os.path.abspath(sys.executable):
            return str(base_exe)
    for command in GLOBAL_CANDIDATES:
        resolved = shutil.which(command)
        if resolved and os.path.abspath(resolved) != os.path.abspath(sys.executable):
            return resolved
    for command in GLOBAL_CANDIDATES:
        resolved = shutil.which(command)
        if resolved:
            return resolved
    base_prefix = getattr(sys, "base_prefix", "") or ""
    if base_prefix:
        suffix = os.path.join("bin", "python3")
        candidate = os.path.join(base_prefix, suffix)
        if os.path.isfile(candidate):
            return candidate
    return sys.executable


def resolve_project_python(workspace_dir: str | None = None) -> str:
    """Resolve the interpreter for ``Run Current File``.

    Args:
        workspace_dir: Active project/cwd root. When None, the current
            process working directory is used.

    Returns:
        Workspace venv Python when present, otherwise a global Python.
    """
    base = workspace_dir or os.getcwd()
    venv_python = find_venv_python(base)
    if venv_python:
        return venv_python
    return find_global_python()


def resolve_workspace_dir(window=None) -> str:
    """Return the active workspace root without touching IDE resources.

    Args:
        window: Main IDE window (uses ``currentDirectory`` when set).

    Returns:
        Absolute path of the active project/cwd.
    """
    candidate = getattr(window, "currentDirectory", "") if window is not None else ""
    if candidate and os.path.isdir(str(candidate)):
        return os.path.abspath(str(candidate))
    return os.path.abspath(os.getcwd())
