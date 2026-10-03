"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Single spill/resolve implementation for analysis wire protocol.
"""

import itertools
import logging
import os
import threading

logger = logging.getLogger(__name__)

_SPILL_THRESHOLD_BYTES = 1_000_000
_spill_counter = itertools.count()
_spill_lock = threading.Lock()


def _spill_dir() -> str:
    """Return temp directory for spilled sources."""
    import tempfile

    path = os.path.join(tempfile.gettempdir(), "dreamstudio_analysis")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def spill_large_strings(payload):
    """Replace oversized top-level strings with file refs."""
    packed = []
    spilled: list = []
    for item in payload:
        if isinstance(item, str) and len(item) >= _SPILL_THRESHOLD_BYTES // 3:
            with _spill_lock:
                number = next(_spill_counter)
            path = os.path.join(_spill_dir(), f"src-{os.getpid()}-{number}.txt")
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(item)
            except OSError as exc:
                logger.debug("Source spill failed, sending inline: %s", exc)
                packed.append(item)
                continue
            spilled.append(path)
            packed.append({"__spilled_source__": path})
        else:
            packed.append(item)
    return type(payload)(packed), spilled


def resolve_spills(payload):
    """Restore spilled file refs to source strings."""
    resolved = []
    for item in payload:
        if isinstance(item, dict) and "__spilled_source__" in item:
            try:
                with open(item["__spilled_source__"], "r", encoding="utf-8") as handle:
                    resolved.append(handle.read())
            except OSError as exc:
                logger.warning("Missing spilled source: %s", exc)
                resolved.append("")
        else:
            resolved.append(item)
    return type(payload)(resolved)


def discard_spills(spilled) -> None:
    """Remove temporary spill files."""
    for path in spilled or []:
        try:
            os.unlink(path)
        except OSError:
            pass
