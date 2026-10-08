"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Domain models for C++ Plugin.
"""

from __future__ import annotations
from dataclasses import dataclass, field


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
    text: str
    insert_text: str = ""
    kind: str = "text"
    signature: str = ""
