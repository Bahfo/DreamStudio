"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

``CMakeLists.txt`` scanner for the DreamStudio CMake plugin.

Parses a paren-aware subset of CMake (commands may span lines, ``#``
comments, quoted arguments, single-level ``${VAR}`` expansion from
``set()``) into a :class:`CmakeModel` of targets, include directories,
linked packages and language standards. Dependency-free and side-effect
free — generation lives in ``generator.py``.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field

logger = logging.getLogger("DreamStudio.CMake.Scanner")

_COMMAND_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_SOURCE_EXTS = frozenset(
    {
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".c++",
        ".C",
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
        ".ixx",
        ".cppm",
    }
)


@dataclass
class CmakeTarget:
    """One ``add_executable`` / ``add_library`` target."""

    name: str = ""
    kind: str = "executable"
    sources: list = field(default_factory=list)
    include_dirs: list = field(default_factory=list)


@dataclass
class CmakeModel:
    """Structured result of scanning a CMake project."""

    root: str = ""
    project_name: str = ""
    cxx_standard: str = ""
    c_standard: str = ""
    include_dirs: list = field(default_factory=list)
    packages: list = field(default_factory=list)
    targets: list = field(default_factory=list)


def find_cmake_root(start: str) -> str | None:
    """Walk upward from *start* looking for a ``CMakeLists.txt``.

    Args:
        start: File or directory to start searching from.

    Returns:
        Directory holding ``CMakeLists.txt``, or ``None``.
    """
    try:
        current = os.path.abspath(start)
    except Exception:
        return None
    if os.path.isfile(current):
        current = os.path.dirname(current)
    while True:
        if os.path.isfile(os.path.join(current, "CMakeLists.txt")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _strip_comment(line: str) -> str:
    """Remove a ``#`` comment starting outside of double quotes."""
    in_quote = False
    for index, char in enumerate(line):
        if char == '"':
            in_quote = not in_quote
        elif char == "#" and not in_quote:
            return line[:index]
    return line


def _split_args(body: str) -> list:
    """Split a command body into arguments, honouring double quotes."""
    args: list = []
    current: list = []
    in_quote = False
    index = 0
    while index < len(body):
        char = body[index]
        if char == '"':
            in_quote = not in_quote
        elif char.isspace() and not in_quote:
            if current:
                args.append("".join(current))
                current = []
        else:
            current.append(char)
        index += 1
    if current:
        args.append("".join(current))
    return args


def _iter_commands(text: str):
    """Yield ``(name, args, line_number)`` for each top-level command."""
    for match in _COMMAND_RE.finditer(text):
        depth = 1
        index = match.end()
        in_quote = False
        while index < len(text) and depth > 0:
            char = text[index]
            if char == '"':
                in_quote = not in_quote
            elif not in_quote:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
            index += 1
        if depth != 0:
            continue
        body = text[match.end() : index - 1]
        line_number = text.count("\n", 0, match.start()) + 1
        yield match.group(1).lower(), _split_args(body), line_number


def _expand(value: str, variables: dict) -> str:
    """Expand ``${VAR}`` references once using *variables*."""

    def _replace(match: re.Match) -> str:
        return variables.get(match.group(1), match.group(0))

    return _VAR_RE.sub(_replace, value)


def _as_abs(path: str, base: str) -> str:
    """Return *path* absolutised against *base* (``BUILD_INTERFACE`` aware)."""
    cleaned = path.strip()
    if cleaned.startswith("$<BUILD_INTERFACE:") and cleaned.endswith(">"):
        cleaned = cleaned[len("$<BUILD_INTERFACE:") : -1]
    cleaned = cleaned.strip().strip('"')
    if not cleaned or cleaned.startswith("$<"):
        return ""
    if not os.path.isabs(cleaned):
        cleaned = os.path.normpath(os.path.join(base, cleaned))
    return cleaned


def scan_cmake_text(
    text: str,
    base_dir: str,
    variables: dict | None = None,
) -> tuple[list, dict]:
    """Parse CMake *text* into commands and collected ``set()`` variables.

    Args:
        text: Raw file content.
        base_dir: Directory used to absolutise relative paths.
        variables: Mutable variable table shared across included files.

    Returns:
        Tuple of ``(commands, variables)`` where commands is a list of
        ``(name, expanded_args, line_number)``.
    """
    if variables is None:
        variables = {}
    cleaned = "\n".join(_strip_comment(line) for line in text.splitlines())
    commands: list = []
    for name, args, line_number in _iter_commands(cleaned):
        expanded = [_expand(arg, variables) for arg in args]
        if name == "set" and len(expanded) >= 2:
            variables[expanded[0]] = " ".join(expanded[1:])
        commands.append((name, expanded, line_number))
    _ = base_dir
    return commands, variables


def scan_project(root: str) -> CmakeModel:
    """Scan the CMake project rooted at *root* into a model.

    Args:
        root: Directory holding the top-level ``CMakeLists.txt``.

    Returns:
        Populated :class:`CmakeModel` (empty when unreadable).
    """
    model = CmakeModel(root=os.path.abspath(root))
    entry = os.path.join(model.root, "CMakeLists.txt")
    try:
        with open(entry, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        logger.debug("cmake scan skipped %s: %s", entry, exc)
        return model

    variables: dict = {}
    commands, variables = scan_cmake_text(text, model.root, variables)

    included: list = []
    for name, args, _line in commands:
        if name == "include" and args:
            candidate = _as_abs(args[0], model.root)
            if candidate.endswith(".cmake") and os.path.isfile(candidate):
                included.append(candidate)
    for path in included[:8]:
        try:
            with open(path, encoding="utf-8") as handle:
                extra = handle.read()
        except OSError:
            continue
        extra_commands, variables = scan_cmake_text(
            extra, os.path.dirname(path), variables
        )
        commands.extend(extra_commands)

    targets: dict = {}
    for name, args, _line in commands:
        if name == "project" and args:
            model.project_name = args[0]
        elif name == "set" and len(args) >= 2:
            key, value = args[0], " ".join(args[1:])
            if key == "CMAKE_CXX_STANDARD":
                model.cxx_standard = value
            elif key == "CMAKE_C_STANDARD":
                model.c_standard = value
        elif name in ("add_executable", "add_library") and args:
            target_name = args[0]
            rest = args[1:]
            kind = "executable" if name == "add_executable" else "library"
            if rest and rest[0] in ("STATIC", "SHARED", "INTERFACE", "MODULE"):
                rest = rest[1:]
            sources = [
                _as_abs(item, model.root)
                for item in rest
                if os.path.splitext(item)[1] in _SOURCE_EXTS
            ]
            targets[target_name] = CmakeTarget(
                name=target_name,
                kind=kind,
                sources=[item for item in sources if item],
            )
        elif name in ("include_directories",) and args:
            for item in args:
                resolved = _as_abs(item, model.root)
                if resolved and resolved not in model.include_dirs:
                    model.include_dirs.append(resolved)
        elif name == "target_include_directories" and len(args) >= 2:
            target = targets.get(args[0])
            candidates = [
                item
                for item in args[1:]
                if item not in ("PRIVATE", "PUBLIC", "INTERFACE")
            ]
            for item in candidates:
                resolved = _as_abs(item, model.root)
                if not resolved:
                    continue
                if target is not None and resolved not in target.include_dirs:
                    target.include_dirs.append(resolved)
                elif resolved not in model.include_dirs:
                    model.include_dirs.append(resolved)
        elif name == "find_package" and args:
            package = args[0]
            if package not in model.packages:
                model.packages.append(package)
        elif name == "pkg_check_modules" and len(args) >= 2:
            for package in args[1:]:
                if (
                    package not in ("REQUIRED", "QUIET")
                    and package not in model.packages
                ):
                    model.packages.append(package)

    model.targets = list(targets.values())
    return model
