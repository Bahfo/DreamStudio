# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Out-of-process analysis server for Ironica.

Runs the Python plugin's CPU-bound work (semantic highlights, fold
regions, jedi diagnostics) in a dedicated interpreter, so heavy typing
in large files never freezes the IDE's main thread.

The server is intentionally launched as a *plain script* rather than
``python -m``.  Package ``__init__`` chains are bypassed by stubbing the
``editor`` / ``editor.Ironica`` packages before any ``editor.*`` module is
imported — the real ``editor/__init__.py`` pulls in the whole GUI stack
(terminal, docker, git …) which must not exist inside the analysis child.

Wire protocol (mirrors ``analysis_bridge``): 8-byte little-endian length
followed by a pickle payload, strictly request/response over stdin/stdout.
The ``None``/empty sentinel tells the loop to exit.
"""

from __future__ import annotations

import logging
import os
import pickle
import struct
import sys
import types

_FRAME_HEADER = struct.Struct("<Q")
_PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL

logger = logging.getLogger("DreamStudio.Analysis.Server")

# ----------------------------------------------------------------------
# Isolated package imports
# ----------------------------------------------------------------------


def _stub_package(name: str, path: str) -> None:
    """Register a namespace-only package so its ``__init__.py`` never runs."""
    module = types.ModuleType(name)
    module.__path__ = [path]
    module.__package__ = name
    sys.modules[name] = module


def _install_package_stubs() -> None:
    # When the real ``editor`` package is already imported (unit tests),
    # keep it — stubbing must only isolate the *child* process, which has
    # never touched the ``editor`` package before this script runs.
    if "editor" in sys.modules:
        return
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    editor_root = os.path.join(root, "editor")
    ironica_root = os.path.join(editor_root, "Ironica")
    _stub_package("editor", editor_root)
    _stub_package("editor.Ironica", ironica_root)
    _stub_package("editor.Ironica.utils", os.path.join(ironica_root, "utils"))
    _stub_package("editor.Ironica.plugins", os.path.join(ironica_root, "plugins"))
    _stub_package(
        "editor.Ironica.plugins.python",
        os.path.join(ironica_root, "plugins", "python"),
    )


_install_package_stubs()

# ----------------------------------------------------------------------
# Framing (kept local — importing analysis_bridge would re-enter the
# ``editor`` package chain this process exists to avoid)
# ----------------------------------------------------------------------


class _WireError(EOFError):
    pass


def _read_exact(stream, n: int) -> bytes:
    chunks: list = []
    remaining = n
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            raise _WireError("parent closed its output stream")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_frame(stream) -> object:
    header = _read_exact(stream, _FRAME_HEADER.size)
    (size,) = _FRAME_HEADER.unpack(header)
    data = _read_exact(stream, size)
    if not data:
        return None
    return pickle.loads(data)


def _write_frame(stream, payload) -> None:
    data = pickle.dumps(payload, protocol=_PICKLE_PROTOCOL)
    stream.write(_FRAME_HEADER.pack(len(data)))
    stream.write(data)
    stream.flush()


# ----------------------------------------------------------------------
# Environment (theme + python config must match the parent editor)
# ----------------------------------------------------------------------

_LAST_THEME: str = ""
_LAST_CONFIG: object = None


def _ensure_environment(config: dict, theme_name: str) -> None:
    global _LAST_THEME, _LAST_CONFIG
    changed = False

    if theme_name != _LAST_THEME:
        try:
            from editor.Ironica.retheme import set_active_theme

            set_active_theme(theme_name)
        except Exception as exc:
            logger.warning("Unable to set theme %r: %s", theme_name, exc)
        _LAST_THEME = theme_name
        changed = True

    if config != _LAST_CONFIG:
        if config:
            try:
                from editor.Ironica.language_engine import LanguageRegistry

                LanguageRegistry.register_language_dict(config)
            except Exception as exc:
                logger.warning("Unable to register python config: %s", exc)
        _LAST_CONFIG = config
        changed = True

    if changed:
        try:
            from editor.Ironica.plugins.python.semantic_highlights import (
                invalidate_semantic_cache,
            )

            invalidate_semantic_cache()
        except Exception:
            pass


# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------


def _handle_analysis(request_id: int, source: str, config: dict, theme_name: str):
    _ensure_environment(config, theme_name)
    from editor.Ironica.plugins.python.semantic_highlights import (
        get_semantic_highlights,
    )
    from editor.Ironica.plugins.python.folding import compute_fold_regions

    highlights = get_semantic_highlights(source)
    fold_regions = compute_fold_regions(source)
    return ("analysis", request_id, highlights, fold_regions)


def _handle_diagnostics(request_id: int, source: str, file_path):
    from editor.Ironica.plugins.python.detect_problems import detect_problems

    diagnostics = detect_problems(source, file_path)
    return ("diagnostics", request_id, diagnostics)


_MAX_COMPLETION_ITEMS = 50


def _handle_completions(request_id: int, source: str, line: int, col: int, file_path):
    import jedi

    lines = source.split("\n") if source else [""]
    jedi_line = max(1, min(line + 1, len(lines)))

    line_len = len(lines[jedi_line - 1]) if 0 < jedi_line <= len(lines) else 0
    jedi_col = max(0, min(col, line_len))

    script = jedi.Script(code=source, path=file_path)
    try:
        comps = script.complete(line=jedi_line, column=jedi_col)
    except Exception as exc:
        logger.warning("Jedi complete failed: %s", exc)
        return ("completions", request_id, [])

    results = []
    for c in comps:
        results.append(
            {
                "text": c.name,
                "insert_text": c.complete or c.name,
                "kind": c.type or "",
                "signature": "",
            }
        )
        if len(results) >= _MAX_COMPLETION_ITEMS:
            break
    return ("completions", request_id, results)


def handle_request(payload) -> object:
    """Dispatch one request and return its response payload.

    Public for direct in-process testing of the dispatch logic.
    """
    if payload is None:
        return None

    try:
        kind = payload[0]
        if kind == "analysis":
            _, request_id, source, config, theme_name = payload
            return _handle_analysis(request_id, source, config, theme_name)
        if kind == "diagnostics":
            _, request_id, source, file_path = payload
            return _handle_diagnostics(request_id, source, file_path)
        if kind == "completions":
            _, request_id, source, line, col, file_path = payload
            return _handle_completions(request_id, source, line, col, file_path)
    except Exception as exc:
        logger.exception("analysis-server request failed")
        request_id = payload[1] if len(payload) > 1 else None
        return ("error", request_id, f"{type(exc).__name__}: {exc}")

    request_id = payload[1] if len(payload) > 1 else None
    return ("error", request_id, "unknown request payload")


def main() -> int:
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    stdin = getattr(sys.stdin, "buffer", sys.stdin)
    stdout = getattr(sys.stdout, "buffer", sys.stdout)

    while True:
        try:
            payload = _read_frame(stdin)
        except (_WireError, EOFError, OSError, struct.error, pickle.UnpicklingError):
            break
        if payload is None:
            break

        response = handle_request(payload)
        try:
            _write_frame(stdout, response)
        except (BrokenPipeError, OSError):
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
