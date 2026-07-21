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
    def get_completions(self, context: PythonContext) -> List[CompletionItem]:
        """
        Retrieves completion items for the given context.
        Must catch all internal parser exceptions and return an empty list.
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

    @abstractmethod
    def get_references(self, context: PythonContext) -> List[ReferenceLocation]:
        """
        Locates all referencing positions for the selected symbol.
        Must catch all internal parser exceptions and return an empty list.
        """
        pass

    @abstractmethod
    def get_rename_changes(
        self, context: PythonContext, new_name: str
    ) -> List[RefactorChange]:
        """
        Calculates Jedi refactoring details safely, wrapping all internal Jedi types.
        """
        pass


class INavigationService(ABC):
    """
    Handles tracking definitions of symbols.
    Allows users to jump to the origin source code lines.
    """

    @abstractmethod
    def navigate_to_definition(
        self, context: PythonContext
    ) -> Optional[DefinitionLocation]:
        """Resolves and returns the origin location of the symbol under the cursor."""
        pass


class IReferenceFinderService(ABC):
    """
    Finds all usages of a target symbol across the program scope.
    """

    @abstractmethod
    def find_all_references(self, context: PythonContext) -> List[ReferenceLocation]:
        """Locates all references to the symbol under the cursor."""
        pass


class IRefactoringService(ABC):
    """Handles symbol transformations across the workspace."""

    @abstractmethod
    def rename_symbol(
        self, context: PythonContext, new_name: str
    ) -> List[RefactorChange]:
        """Calculates renaming operations for the symbol under the cursor."""
        pass


class IComplexityService(ABC):
    """Parses files to analyze code quality metrics without execution."""

    @abstractmethod
    def analyze_source(self, source_code: str) -> ComplexityReport:
        """Parses source code into an AST and extracts complex code paths."""
        pass
