"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared subprocess helpers with consistent cwd, timeout and logging.
"""

import logging
import os
import subprocess
from typing import Mapping

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


def run_capture(
    argv: list[str],
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess:
    """Run *argv* and capture output with uniform error mapping.

    Args:
        argv: Argument sequence, must be non-empty.
        cwd: Working directory, may be None for inherit.
        env: Optional environment override.
        timeout: Seconds before ``TimeoutExpired``.

    Returns:
        Completed process instance.

    Raises:
        FileNotFoundError: When executable is missing.
        RuntimeError: For spawn or timeout failures.
    """
    if not argv:
        raise ValueError("argv must be non-empty.")
    if cwd is not None and not os.path.isdir(cwd):
        raise ValueError(f"Working directory does not exist: {cwd}")
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Executable not found: {argv[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out: {' '.join(argv)}") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to launch {' '.join(argv)}: {exc}") from exc


def spawn_popen(
    argv: list[str],
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.Popen:
    """Spawn *argv* as async Popen with pipes and consistent defaults."""
    if not argv:
        raise ValueError("argv must be non-empty.")
    if cwd is not None and not os.path.isdir(cwd):
        raise ValueError(f"Working directory does not exist: {cwd}")
    try:
        return subprocess.Popen(
            argv,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Executable not found: {argv[0]}") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to launch {' '.join(argv)}: {exc}") from exc
