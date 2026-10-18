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
    """One completion row offered to the editor popup.

    Attributes:
        text: Identifier shown and matched against the typed prefix.
        insert_text: Text actually inserted on acceptance. Defaults to
            empty so callers that omit it get a row that inserts nothing
            rather than a silent duplicate of ``text``.
        kind: Icon/metadata category (``method``, ``function``, ``path``…).
            Drives the popup icon and completion ranking.
        signature: Right-hand detail text; for callables this is the
            rendered parameter list.
    """

    text: str
    insert_text: str = ""
    kind: str = "text"
    signature: str = ""
