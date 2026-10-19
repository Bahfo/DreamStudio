"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Completion pipeline timing marks for latency diagnosis.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional

logger = logging.getLogger("DreamStudio.CompletionProfile")

_FLAG = "DS_COMPLETION_PROFILE"

_marks: Dict[int, List[tuple]] = {}
_notes: Dict[int, List[str]] = {}


def enabled() -> bool:
    """Return whether profiling marks are recorded."""
    return bool(os.environ.get(_FLAG))


def mark(owner: object, stage: str) -> None:
    """Record a monotonic timestamp for (*owner*, *stage*)."""
    if not enabled():
        return
    try:
        store = _marks.setdefault(id(owner), [])
        store.append((stage, time.perf_counter_ns()))
    except Exception:
        pass


def report(owner: object) -> Optional[str]:
    """Format recorded stages for *owner* as a relative-timing line."""
    if not enabled():
        return None
    store: List[tuple] = _marks.get(id(owner), [])
    if len(store) < 2:
        return None
    base = store[0][1]
    parts = [f"{stage}=+{(stamp - base) / 1e6:.1f}ms"
             for stage, stamp in store]
    parts.extend(_notes.get(id(owner), []))
    return " ".join(parts)


def log_report(owner: object, label: str) -> None:
    """Emit the timing line for *owner* at debug level when enabled."""
    if not enabled():
        return
    line = report(owner)
    if line:
        logger.debug("%s: %s", label, line)


def reset(owner: object) -> None:
    """Drop recorded stages for *owner*."""
    _marks.pop(id(owner), None)
    _notes.pop(id(owner), None)


def note(owner: object, message: str) -> None:
    """Attach a free-form note (e.g."""
    if not enabled():
        return
    try:
        _notes.setdefault(id(owner), []).append(str(message))
    except Exception:
        pass
