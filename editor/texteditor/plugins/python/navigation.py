"""
Service implementations for code navigation and cross-reference searches.
Completely decoupled from Jedi implementation details.
"""

from typing import List, Optional
from .domain_models import PythonContext, DefinitionLocation, ReferenceLocation
from .interfaces import INavigationService, IReferenceFinderService, IJediAdapter


class NavigationService(INavigationService):
    """
    Stateless service providing target definition calculations.
    """

    def __init__(self, adapter: IJediAdapter) -> None:
        self._adapter = adapter

    def navigate_to_definition(
        self, context: PythonContext
    ) -> Optional[DefinitionLocation]:
        """Delegates work directly to the adapter layer safely."""
        return self._adapter.get_definition(context)


class ReferenceFinderService(IReferenceFinderService):
    """
    Stateless service searching for symbol references across open context.
    """

    def __init__(self, adapter: IJediAdapter) -> None:
        self._adapter = adapter

    def find_all_references(self, context: PythonContext) -> List[ReferenceLocation]:
        """Retrieves and filters references from the injected adapter."""
        return self._adapter.get_references(context)
