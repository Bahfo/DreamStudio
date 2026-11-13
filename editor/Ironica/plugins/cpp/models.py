"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.
Domain models for C++ Plugin.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class CppContext:
    """
    Completion request snapshot.
    """

    source_code: str
    line: int
    col: int
    file_path: str | None = None
    compile_args: list[str] = field(default_factory=list)
    prefix: str = ""


@dataclass(frozen=True)
class CppCompletion:
    """One completion row offered to the editor popup."""

    text: str
    insert_text: str = ""
    kind: str = "text"
    signature: str = ""


@dataclass(frozen=True)
class CppHoverDetails:
    """
    Rich documentation details for C++ hover tooltips.
    Mirrors Python's HoverDetails for unified UI rendering.
    """

    name: str
    kind: str
    signature: str
    parameters: list[str] = field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
