"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
``CMakeLists.txt`` scanner for the DreamStudio CMake plugin.
"""

from __future__ import annotations

import glob
import logging
import os
import re
from dataclasses import dataclass, field

logger = logging.getLogger("DreamStudio.CMake.Scanner")

_COMMAND_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_ENV_RE = re.compile(r"\$ENV\{([A-Za-z_][A-Za-z0-9_]*)\}")
_BUILD_INTERFACE_RE = re.compile(r"\$<BUILD_INTERFACE:([^>]*)>")
_GENEX_RE = re.compile(r"\$<[^>]*>")
_BLOCK_COMMENT_RE = re.compile(r"#\[\[.*?\]\]", re.DOTALL)

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
        ".inl",
        ".ipp",
        ".tpp",
        ".ixx",
        ".cppm",
    }
)
_MAX_INCLUDE_DEPTH = 8
_MAX_SUBDIRECTORY_DEPTH = 12
_MAX_GLOB_MATCHES = 5000
_MAX_DIRECTORIES = 2000

_VISIBILITY = frozenset({"PRIVATE", "PUBLIC", "INTERFACE"})
_IGNORED_ARGUMENTS = frozenset(
    {
        "AFTER",
        "ALIAS",
        "BEFORE",
        "CACHE",
        "CONFIGURE_DEPENDS",
        "EXCLUDE_FROM_ALL",
        "FILE_SET",
        "GLOBAL",
        "IMPORTED",
        "INTERNAL",
        "LIST_DIRECTORIES",
        "MODULE",
        "OBJECT",
        "PARENT_SCOPE",
        "RELATIVE",
        "REQUIRED",
        "QUIET",
        "SHARED",
        "STATIC",
        "SYSTEM",
        "UNKNOWN",
    }
)


@dataclass
class CmakeTarget:
    """One ``add_executable`` / ``add_library`` target."""

    name: str = ""
    kind: str = "executable"
    sources: list = field(default_factory=list)
    include_dirs: list = field(default_factory=list)
    public_include_dirs: list = field(default_factory=list)
    definitions: list = field(default_factory=list)
    public_definitions: list = field(default_factory=list)
    compile_options: list = field(default_factory=list)
    links: list = field(default_factory=list)


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
    definitions: list = field(default_factory=list)
    compile_options: list = field(default_factory=list)
    cmake_files: list = field(default_factory=list)


def find_cmake_root(start: str) -> str | None:
    """Walk upward from *start* looking for the owning CMake project root.

    The highest directory in a contiguous chain of ``CMakeLists.txt`` files is
    returned, so a nested target directory that relies on a parent project for
    ``project()`` and shared include directories resolves to the real root.

    Args:
        start: File or directory to start the upward walk from.

    Returns:
        The owning CMake project directory, or ``None``.
    """
    try:
        current = os.path.abspath(start)
    except Exception:
        return None
    if os.path.isfile(current):
        current = os.path.dirname(current)
    found: str | None = None
    while True:
        if os.path.isfile(os.path.join(current, "CMakeLists.txt")):
            found = current
        elif found is not None:
            break
        if os.path.isdir(os.path.join(current, ".git")):
            break
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return found


def _strip_comments(text: str) -> str:
    """Remove CMake line and block comments outside of double quotes."""
    cleaned = _BLOCK_COMMENT_RE.sub(" ", text)
    lines = []
    for line in cleaned.splitlines():
        in_quote = False
        cut = len(line)
        for index, char in enumerate(line):
            if char == '"' and (index == 0 or line[index - 1] != "\\"):
                in_quote = not in_quote
            elif char == "#" and not in_quote:
                cut = index
                break
        lines.append(line[:cut])
    return "\n".join(lines)


def _split_args(body: str) -> list:
    """Split a command body into arguments, honouring double quotes."""
    args: list = []
    current: list = []
    in_quote = False
    escaped = False
    for char in body:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if char.isspace() and not in_quote:
            if current:
                args.append("".join(current))
                current = []
            continue
        current.append(char)
    if current:
        args.append("".join(current))
    return args


def _iter_commands(text: str):
    """Yield ``(name, args, line_number)`` for each command in *text*."""
    for match in _COMMAND_RE.finditer(text):
        depth = 1
        index = match.end()
        in_quote = False
        escaped = False
        while index < len(text) and depth > 0:
            char = text[index]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
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
    """Expand ``${VAR}``, ``$ENV{VAR}`` and generator expressions once."""
    result = _ENV_RE.sub(lambda match: os.environ.get(match.group(1), ""), value)
    result = _BUILD_INTERFACE_RE.sub(lambda match: match.group(1), result)
    result = re.sub(r"\$<INSTALL_INTERFACE:[^>]*>", "", result)
    result = _GENEX_RE.sub("", result)
    for _ in range(5):
        expanded = _VAR_RE.sub(
            lambda match: variables.get(match.group(1), ""), result
        )
        if expanded == result:
            break
        result = expanded
    return result


def _as_abs(value: str, base: str) -> str:
    """Return *value* absolutised against *base* (generator-expression aware)."""
    cleaned = str(value).strip().strip('"')
    if not cleaned or cleaned.startswith("$") or "$<" in cleaned:
        return ""
    if not os.path.isabs(cleaned):
        cleaned = os.path.normpath(os.path.join(base, cleaned))
    return os.path.normpath(cleaned)


def _add_unique(target: list, value: str) -> None:
    """Append *value* to *target* when non-empty and not already present."""
    if value and value not in target:
        target.append(value)


class _ProjectScanner:
    """Stateful recursive scanner for one CMake project tree."""

    def __init__(self, root: str, model: CmakeModel) -> None:
        self.root = os.path.abspath(root)
        self.model = model
        self._targets: dict = {}
        self._visited_files: set = set()
        self._visited_dirs: set = set()
        self._directory_count = 0

    def scan(self) -> None:
        """Scan the project tree rooted at ``self.root``."""
        base: dict = {
            "CMAKE_SOURCE_DIR": self.root,
            "CMAKE_BINARY_DIR": self.root,
            "PROJECT_SOURCE_DIR": self.root,
            "PROJECT_BINARY_DIR": self.root,
            "CMAKE_CURRENT_SOURCE_DIR": self.root,
            "CMAKE_CURRENT_LIST_DIR": self.root,
            "CMAKE_CURRENT_BINARY_DIR": self.root,
        }
        self._scan_directory(self.root, base, 0)

    def _scan_directory(self, directory: str, variables: dict, depth: int) -> None:
        """Scan ``CMakeLists.txt`` inside *directory* with inherited variables."""
        if depth > _MAX_SUBDIRECTORY_DEPTH or self._directory_count >= _MAX_DIRECTORIES:
            return
        normalized = os.path.normcase(os.path.abspath(directory))
        if normalized in self._visited_dirs:
            return
        self._visited_dirs.add(normalized)
        self._directory_count += 1
        entry = os.path.join(directory, "CMakeLists.txt")
        if not os.path.isfile(entry):
            return
        scope = dict(variables)
        scope["CMAKE_CURRENT_SOURCE_DIR"] = os.path.abspath(directory)
        scope["CMAKE_CURRENT_LIST_DIR"] = os.path.abspath(directory)
        scope["CMAKE_CURRENT_BINARY_DIR"] = os.path.abspath(directory)
        self._scan_file(entry, scope, depth, 0)

    def _scan_file(self, path: str, variables: dict, depth: int, include_depth: int) -> None:
        """Scan one CMake script, mutating *variables* in place."""
        key = os.path.normcase(os.path.abspath(path))
        if key in self._visited_files or include_depth > _MAX_INCLUDE_DEPTH:
            return
        self._visited_files.add(key)
        _add_unique(self.model.cmake_files, os.path.abspath(path))
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            logger.debug("cmake scan skipped %s: %s", path, exc)
            return
        for name, raw_args, _line in _iter_commands(_strip_comments(text)):
            args = self._expand_arguments(raw_args, variables)
            try:
                self._handle(name, args, variables, depth, include_depth)
            except Exception as exc:
                logger.debug("cmake command %s skipped: %s", name, exc)

    @staticmethod
    def _expand_arguments(raw_args: list, variables: dict) -> list:
        """Expand variables and split CMake list values into separate args."""
        expanded: list = []
        for argument in raw_args:
            value = _expand(argument, variables)
            for item in value.split(";"):
                item = item.strip()
                if item:
                    expanded.append(item)
        return expanded

    def _handle(
        self, name: str, args: list, variables: dict, depth: int, include_depth: int
    ) -> None:
        """Dispatch one CMake command."""
        if name == "set":
            self._handle_set(args, variables)
        elif name == "unset":
            if args:
                variables.pop(args[0], None)
        elif name == "list":
            self._handle_list(args, variables)
        elif name == "file":
            self._handle_file(args, variables)
        elif name == "aux_source_directory":
            self._handle_aux_source(args, variables)
        elif name == "include":
            self._handle_include(args, variables, depth, include_depth)
        elif name == "add_subdirectory":
            self._handle_subdirectory(args, variables, depth)
        elif name == "project":
            self._handle_project(args, variables)
        elif name == "add_executable":
            self._handle_target(args, "executable", variables)
        elif name == "add_library":
            self._handle_target(args, "library", variables)
        elif name == "target_sources":
            self._handle_target_sources(args, variables)
        elif name == "include_directories":
            self._handle_include_directories(args, variables)
        elif name == "target_include_directories":
            self._handle_target_include_directories(args, variables)
        elif name == "add_compile_definitions":
            self._handle_definitions(args, self.model.definitions)
        elif name == "add_definitions":
            self._handle_legacy_definitions(args, variables)
        elif name == "target_compile_definitions":
            self._handle_target_definitions(args)
        elif name == "add_compile_options":
            self._handle_options(args, self.model.compile_options)
        elif name == "target_compile_options":
            self._handle_target_options(args)
        elif name == "target_link_libraries":
            self._handle_target_links(args)
        elif name == "find_package":
            if args:
                _add_unique(self.model.packages, args[0])
        elif name == "pkg_check_modules":
            for package in args[1:]:
                if package.upper() not in ("REQUIRED", "QUIET", "IMPORTED_TARGET"):
                    _add_unique(self.model.packages, package)

    def _handle_set(self, args: list, variables: dict) -> None:
        """Handle ``set(VAR value...)`` including CACHE/PARENT_SCOPE forms."""
        if len(args) < 2:
            return
        key = args[0]
        values = [
            item
            for item in args[1:]
            if item.upper() not in ("CACHE", "PARENT_SCOPE", "BOOL", "STRING",
                                    "PATH", "FILEPATH", "INTERNAL")
        ]
        variables[key] = ";".join(values)
        if key == "CMAKE_CXX_STANDARD" and values:
            self.model.cxx_standard = values[0]
        elif key == "CMAKE_C_STANDARD" and values:
            self.model.c_standard = values[0]

    @staticmethod
    def _handle_list(args: list, variables: dict) -> None:
        """Handle the common mutating ``list()`` sub-commands."""
        if len(args) < 2:
            return
        action = args[0].upper()
        key = args[1]
        items = args[2:]
        current = [item for item in variables.get(key, "").split(";") if item]
        if action == "APPEND":
            current.extend(items)
        elif action == "PREPEND":
            current = list(items) + current
        elif action == "REMOVE_ITEM":
            current = [item for item in current if item not in items]
        elif action == "REMOVE_DUPLICATES":
            deduped: list = []
            for item in current:
                _add_unique(deduped, item)
            current = deduped
        elif action == "INSERT":
            position = int(args[2]) if len(args) > 2 and args[2].isdigit() else len(current)
            current[position:position] = args[3:]
        else:
            return
        variables[key] = ";".join(current)

    def _handle_file(self, args: list, variables: dict) -> None:
        """Handle ``file(GLOB ...)`` so source lists are not lost."""
        if len(args) < 3:
            return
        action = args[0].upper()
        if action not in ("GLOB", "GLOB_RECURSE"):
            return
        key = args[1]
        patterns = [
            item
            for item in args[2:]
            if item.upper() not in _IGNORED_ARGUMENTS
        ]
        base = variables.get("CMAKE_CURRENT_SOURCE_DIR", self.root)
        matches: list = []
        for pattern in patterns:
            candidate = pattern if os.path.isabs(pattern) else os.path.join(base, pattern)
            found = glob.glob(candidate, recursive=action == "GLOB_RECURSE")
            for path in found[:_MAX_GLOB_MATCHES]:
                if os.path.isfile(path):
                    _add_unique(matches, os.path.normpath(path))
            if len(matches) >= _MAX_GLOB_MATCHES:
                break
        variables[key] = ";".join(sorted(matches))

    def _handle_aux_source(self, args: list, variables: dict) -> None:
        """Handle ``aux_source_directory(dir VAR)``."""
        if len(args) < 2:
            return
        directory = args[0]
        base = variables.get("CMAKE_CURRENT_SOURCE_DIR", self.root)
        absolute = _as_abs(directory, base)
        if not absolute or not os.path.isdir(absolute):
            return
        matches: list = []
        try:
            for name in sorted(os.listdir(absolute)):
                if os.path.splitext(name)[1] in _SOURCE_EXTS:
                    _add_unique(matches, os.path.join(absolute, name))
        except OSError:
            return
        variables[args[1]] = ";".join(matches)

    def _handle_include(self, args: list, variables: dict, depth: int, include_depth: int) -> None:
        """Scan an included ``.cmake`` script in the current scope."""
        if not args:
            return
        base = variables.get("CMAKE_CURRENT_LIST_DIR", self.root)
        module_dirs = [
            item
            for item in variables.get("CMAKE_MODULE_PATH", "").split(";")
            if item
        ]
        target = args[0]
        candidates: list = []
        if os.path.isabs(target):
            candidates.append(target)
        else:
            candidates.append(os.path.join(base, target))
            for directory in module_dirs:
                candidates.append(os.path.join(directory, target))
        for candidate in candidates:
            if os.path.isfile(candidate):
                self._scan_file(candidate, variables, depth, include_depth + 1)
                return
            if os.path.isfile(candidate + ".cmake"):
                self._scan_file(candidate + ".cmake", variables, depth, include_depth + 1)
                return

    def _handle_subdirectory(self, args: list, variables: dict, depth: int) -> None:
        """Recurse into ``add_subdirectory(dir)`` with a child variable scope."""
        if not args:
            return
        base = variables.get("CMAKE_CURRENT_SOURCE_DIR", self.root)
        directory = _as_abs(args[0], base)
        if directory and os.path.isdir(directory):
            self._scan_directory(directory, dict(variables), depth + 1)

    def _handle_project(self, args: list, variables: dict) -> None:
        """Record ``project(...)`` metadata and source-dir variables."""
        if args:
            if not self.model.project_name:
                self.model.project_name = args[0]
            variables["PROJECT_NAME"] = args[0]
        directory = variables.get("CMAKE_CURRENT_SOURCE_DIR", self.root)
        variables["PROJECT_SOURCE_DIR"] = directory
        variables["PROJECT_BINARY_DIR"] = directory

    def _target_for(self, name: str, kind: str = "") -> CmakeTarget:
        """Return (or create) the target named *name*."""
        target = self._targets.get(name)
        if target is None:
            target = CmakeTarget(name=name, kind=kind or "library")
            self._targets[name] = target
            self.model.targets.append(target)
        elif kind:
            target.kind = kind
        return target

    def _handle_target(self, args: list, kind: str, variables: dict) -> None:
        """Handle ``add_executable`` / ``add_library``."""
        if not args:
            return
        name = args[0]
        target = self._target_for(name, kind)
        base = variables.get("CMAKE_CURRENT_SOURCE_DIR", self.root)
        rest = args[1:]
        if rest and rest[0].upper() in (
            "STATIC", "SHARED", "MODULE", "OBJECT", "INTERFACE", "UNKNOWN", "IMPORTED",
            "ALIAS",
        ):
            rest = rest[1:]
        for item in rest:
            if item.upper() in _IGNORED_ARGUMENTS or item.upper() in _VISIBILITY:
                continue
            if os.path.splitext(item)[1] not in _SOURCE_EXTS:
                continue
            resolved = _as_abs(item, base)
            if resolved:
                _add_unique(target.sources, resolved)

    def _handle_target_sources(self, args: list, variables: dict) -> None:
        """Handle ``target_sources`` source additions."""
        if not args:
            return
        target = self._target_for(args[0])
        base = variables.get("CMAKE_CURRENT_SOURCE_DIR", self.root)
        for item in args[1:]:
            if item.upper() in _VISIBILITY or item.upper() in _IGNORED_ARGUMENTS:
                continue
            if os.path.splitext(item)[1] not in _SOURCE_EXTS:
                continue
            resolved = _as_abs(item, base)
            if resolved:
                _add_unique(target.sources, resolved)

    def _handle_include_directories(self, args: list, variables: dict) -> None:
        """Handle directory-wide ``include_directories``."""
        base = variables.get("CMAKE_CURRENT_SOURCE_DIR", self.root)
        for item in args:
            if item.upper() in _IGNORED_ARGUMENTS or item.upper() in _VISIBILITY:
                continue
            resolved = _as_abs(item, base)
            _add_unique(self.model.include_dirs, resolved)

    def _handle_target_include_directories(self, args: list, variables: dict) -> None:
        """Handle ``target_include_directories`` with visibility keywords."""
        if not args:
            return
        target = self._target_for(args[0])
        base = variables.get("CMAKE_CURRENT_SOURCE_DIR", self.root)
        visibility = "PRIVATE"
        for item in args[1:]:
            upper = item.upper()
            if upper in _VISIBILITY:
                visibility = upper
                continue
            if upper in _IGNORED_ARGUMENTS:
                continue
            resolved = _as_abs(item, base)
            if not resolved:
                continue
            _add_unique(target.include_dirs, resolved)
            if visibility in ("PUBLIC", "INTERFACE"):
                _add_unique(target.public_include_dirs, resolved)

    @staticmethod
    def _handle_definitions(args: list, destination: list) -> None:
        """Append ``-D`` definitions from *args* to *destination*."""
        for item in args:
            if item.upper() in _VISIBILITY or item.upper() in _IGNORED_ARGUMENTS:
                continue
            value = item if item.startswith("-D") else "-D" + item
            _add_unique(destination, value)

    def _handle_legacy_definitions(self, args: list, variables: dict) -> None:
        """Handle ``add_definitions`` for ``-D`` and ``-I`` flags."""
        base = variables.get("CMAKE_CURRENT_SOURCE_DIR", self.root)
        for item in args:
            if item.startswith("-D"):
                _add_unique(self.model.definitions, item)
            elif item.startswith("-I"):
                resolved = _as_abs(item[2:], base)
                _add_unique(self.model.include_dirs, resolved)
            elif item.startswith("-"):
                _add_unique(self.model.compile_options, item)

    def _handle_target_definitions(self, args: list) -> None:
        """Handle ``target_compile_definitions`` with visibility keywords."""
        if not args:
            return
        target = self._target_for(args[0])
        visibility = "PRIVATE"
        for item in args[1:]:
            upper = item.upper()
            if upper in _VISIBILITY:
                visibility = upper
                continue
            if upper in _IGNORED_ARGUMENTS:
                continue
            value = item if item.startswith("-D") else "-D" + item
            _add_unique(target.definitions, value)
            if visibility in ("PUBLIC", "INTERFACE"):
                _add_unique(target.public_definitions, value)

    @staticmethod
    def _handle_options(args: list, destination: list) -> None:
        """Append compile options from *args* to *destination*."""
        for item in args:
            if item.upper() in _VISIBILITY or item.upper() in _IGNORED_ARGUMENTS:
                continue
            if item.startswith("-"):
                _add_unique(destination, item)

    def _handle_target_options(self, args: list) -> None:
        """Handle ``target_compile_options``."""
        if not args:
            return
        target = self._target_for(args[0])
        self._handle_options(args[1:], target.compile_options)

    def _handle_target_links(self, args: list) -> None:
        """Record ``target_link_libraries`` dependencies."""
        if not args:
            return
        target = self._target_for(args[0])
        for item in args[1:]:
            if item.upper() in _VISIBILITY or item.upper() in _IGNORED_ARGUMENTS:
                continue
            _add_unique(target.links, item)

    def finish(self) -> None:
        """Propagate public include dirs/definitions across linked targets."""
        by_name = {target.name: target for target in self.model.targets}
        for _ in range(8):
            changed = False
            for target in self.model.targets:
                for link in target.links:
                    linked = by_name.get(link)
                    if linked is None:
                        continue
                    for directory in linked.public_include_dirs:
                        if directory not in target.include_dirs:
                            target.include_dirs.append(directory)
                            changed = True
                    for definition in linked.public_definitions:
                        if definition not in target.definitions:
                            target.definitions.append(definition)
                            changed = True
                        if definition not in target.public_definitions and target.kind == "library":
                            target.public_definitions.append(definition)
                            changed = True
                    if linked.public_include_dirs:
                        for directory in linked.public_include_dirs:
                            if (
                                target.kind == "library"
                                and directory not in target.public_include_dirs
                            ):
                                target.public_include_dirs.append(directory)
                                changed = True
            if not changed:
                break
        self.model.targets = [
            target
            for target in self.model.targets
            if target.sources or target.include_dirs
        ]


def scan_cmake_text(
    text: str,
    base_dir: str,
    variables: dict | None = None,
) -> tuple[list, dict]:
    """Parse CMake *text* into commands and collected ``set()`` variables."""
    if variables is None:
        variables = {}
    cleaned = _strip_comments(text)
    commands: list = []
    for name, args, line_number in _iter_commands(cleaned):
        expanded = [item for arg in args for item in _expand(arg, variables).split(";") if item]
        if name == "set" and len(expanded) >= 2:
            variables[expanded[0]] = " ".join(expanded[1:])
        commands.append((name, expanded, line_number))
    _ = base_dir
    return commands, variables


def scan_project(root: str) -> CmakeModel:
    """Scan the CMake project rooted at *root* into a model.

    Args:
        root: Directory holding the project's top-level ``CMakeLists.txt``.

    Returns:
        A :class:`CmakeModel` describing include dirs, targets and packages.
    """
    model = CmakeModel(root=os.path.abspath(root))
    if not os.path.isfile(os.path.join(model.root, "CMakeLists.txt")):
        return model
    scanner = _ProjectScanner(model.root, model)
    scanner.scan()
    scanner.finish()
    return model
