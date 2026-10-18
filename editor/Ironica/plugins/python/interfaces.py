"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Abstract interface for the Python language support system.
All editor features must depend on these interfaces, never concrete
implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .domain_models import (
    CompletionDetails,
    DefinitionLocation,
    HoverDetails,
    PythonContext,
)

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

    @abstractmethod
    def get_completions(self, context: PythonContext) -> List["CompletionDetails"]:
        """Return code-completion suggestions at the cursor position.

        Args:
            context: Immutable snapshot of the editor state.

        Returns:
            A list of ``CompletionDetails`` objects.  May be empty when
            no completions are available.
        """
        pass
