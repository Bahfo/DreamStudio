"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Precompiled-header support for the C++ plugin.

Cold translation-unit parses re-parse every included header (seconds on
SDL-scale dependencies). This module harvests workspace ``#include``s,
builds one shared ``.ds/cpp/stable.pch`` with libclang itself in the
background, and validates it per request via a key file. A mismatched or
failed PCH is simply not used — completion falls back to parsing without
it, so the PCH is strictly additive and never load-bearing.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time

logger = logging.getLogger("DreamStudio.Cpp.Pch")

try:
    from editor.utils.solution.paths import (
        CPP_PCH_FILENAME as PCH_FILENAME,
    )
    from editor.utils.solution.paths import (
        CPP_PCH_KEY_FILENAME as PCH_KEY_FILENAME,
    )
except Exception:
    PCH_FILENAME = "stable.pch"
    PCH_KEY_FILENAME = "stable.pch.key"

PCH_STUB_FILENAME = "stable_stub.h"

_INCLUDE_RE = re.compile(r'^[ \t]*#[ \t]*include[ \t]*([<"])([^>"]+)[>"]', re.M)
_MAX_INCLUDES = 200
_MAX_STUB_BYTES = 32768
_MIN_REBUILD_SECONDS = 600


def _cpp_dir(root: str) -> str:
    """Return the ``.ds/cpp`` directory for *root* (uncreated)."""
    from editor.utils.solution.paths import cpp_dir

    return cpp_dir(root)


def harvest_includes(files: list) -> list:
    """Collect raw ``(open_char, path)`` includes from *files*.

    Only file heads are read — includes live at the top. Never raises.

    Args:
        files: Absolute source paths to scan.

    Returns:
        Sorted unique ``(open_char, path)`` tuples (capped).
    """
    found: set = set()
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                head = handle.read(_MAX_STUB_BYTES)
        except OSError:
            continue
        for match in _INCLUDE_RE.finditer(head):
            found.add((match.group(1), match.group(2).strip()))
            if len(found) >= _MAX_INCLUDES:
                break
        if len(found) >= _MAX_INCLUDES:
            break
    # NOTE: plain lists (not tuples) so the key round-trips through JSON
    # unchanged — otherwise every validation compares unequal and rebuilds.
    return [[open_char, path] for open_char, path in sorted(found)]


def _base_flags(root: str) -> list:
    """Return the normalized base flags the PCH is built and keyed with.

    Uses the generated ``compile_flags.txt`` when present so the PCH and
    its consumers derive flags from the same source by construction.

    Args:
        root: Solution root.

    Returns:
        Ordered flag list (defaults + resource dir + generated flags).
    """
    from editor.utils.solution.paths import compile_flags_path

    try:
        from . import args as cpp_args

        base = list(cpp_args._DEFAULTS) + cpp_args.resource_args()
    except Exception:
        base = ["-x", "c++", "-std=c++20"]
    try:
        flags_path = compile_flags_path(root)
        if os.path.isfile(flags_path):
            with open(flags_path, encoding="utf-8") as handle:
                for line in handle.read().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        base.append(line)
    except OSError as exc:
        logger.debug("pch base flags skipped: %s", exc)
    return base


def _key_for(root: str, includes: list, base: list) -> dict:
    """Build the validity key dict for *root*.

    Args:
        root: Solution root.
        includes: Harvested ``(open_char, path)`` includes.
        base: Normalized base flags.

    Returns:
        Key dict with flags hash, includes and newest header mtime.
    """
    digest = hashlib.sha1()
    digest.update(json.dumps(base, sort_keys=True).encode("utf-8"))
    digest.update(json.dumps(includes, sort_keys=True).encode("utf-8"))
    newest = 0.0
    anchor = os.path.abspath(root)
    try:
        for current, _directories, files in os.walk(anchor):
            if os.path.basename(current).startswith("."):
                continue
            for name in files:
                if os.path.splitext(name)[1].lower() in (
                    ".h", ".hpp", ".hh", ".hxx", ".ixx",
                ):
                    try:
                        mtime = os.path.getmtime(os.path.join(current, name))
                    except OSError:
                        continue
                    if mtime > newest:
                        newest = mtime
    except Exception as exc:
        logger.debug("pch mtime scan skipped: %s", exc)
    return {
        "flags": digest.hexdigest(),
        "includes": includes,
        "headers_mtime": newest,
        "built_at": 0.0,
    }


def _read_key(root: str) -> dict | None:
    """Read the stored PCH key for *root*, or ``None`` when absent."""
    try:
        with open(
            os.path.join(_cpp_dir(root), PCH_KEY_FILENAME), encoding="utf-8"
        ) as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _pch_path(root: str) -> str:
    """Return the absolute PCH path for *root*."""
    return os.path.join(_cpp_dir(root), PCH_FILENAME)


def is_valid(root: str, files: list | None = None) -> bool:
    """Check whether *root*'s PCH matches current flags and headers.

    Args:
        root: Solution root owning the PCH.
        files: Workspace files to harvest (re-harvested when omitted).

    Returns:
        ``True`` when the PCH file exists and its key matches.
    """
    try:
        stored = _read_key(root)
        if stored is None or not stored.get("built_at"):
            return False
        if not os.path.isfile(_pch_path(root)):
            return False
        if files is None:
            return bool(stored.get("flags"))
        base = _base_flags(root)
        current = _key_for(root, harvest_includes(files), base)
        if current["flags"] != stored.get("flags"):
            return False
        if current["includes"] != stored.get("includes"):
            return False
        if current["headers_mtime"] > float(stored.get("built_at", 0.0)):
            return False
        return True
    except Exception as exc:
        logger.debug("pch validation failed: %s", exc)
        return False


def include_args(root: str | None) -> list:
    """Return ``-include-pch`` args for *root* when its PCH is usable.

    Deliberately cheap (key-file read only, no header walk): per-keystroke
    freshness is enforced by rebuilds, not by revalidation here.

    Args:
        root: Solution root (``None`` disables).

    Returns:
        ``['-include-pch', path]`` or ``[]`` — never raises.
    """
    try:
        if not root:
            return []
        stored = _read_key(root)
        if stored is None or not stored.get("built_at"):
            return []
        path = _pch_path(root)
        if not os.path.isfile(path):
            return []
        return ["-include-pch", path]
    except Exception as exc:
        logger.debug("pch args skipped: %s", exc)
        return []


def ensure_for_root(root: str, files: list) -> bool:
    """Build (or skip) the PCH for *root* from *files*. Background use.

    Rebuilds when the key mismatches, honouring a minimum rebuild
    interval so header churn cannot busy-loop the indexer. Never raises.

    Args:
        root: Solution root receiving ``.ds/cpp/stable.pch``.
        files: Workspace source files to harvest includes from.

    Returns:
        ``True`` when a usable PCH exists afterwards.
    """
    try:
        if not root or not os.path.isdir(root):
            return False
        includes = harvest_includes(files)
        if not includes:
            return False
        base = _base_flags(root)
        current = _key_for(root, includes, base)
        stored = _read_key(root)
        if stored is not None and os.path.isfile(_pch_path(root)):
            same_config = (
                stored.get("flags") == current["flags"]
                and stored.get("includes") == current["includes"]
            )
            headers_fresh = current["headers_mtime"] <= float(
                stored.get("built_at", 0.0)
            )
            if same_config and headers_fresh:
                return True
            if same_config and (
                time.time() - float(stored.get("built_at", 0.0))
                < _MIN_REBUILD_SECONDS
            ):
                # Only header mtimes drifted and the last build is recent:
                # serve the existing PCH, rebuild on a later pass.
                return True
        return _build(root, includes, base, current)
    except Exception as exc:
        logger.debug("pch ensure failed: %s", exc)
        return False


def _build(root: str, includes: list, base: list, key: dict) -> bool:
    """Parse the stub header and save the PCH for *root*.

    Args:
        root: Solution root receiving the artefacts.
        includes: Harvested ``(open_char, path)`` includes.
        base: Normalized base flags.
        key: Validity key dict to persist alongside.

    Returns:
        ``True`` when a usable PCH exists afterwards.
    """
    try:
        import clang.cindex as cindex
        from clang.cindex import Index, TranslationUnit
    except Exception as exc:
        logger.debug("pch skipped, libclang unavailable: %s", exc)
        return False
    if not hasattr(TranslationUnit, "save"):
        logger.debug("pch skipped, serializer unavailable")
        return False
    _ = cindex
    directory = _cpp_dir(root)
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as exc:
        logger.debug("pch skipped, cannot create %s: %s", directory, exc)
        return False
    stub_path = os.path.join(directory, PCH_STUB_FILENAME)
    lines = []
    for open_char, path in includes:
        if open_char == '"':
            candidate = path if os.path.isabs(path) else os.path.join(root, path)
            if not os.path.isfile(candidate):
                continue
            lines.append(f'#include "{candidate}"')
        else:
            lines.append(f"#include <{path}>")
    if not lines:
        return False
    try:
        with open(stub_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except OSError as exc:
        logger.debug("pch stub skipped: %s", exc)
        return False
    try:
        tu = Index.create().parse(
            stub_path,
            args=base,
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
        )
    except Exception as exc:
        logger.warning("pch build parse failed: %s", exc)
        return False
    try:
        tu.save(_pch_path(root))
    except Exception as exc:
        logger.warning("pch save failed: %s", exc)
        return False
    if not os.path.isfile(_pch_path(root)):
        return False
    key["built_at"] = time.time()
    try:
        tmp_path = os.path.join(directory, PCH_KEY_FILENAME + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(key, handle, indent=2, sort_keys=True)
        os.replace(tmp_path, os.path.join(directory, PCH_KEY_FILENAME))
    except OSError as exc:
        logger.debug("pch key skipped: %s", exc)
        return False
    logger.info("pch built: %d includes at %s", len(lines), _pch_path(root))
    return True


__all__ = [
    "PCH_FILENAME",
    "PCH_KEY_FILENAME",
    "ensure_for_root",
    "harvest_includes",
    "include_args",
    "is_valid",
]
