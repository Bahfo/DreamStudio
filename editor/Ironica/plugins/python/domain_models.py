"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Domain models and context definitions for the DreamStudio Python language
support system. These models are completely decoupled from any providers
such as Jedi, Qt, or the filesystem.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class PythonContext:
    """
    An immutable snapshot of the editor's state at the moment of a request.
    This prevents race conditions and keeps language providers stateless.
    """

    source_code: str
    line: int
    column: int
    file_path: Optional[str] = None


@dataclass(frozen=True)
class ParameterInfo:
    """
    Represents a single parameter of a function or method signature.
    """

    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None


@dataclass(frozen=True)
class HoverDetails:
    """
    Rich documentation details for hover tooltips, separated from GUI rendering.
    """

    name: str
    kind: str
    signature: str
    parameters: List[ParameterInfo] = field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None


@dataclass(frozen=True)
class DefinitionLocation:
    """T
    arget location details for GoTo Definition and Find References requests.
    """

    file_path: Optional[str]
    line: int
    column: int
    context_line: Optional[str] = None


@dataclass(frozen=True)
class ReferenceLocation:
    """
    Represents an occurrence of a symbol somewhere in the codebase.
    Used by the reference finder tool to list occurrences.
    """

    file_path: Optional[str]
    line: int  # 1-based index
    column: int  # 0-based index
    context_line: str  # The line of source code containing the reference
    symbol_length: int  # Width of the symbol for code highlighting


@dataclass(frozen=True)
class RefactorChange:
    """
    Represents a proposed file modification during a refactoring task.
    This lets the editor core approve and apply changes to its own buffers.
    """

    file_path: Optional[str]
    new_source_code: str


@dataclass(frozen=True)
class FunctionComplexity:
    """Complexity metrics computed for a specific function/method."""

    name: str
    line: int
    cyclomatic_complexity: int
    nesting_depth: int


@dataclass(frozen=True)
class ComplexityReport:
    """Comprehensive AST complexity metrics for a single source file."""

    total_loc: int
    class_count: int
    function_count: int
    max_cyclomatic_complexity: int
    functions: List[FunctionComplexity] = field(default_factory=list)
