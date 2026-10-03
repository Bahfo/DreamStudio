"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Resolve the Python interpreter belonging to the active workspace (cwd)
instead of the IDE's own interpreter, with a global-Python fallback.
"""

import logging
import os
import shutil
import sys

logger = logging.getLogger(__name__)

VENV_DIR_NAMES = ("venv", ".venv", "env", ".env")
GLOBAL_CANDIDATES = ("python3", "python")


def find_venv_python(workspace_dir: str | None) -> str | None:
    """Return the workspace venv interpreter when one exists.

    Args:
        workspace_dir: Absolute path of the active project/cwd. May be
            None or empty, in which case ``VIRTUAL_ENV`` is honoured.

    Returns:
        Absolute path to the venv Python executable, or None when no
        workspace venv was found.
    """
    candidates: list[str] = []
    if workspace_dir and os.path.isdir(os.path.abspath(workspace_dir)):
        base = os.path.abspath(workspace_dir)
        for venv_name in VENV_DIR_NAMES:
            venv_root = os.path.join(base, venv_name)
            if not os.path.isdir(venv_root):
                continue
            if os.name == "nt":
                candidates.append(os.path.join(venv_root, "Scripts", "python.exe"))
            else:
                candidates.extend(
                    [
                        os.path.join(venv_root, "bin", "python"),
                        os.path.join(venv_root, "bin", "python3"),
                    ]
                )
    venv_env = os.environ.get("VIRTUAL_ENV", "")
    if venv_env and os.path.isdir(venv_env):
        if os.name == "nt":
            candidates.append(os.path.join(venv_env, "Scripts", "python.exe"))
        else:
            candidates.extend(
                [
                    os.path.join(venv_env, "bin", "python"),
                    os.path.join(venv_env, "bin", "python3"),
                ]
            )
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def find_global_python() -> str:
    """Return a system-wide Python interpreter, never the IDE venv silently.

    Returns:
        Path or command name of a global Python interpreter.

    Raises:
        RuntimeError: When no external interpreter can be located.
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
            logger.warning("Only IDE interpreter found on PATH: %s", resolved)
            return resolved
    base_prefix = getattr(sys, "base_prefix", "") or ""
    if base_prefix:
        if os.name == "nt":
            candidate = os.path.join(base_prefix, "python.exe")
        else:
            candidate = os.path.join(base_prefix, "bin", "python3")
        if os.path.isfile(candidate):
            if os.path.abspath(candidate) != os.path.abspath(sys.executable):
                return candidate
    raise RuntimeError("No system Python interpreter found outside the IDE venv.")


def resolve_project_python(workspace_dir: str | None = None) -> str:
    """Resolve the interpreter for ``Run Current File``.

    Args:
        workspace_dir: Active project/cwd root. When None or empty, only
            ``VIRTUAL_ENV`` and global interpreters are considered; the
            process CWD is never used as a workspace.

    Returns:
        Workspace venv Python when present, otherwise a global Python.
    """
    base = workspace_dir if workspace_dir else None
    venv_python = find_venv_python(base)
    if venv_python:
        return venv_python
    return find_global_python()


def resolve_workspace_dir(window=None) -> str:
    """Return the active workspace root without touching IDE resources.

    Args:
        window: Main IDE window (uses ``currentDirectory`` when set).

    Returns:
        Absolute path of the active workspace, or ``""`` when no
        workspace is open. Never falls back to process CWD.
    """
    from editor.utils.workspace import get_workspace_dir

    return get_workspace_dir(window)
