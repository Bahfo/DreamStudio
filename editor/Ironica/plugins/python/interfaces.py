"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Abstract interface for the Python language support system.
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
    """An abstract class bridge isolation interface."""

    @abstractmethod
    def get_hover(self, context: PythonContext) -> Optional[HoverDetails]:
        """Retrieves hovering signature and docstring information for the cursor location."""
        pass

    @abstractmethod
    def get_definition(self, context: PythonContext) -> Optional[DefinitionLocation]:
        """Locates the definition file and position coordinates of the symbol under the cursor."""
        pass

    @abstractmethod
    def get_completions(self, context: PythonContext) -> List["CompletionDetails"]:
        """Return code-completion suggestions at the cursor position."""
        pass
