"""
Service implementation managing code structure and symbol transformations.
"""

from typing import List
from .domain_models import PythonContext, RefactorChange
from .interfaces import IRefactoringService, IJediAdapter


class RenameRefactoringService(IRefactoringService):
    """
    Stateless controller for renaming execution.
    """

    def __init__(self, adapter: IJediAdapter) -> None:
        self._adapter = adapter

    def rename_symbol(
        self, context: PythonContext, new_name: str
    ) -> List[RefactorChange]:
        """Delegates rename tracking directly to the adapter boundary."""
        if not new_name.isidentifier():
            return []  # Gracefully ignore invalid identifier names
        return self._adapter.get_rename_changes(context, new_name)
