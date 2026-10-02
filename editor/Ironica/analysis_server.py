# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Out-of-process analysis server for Ironica.

Runs the Python plugin's CPU-bound work (semantic highlights, fold
regions, jedi diagnostics) in a dedicated interpreter, so heavy typing
in large files never freezes the IDE's main thread.

The server is intentionally launched as a *plain script* rather than
``python -m``.  The ``editor`` package itself is a pure standard-library
/ PyQt6 import hub (safe to load here), but ``editor.Ironica`` still
pulls the whole widget GUI chain, so the ``Ironica`` subtree is stubbed
as namespace-only packages before any ``editor.Ironica.*`` module is
imported - those modules must never exist inside the analysis child.

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
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        root = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root not in sys.path:
        sys.path.insert(0, root)
    ironica_root = os.path.join(root, "editor", "Ironica")
    # NOTE: the ``editor`` package itself is only an import hub now, so the
    # child loads it directly; plugin modules rely on its namespace.
    import editor  # noqa: F401

    _stub_package("editor.Ironica", ironica_root)
    _stub_package("editor.Ironica.utils", os.path.join(ironica_root, "utils"))
    _stub_package("editor.Ironica.plugins", os.path.join(ironica_root, "plugins"))
    _stub_package(
        "editor.Ironica.plugins.python",
        os.path.join(ironica_root, "plugins", "python"),
    )
    _stub_package(
        "editor.Ironica.plugins.clang",
        os.path.join(ironica_root, "plugins", "clang"),
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
# Environment (theme + language config must match the parent editor)
# ----------------------------------------------------------------------

_LAST_THEME: str = ""
_LAST_CONFIGS: dict = {}


def _ensure_environment(config: dict, theme_name: str, lang: str = "python") -> None:
    """Sync theme and language config for *lang*, invalidating caches.

    Args:
        config: Language config dict (plain data) for *lang*.
        theme_name: Active theme name in the parent editor.
        lang: Language id (``"python"`` or ``"clang"``).
    """
    global _LAST_THEME

    if theme_name != _LAST_THEME:
        try:
            from editor.Ironica.retheme import set_active_theme

            set_active_theme(theme_name)
        except Exception as exc:
            logger.warning("Unable to set theme %r: %s", theme_name, exc)
        _LAST_THEME = theme_name
        changed = True
    else:
        changed = False

    if config != _LAST_CONFIGS.get(lang):
        if config:
            try:
                from editor.Ironica.language_engine import LanguageRegistry

                LanguageRegistry.register_language_dict(config)
            except Exception as exc:
                logger.warning("Unable to register %s config: %s", lang, exc)
        _LAST_CONFIGS[lang] = config
        changed = True

    if changed:
        for module_name, func_name in (
            ("editor.Ironica.plugins.python.semantic_highlights", "invalidate_semantic_cache"),
            ("editor.Ironica.plugins.clang.c_semantic_highlights", "invalidate_semantic_cache"),
        ):
            try:
                module = __import__(module_name, fromlist=[func_name])
                getattr(module, func_name)()
            except Exception:
                pass


def _resolve_spills(payload):
    """Restore spilled file-ref sources in *payload* (parent spilled >1MB)."""
    resolved = []
    for item in payload:
        if isinstance(item, dict) and "__spilled_source__" in item:
            try:
                with open(item["__spilled_source__"], "r", encoding="utf-8") as handle:
                    resolved.append(handle.read())
            except OSError as exc:
                logger.error("Missing spilled source: %s", exc)
                resolved.append("")
        else:
            resolved.append(item)
    return type(payload)(resolved)


# ----------------------------------------------------------------------
# Memory guard (keeps the child inside the large-file memory budget)
# ----------------------------------------------------------------------

_RSS_CAP_MB = int(os.environ.get("DREAMSTUDIO_ANALYSIS_RSS_MB", "600"))


def _rss_mb() -> float:
    """Return current process RSS in MiB, or -1 when unavailable."""
    try:
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        return -1.0


def _check_rss_budget() -> None:
    """Drop warm caches when the child exceeds its RSS budget.

    Translation units, Jedi scripts and semantic token caches are all
    recomputable; shedding them trades one slower re-parse for never
    spiking past the budget on 100k-line buffers.
    """
    if _RSS_CAP_MB <= 0:
        return
    current = _rss_mb()
    if current < 0 or current <= _RSS_CAP_MB:
        return
    logger.warning(
        "Analysis RSS %.0f MiB exceeds %d MiB budget; shedding caches",
        current,
        _RSS_CAP_MB,
    )
    global _CLANG_ADAPTER
    global _JEDI_LAST_SOURCE, _JEDI_LAST_PATH, _JEDI_LAST_SCRIPT
    try:
        if _CLANG_ADAPTER is not None:
            _CLANG_ADAPTER.clear_tu_cache()
    except Exception:
        pass
    _JEDI_LAST_SOURCE = ""
    _JEDI_LAST_PATH = None
    _JEDI_LAST_SCRIPT = None
    for module_name, func_name in (
        ("editor.Ironica.plugins.python.semantic_highlights", "invalidate_semantic_cache"),
        ("editor.Ironica.plugins.clang.c_semantic_highlights", "invalidate_semantic_cache"),
    ):
        try:
            module = __import__(module_name, fromlist=[func_name])
            getattr(module, func_name)()
        except Exception:
            pass


# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------


def _handle_analysis(request_id: int, source: str, config: dict, theme_name: str):
    _ensure_environment(config, theme_name, "python")
    from editor.Ironica.plugins.python.semantic_highlights import (
        get_semantic_highlights,
    )
    from editor.Ironica.plugins.python.folding import compute_fold_regions

    highlights = get_semantic_highlights(source)
    fold_regions = compute_fold_regions(source)
    _check_rss_budget()
    return ("analysis", request_id, highlights, fold_regions)


_CLANG_ADAPTER = None


def _clang_adapter():
    """Return the process-wide shared ClangAdapter (warm TU cache)."""
    global _CLANG_ADAPTER
    if _CLANG_ADAPTER is None:
        from editor.Ironica.plugins.clang.clang_adapter import ClangAdapter

        _CLANG_ADAPTER = ClangAdapter()
    return _CLANG_ADAPTER


def _handle_c_analysis(
    request_id: int,
    source: str,
    file_path,
    config: dict,
    theme_name: str,
):
    _ensure_environment(config, theme_name, "clang")
    from editor.Ironica.plugins.clang.c_folding import compute_fold_regions
    from editor.Ironica.plugins.clang.c_semantic_highlights import CSemanticProvider

    provider = CSemanticProvider(adapter=_clang_adapter())
    try:
        highlights = provider.get_semantic_ranges(source, file_path)
    except Exception as exc:
        logger.warning("C semantic analysis failed: %s", exc)
        highlights = []
    try:
        fold_regions = compute_fold_regions(source)
    except Exception as exc:
        logger.warning("C folding failed: %s", exc)
        fold_regions = []
    _check_rss_budget()
    return ("c_analysis", request_id, highlights, fold_regions)


def _handle_diagnostics(request_id: int, source: str, file_path):
    return ("diagnostics", request_id, [])


_MAX_COMPLETION_ITEMS = 50

_JEDI_LAST_SOURCE: str = ""
_JEDI_LAST_PATH = None
_JEDI_LAST_SCRIPT = None


def _jedi_script(source: str, file_path):
    """Return a cached Jedi script for *source*, reusing the last buffer.

    Args:
        source: Full buffer content.
        file_path: Optional path handed to Jedi for context.

    Returns:
        A ``jedi.Script`` bound to *source*.
    """
    global _JEDI_LAST_SOURCE, _JEDI_LAST_PATH, _JEDI_LAST_SCRIPT
    import jedi

    if (
        _JEDI_LAST_SCRIPT is not None
        and file_path == _JEDI_LAST_PATH
        and source == _JEDI_LAST_SOURCE
    ):
        return _JEDI_LAST_SCRIPT
    script = jedi.Script(code=source, path=file_path)
    _JEDI_LAST_SOURCE = source
    _JEDI_LAST_PATH = file_path
    _JEDI_LAST_SCRIPT = script
    return script


def _handle_completions(request_id: int, source: str, line: int, col: int, file_path):
    lines = source.split("\n") if source else [""]
    jedi_line = max(1, min(line + 1, len(lines)))

    line_len = len(lines[jedi_line - 1]) if 0 < jedi_line <= len(lines) else 0
    jedi_col = max(0, min(col, line_len))

    script = _jedi_script(source, file_path)
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
                # NOTE: ``c.complete`` is only the missing suffix (typed
                # "imp" -> "ort"); clients replace the typed prefix, so the
                # full identifier must be inserted instead.
                "insert_text": c.name,
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
        payload = _resolve_spills(payload)
        kind = payload[0]
        if kind == "analysis":
            _, request_id, source, config, theme_name = payload
            return _handle_analysis(request_id, source, config, theme_name)
        if kind == "c_analysis":
            _, request_id, source, file_path, config, theme_name = payload
            return _handle_c_analysis(
                request_id, source, file_path, config, theme_name
            )
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
