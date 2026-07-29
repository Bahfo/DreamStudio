"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Integration layer bridging the Python plugin domain models to the
editor engine's expectations.  Keeps all Qt/GUI concerns out of the
provider and adapter layers.
"""

import logging
from typing import Optional, Tuple

from .domain_models import (
    PythonContext,
    HoverDetails,
    DefinitionLocation,
)
from .interfaces import IJediAdapter

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds ``PythonContext`` snapshots from raw editor state."""

    @staticmethod
    def from_editor(
        text: str,
        line: int,
        col: int,
        file_path: Optional[str] = None,
    ) -> PythonContext:
        """Create an immutable context from editor parameters.

        Converts the editor's 0-indexed line to Jedi's 1-indexed line.
        """
        return PythonContext(
            source_code=text,
            line=line + 1,
            column=col,
            file_path=file_path,
        )


class ResultTranslator:
    """Translates adapter domain models to editor-expected formats."""

    @staticmethod
    def definition_to_tuple(
        loc: Optional[DefinitionLocation],
    ) -> Optional[Tuple[str, int, int]]:
        """Convert a DefinitionLocation to a strict (file_path, line, col) tuple.

        All numerical values are cast to ``int`` to satisfy the C++ backend's
        type expectations and prevent segmentation faults.
        """
        if loc is None:
            return None
        return (
            str(loc.file_path) if loc.file_path else "",
            int(loc.line),
            int(loc.column),
        )


class PythonIntegrationLayer:
    """High-level facade used by the registration and editor layers.

    Wires together the ``IJediAdapter`` implementation, the ``ContextBuilder``,
    and the ``ResultTranslator`` so that the editor never needs to know about
    Jedi or the plugin's internal domain models.
    """

    def __init__(self, adapter: IJediAdapter) -> None:
        self._adapter = adapter

    @property
    def adapter(self) -> IJediAdapter:
        return self._adapter

    def get_hover(
        self, text: str, line: int, col: int
    ) -> Optional[HoverDetails]:
        """Return rich hover details for the symbol under the cursor."""
        try:
            ctx = ContextBuilder.from_editor(text, line, col)
            return self._adapter.get_hover(ctx)
        except Exception:
            logger.exception("get_hover failed")
            return None

    def get_definition(
        self, text: str, line: int, col: int
    ) -> Optional[Tuple[str, int, int]]:
        """Return a strict (file_path, line, col) tuple for the definition."""
        try:
            ctx = ContextBuilder.from_editor(text, line, col)
            loc = self._adapter.get_definition(ctx)
            return ResultTranslator.definition_to_tuple(loc)
        except Exception:
            logger.exception("get_definition failed")
            return None
