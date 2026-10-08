"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Completion pipeline timing marks for latency diagnosis.

Active only when the ``DS_COMPLETION_PROFILE`` environment variable is
set; every call is a no-op otherwise, so instrumented hot paths keep
their steady-state cost at two attribute lookups and one branch.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional

logger = logging.getLogger("DreamStudio.CompletionProfile")

_FLAG = "DS_COMPLETION_PROFILE"

_marks: Dict[int, List[tuple]] = {}


def enabled() -> bool:
    """Return whether profiling marks are recorded."""
    return bool(os.environ.get(_FLAG))


def mark(owner: object, stage: str) -> None:
    """Record a monotonic timestamp for (*owner*, *stage*).

    Args:
        owner: Request owner (manager or controller instance).
        stage: Pipeline stage name (e.g. ``"queue"``, ``"emit"``).
    """
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
