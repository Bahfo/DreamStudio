"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Size-adaptive debounce delays for large-file analysis.

Small buffers keep snappy base delays; huge buffers back off linearly
so whole-document work (semantic highlights, folds, diagnostics) fires
less often instead of queueing overlapping full-buffer computations.
"""

from __future__ import annotations

from typing import Any


def adaptive_delay_ms(
    base_ms: int,
    line_count: int,
    step_lines: int = 10000,
    step_ms: int = 50,
    max_extra_ms: int = 500,
) -> int:
    """Scale *base_ms* with the buffer size.

    Args:
        base_ms: Delay used for small buffers.
        line_count: Number of lines in the buffer.
        step_lines: Lines per backoff step.
        step_ms: Extra milliseconds per step.
        max_extra_ms: Cap for the size-based extra delay.

    Returns:
        Effective debounce delay in milliseconds.
    """
    if line_count <= 0:
        return base_ms
    extra = min(max_extra_ms, (line_count // step_lines) * step_ms)
    return base_ms + extra


def line_count_of(editor: Any) -> int:
    """Return the document line count without copying the buffer.

    Args:
        editor: Editor widget, preferably exposing QScintilla ``lines()``.

    Returns:
        Line count, or ``0`` when it cannot be determined cheaply.
    """
    try:
        lines = editor.lines()
        return int(lines)
    except Exception:
        return 0


def adaptive_delay_for_editor(base_ms: int, editor: Any) -> int:
    """Return the debounce delay for *editor* based on its size.

    Args:
        base_ms: Delay used for small buffers.
        editor: Editor widget to size the delay for.

    Returns:
        Effective debounce delay in milliseconds.
    """
    return adaptive_delay_ms(base_ms, line_count_of(editor))


def adaptive_delay_for_cost(
    base_ms: int,
    editor: Any,
    cost_ms: float = 0.0,
    cap_extra_ms: int = 400,
) -> int:
    """Return the debounce delay scaled by buffer size and query cost.

    Slow translation units back the delay off so keystrokes stop queuing
    full queries that latest-wins discards anyway. The cost term decays
    on its own (the EMA behind *cost_ms* drops on fast queries), so
    fixing flags or a PCH landing re-snappens the delay automatically.

    Args:
        base_ms: Delay used for small buffers and cheap queries.
        editor: Editor widget to size the delay for.
        cost_ms: Smoothed parse+complete cost in milliseconds.
        cap_extra_ms: Cap for the cost-based extra delay.

    Returns:
        Effective debounce delay in milliseconds.
    """
    delay = adaptive_delay_for_editor(base_ms, editor)
    try:
        cost = float(cost_ms or 0.0)
    except (TypeError, ValueError):
        return delay
    if cost >= 1000.0:
        extra = 300
    elif cost >= 200.0:
        extra = 150
    else:
        extra = 0
    return delay + min(extra, max(0, int(cap_extra_ms)))
