"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Size-adaptive debounce delays for large-file analysis.
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
    """Scale *base_ms* with the buffer size."""
    if line_count <= 0:
        return base_ms
    extra = min(max_extra_ms, (line_count // step_lines) * step_ms)
    return base_ms + extra


def line_count_of(editor: Any) -> int:
    """Return the document line count without copying the buffer."""
    try:
        lines = editor.lines()
        return int(lines)
    except Exception:
        return 0


def adaptive_delay_for_editor(base_ms: int, editor: Any) -> int:
    """Return the debounce delay for *editor* based on its size."""
    return adaptive_delay_ms(base_ms, line_count_of(editor))


def adaptive_delay_for_cost(
    base_ms: int,
    editor: Any,
    cost_ms: float = 0.0,
    cap_extra_ms: int = 400,
) -> int:
    """Return the debounce delay scaled by buffer size and query cost."""
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
