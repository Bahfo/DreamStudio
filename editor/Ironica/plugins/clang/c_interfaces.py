"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Abstract interface for the C/C++ language support system.
All editor features depend on these interfaces, never concrete libclang bindings.
"""

from typing import List, Optional
from abc import ABC, abstractmethod
from editor.Ironica.plugins.clang.clang_domain_models import *


class IClangAdapter(ABC):
    """
    Abstract bridge isolating the IDE from raw libclang C-API data
    structures.
    """

    @abstractmethod
    def get_hover(self, context: CContext) -> Optional[HoverDetails]:
        """
        Retrieves symbol type, function signature, and Doxygen comments
        at the cursor location.
        """
        pass

    @abstractmethod
    def get_definition(self, context: CContext) -> Optional[DefinitionLocation]:
        """
        Locates the declaration or definition source position of the
        symbol under the cursor.
        """
        pass

    @abstractmethod
    def get_completions(self, context: CContext) -> List[CompletionDetails]:
        """
        Returns code-completion candidates (functions, structs, macros, variables)
        at the cursor.
        """
        pass

    @abstractmethod
    def get_diagnostics(self, context: CContext) -> List[CDiagnostic]:
        """
        Parses C source code and returns compiler syntax errors and warnings.
        """
        pass
