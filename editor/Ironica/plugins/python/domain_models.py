"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Domain models and context definitions for the DreamStudio Python language support system.
"""

import dataclasses
from typing import List, Optional

@dataclasses.dataclass
class PythonContext:
    """An immutable snapshot of the editor's state at the moment of a request."""

    source_code: str
    line: int
    column: int
    file_path: Optional[str] = None
    project_root: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ParameterInfo:
    """
    Represents a single parameter of a function or method signature.
    """

    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class HoverDetails:
    """
    Rich documentation details for hover tooltips, separated from GUI rendering.
    """

    name: str
    kind: str
    signature: str
    parameters: List[ParameterInfo] = dataclasses.field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class DefinitionLocation:
    """
    Target location details for GoTo Definition and Find References requests.
    """

    file_path: Optional[str]
    line: int
    column: int
    context_line: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ReferenceLocation:
    """Represents an occurrence of a symbol somewhere in the codebase."""

    file_path: Optional[str]
    line: int  # 1-based index
    column: int  # 0-based index
    context_line: str  # The line of source code containing the reference
    symbol_length: int  # Width of the symbol for code highlighting


@dataclasses.dataclass(frozen=True)
class CompletionDetails:
    """One autocompletion suggestion from the language plugin."""

    text: str
    insert_text: str = ""
    kind: str = ""
    signature: str = ""
