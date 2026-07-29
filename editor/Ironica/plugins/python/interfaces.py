"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Abstract interface for the Python language support system.
All editor features must depend on these interfaces, never concrete
implementations.
"""

from .domain_models import *
from typing import List, Optional
from abc import ABC, abstractmethod


class IJediAdapter(ABC):
    """
    An abstract class bridge isolation interface.
    Implementations must translate raw jedi objects and exceptions into
    stable domain models.
    """

    @abstractmethod
    def get_hover(self, context: PythonContext) -> Optional[HoverDetails]:
        """
        Retrieves hovering signature and docstring information for the cursor location.
        Returns None if no symbol is under the cursor or if resolving fails.
        """
        pass

    @abstractmethod
    def get_definition(self, context: PythonContext) -> Optional[DefinitionLocation]:
        """
        Locates the definition file and position coordinates of the symbol under the cursor.
        Returns None if the definition cannot be tracked or resolved.
        """
        pass


class IComplexityService(ABC):
    """Parses files to analyze code quality metrics without execution."""

    @abstractmethod
    def analyze_source(self, source_code: str) -> ComplexityReport:
        """Parses source code into an AST and extracts complex code paths."""
        pass
