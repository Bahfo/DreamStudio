"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Compile database generator for the DreamStudio CMake plugin.

Turns a scanned :class:`CmakeModel` into ``.ds/cpp/compile_commands.json``
and ``.ds/cpp/compile_flags.txt`` so the C++ plugin's flag resolution can
index third-party dependencies without the user hand-writing a compile
database. Writes are atomic and skipped when content is unchanged.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess

from editor.utils.solution.paths import (
    COMPILE_COMMANDS_FILENAME,
    COMPILE_FLAGS_FILENAME,
    cpp_dir,
)

from .scanner import CmakeModel

logger = logging.getLogger("DreamStudio.CMake.Generator")

_pkg_cache: dict = {}


def _pkg_cflags(package: str) -> list:
    """Query ``pkg-config --cflags`` for *package*, cached per process.

    The package name is used verbatim — no name mapping is assumed.

    Args:
        package: Package name as discovered by the scanner.

    Returns:
        Flag list (possibly empty) — never raises.
    """
    key = str(package).strip()
    if not key:
        return []
    if key in _pkg_cache:
        return list(_pkg_cache[key])
    flags: list = []
    try:
        proc = subprocess.run(
            ["pkg-config", "--cflags", key],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass
    else:
        if proc.returncode == 0:
            flags = shlex.split(proc.stdout.decode(errors="replace").strip())
    _pkg_cache[key] = flags
    return list(flags)


def _probe_compiler() -> str:
    """Return the first available C++ compiler driver name.

    Returns:
        Driver name (``"c++"`` fallback, never empty).
    """
    for candidate in ("c++", "clang++", "g++"):
        if shutil.which(candidate):
            return candidate
    return "c++"


def _model_flags(model: CmakeModel) -> tuple[list, list, list]:
    """Derive ``(std_flags, include_flags, define_flags)`` for *model*.

    Args:
        model: Scanned CMake model.

    Returns:
        Tuple of flag lists ready for splicing into commands.
    """
    std_flags: list = []
    standard = (model.cxx_standard or "").strip()
    if standard and standard[0].isdigit():
        std_flags = [f"-std=c++{standard}"]
    include_flags: list = []
    for directory in model.include_dirs:
        if directory and os.path.isdir(directory):
            include_flags += ["-I", directory]
    extra_flags: list = []
    defines: list = []
    for package in model.packages:
        for flag in _pkg_cflags(package):
            if flag.startswith("-I"):
                if flag not in extra_flags and flag[2:] not in include_flags:
                    extra_flags.append(flag)
            elif flag.startswith("-D"):
                if flag not in defines:
                    defines.append(flag)
            elif flag and flag not in extra_flags:
                extra_flags.append(flag)
    return std_flags, include_flags, extra_flags + defines


def _atomic_write_text(path: str, content: str) -> bool:
    """Write *content* to *path* atomically; skip when unchanged.

    Args:
        path: Destination file path.
        content: Text content to persist.

    Returns:
        ``True`` when the file was written, ``False`` when skipped/failed.
    """
    try:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                if handle.read() == content:
                    return False
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
        return True
    except OSError as exc:
        logger.warning("cmake generate skipped %s: %s", path, exc)
        return False


def generate(root: str, model: CmakeModel) -> dict:
    """Write the compile database and flags file for *model*.

    Args:
        root: Solution root receiving ``.ds/cpp/`` artefacts.
        model: Scanned CMake model.

    Returns:
        Dict with ``compile_commands``, ``compile_flags`` and ``entries``.
    """
    directory = cpp_dir(root, ensure=True)
    commands_path = os.path.join(directory, COMPILE_COMMANDS_FILENAME)
    flags_path = os.path.join(directory, COMPILE_FLAGS_FILENAME)

    compiler = _probe_compiler()
    std_flags, include_flags, extra_flags = _model_flags(model)

    entries: list = []
    seen: set = set()
    for target in model.targets:
        target_flags = list(include_flags)
        for directory_flag in target.include_dirs:
            if os.path.isdir(directory_flag):
                target_flags += ["-I", directory_flag]
        for source in target.sources:
            if source in seen:
                continue
            seen.add(source)
            entries.append(
                {
                    "directory": model.root or os.path.abspath(root),
                    "file": source,
                    "arguments": (
                        [compiler]
                        + std_flags
                        + target_flags
                        + extra_flags
                        + [source]
                    ),
                }
            )

    commands_content = json.dumps(entries, indent=2) + "\n"
    _atomic_write_text(commands_path, commands_content)

    flag_lines: list = []
    flag_lines += std_flags
    for index in range(0, len(include_flags), 2):
        pair = include_flags[index:index + 2]
        flag_lines.append("".join(pair) if len(pair) == 2 else pair[0])
    flag_lines += extra_flags
    _atomic_write_text(flags_path, "\n".join(flag_lines) + "\n")

    logger.info("cmake database generated: %d entries at %s", len(entries), commands_path)
    return {
        "compile_commands": commands_path,
        "compile_flags": flags_path,
        "entries": len(entries),
    }
