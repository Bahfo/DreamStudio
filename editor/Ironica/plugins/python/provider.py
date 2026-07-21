"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Stateless PythonLanguageProvider bridging the editor UI expectations to the Jedi
isolation adapter.
Implements the abstract BaseLanguageProvider required by the editor core.

**Coordinate System:**

The editor uses 0-indexed line numbers.  Jedi uses 1-indexed lines and
0-indexed columns.  This provider translates between the two so that
neither the editor nor the adapter needs to know about the other's
coordinate convention.
"""

import keyword
import logging
import re
from typing import List, Optional, Tuple

try:
    from editor.Ironica.language_engine import BaseLanguageProvider
except ImportError:
    # Fallback stub when running outside the editor context (e.g. standalone tests).
    from abc import ABC, abstractmethod

    class BaseLanguageProvider(ABC):
        @abstractmethod
        def get_auto_completions(self, text: str, line: int, col: int) -> List[str]:
            return []

        @abstractmethod
        def get_hover_hint(self, text: str, line: int, col: int) -> Optional[str]:
            return None

        @abstractmethod
        def get_definition_location(
            self, text: str, line: int, col: int
        ) -> Optional[Tuple[Optional[str], int, int]]:
            return None

        @abstractmethod
        def format_source(self, source_code: str) -> str:
            return source_code


from .domain_models import PythonContext
from .interfaces import IJediAdapter
from .cache import LanguageCache
from .hover_presenter import HoverPresenter

logger = logging.getLogger("DreamStudio.PythonSupport.Provider")


def _is_inside_string(line_text: str, col: int) -> bool:
    """Return ``True`` if *col* falls inside a string literal on *line_text*.

    Handles single-quoted, double-quoted, and triple-quoted strings.
    This is a best-effort check without a full tokenizer — it handles
    the common cases that cause spurious hover popups.
    """
    i = 0
    n = len(line_text)
    while i < n:
        ch = line_text[i]
        if ch in ("'", '"'):
            quote = ch * 3 if line_text[i : i + 3] == ch * 3 else ch
            q_len = len(quote)
            if i <= col < i + q_len:
                return True
            end = line_text.find(quote, i + q_len)
            if end == -1:
                # Unclosed string — everything to the right is inside it.
                return col >= i
            if i + q_len <= col <= end:
                return True
            i = end + q_len
        elif ch == "#":
            # Comment — stop scanning (nothing after it is a string).
            break
        else:
            i += 1
    return False


class PythonLanguageProvider(BaseLanguageProvider):
    """
    Stateless provider.  This handles coordinate transformations and caching,
    while delegating source code analysis tasks entirely to an IJediAdapter.

    **Coordinate translation:** The editor passes 0-indexed lines.  Jedi
    expects 1-indexed lines.  Every ``_build_context`` call converts
    ``editor_line`` to ``jedi_line = editor_line + 1``.
    """

    def __init__(
        self,
        adapter: IJediAdapter,
        cache: Optional[LanguageCache] = None,
        file_path: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._adapter = adapter
        self._cache = cache if cache is not None else LanguageCache()
        self._file_path = file_path

    # ------------------------------------------------------------------
    # Public property for file_path (allows the integration layer to
    # set it when an editor tab is focused).
    # ------------------------------------------------------------------

    @property
    def file_path(self) -> Optional[str]:
        """Return the currently active file path, if known."""
        return self._file_path

    @file_path.setter
    def file_path(self, value: Optional[str]) -> None:
        self._file_path = value

    # ------------------------------------------------------------------
    # Context translation
    # ------------------------------------------------------------------

    def _build_context(
        self, text: str, line: int, col: int, file_path: Optional[str] = None
    ) -> PythonContext:
        """Build an immutable ``PythonContext`` with correct coordinates.

        Converts the editor's 0-indexed line to Jedi's 1-indexed line.
        Columns are already 0-indexed in both systems.
        """
        effective_path = file_path or self._file_path
        return PythonContext(
            source_code=text,
            line=line + 1,
            column=col,
            file_path=effective_path,
        )

    # ------------------------------------------------------------------
    # BaseLanguageProvider contract
    # ------------------------------------------------------------------

    def get_auto_completions(self, text: str, line: int, col: int) -> List[str]:
        """Return completion strings for the cursor position.

        Args:
            text: Full buffer content.
            line: 0-indexed cursor line (editor convention).
            col: 0-indexed cursor column.
        """
        if not text:
            return []

        context = self._build_context(text, line, col)

        cached_result = self._cache.get(context, "completions")
        if cached_result is not None:
            return cached_result

        items = self._adapter.get_completions(context)
        completions_list = [item.label for item in items]

        self._cache.set(context, "completions", completions_list)
        return completions_list

    def get_hover_hint(self, text: str, line: int, col: int) -> Optional[str]:
        """Return a Qt-tooltip-compatible HTML string for the symbol under the cursor.

        Uses ``HoverPresenter.to_qt_tooltip()`` which produces HTML safe
        for ``QToolTip.showText()`` -- only ``<b>``, ``<i>``, ``<font>``,
        ``<br>``, ``<table>`` tags with inline CSS.

        Returns ``None`` for Python keywords (``if``, ``def``, ``class``,
        etc.) since they carry no useful documentation.
        """
        if not text:
            return None

        symbol = self._symbol_at(text, line, col)
        if not symbol:
            return None
        if keyword.iskeyword(symbol):
            return None

        context = self._build_context(text, line, col)

        cached_result = self._cache.get(context, "hover")
        if cached_result is not None:
            return cached_result

        hover_details = self._adapter.get_hover(context)
        if not hover_details:
            return None

        formatted_hint = HoverPresenter.to_qt_tooltip(hover_details)

        self._cache.set(context, "hover", formatted_hint)
        return formatted_hint

    @staticmethod
    def _symbol_at(text: str, line: int, col: int) -> Optional[str]:
        """Extract the word under the cursor at (*line*, *col*).

        Returns ``None`` if the cursor is not over a valid identifier
        or if it is inside a string literal.
        """
        lines = text.split("\n")
        if line < 0 or line >= len(lines):
            return None
        row = lines[line]
        if col < 0 or col > len(row):
            return None

        # Check if the cursor is inside a string literal (single, double,
        # or triple-quoted) by scanning for unescaped quote characters.
        if _is_inside_string(row, col):
            return None

        for match in re.finditer(r"[A-Za-z_]\w*", row):
            if match.start() <= col < match.end():
                return match.group(0)
        return None

    def get_hover_html(self, text: str, line: int, col: int) -> Optional[str]:
        """Return an HTML string for rich hover tooltip rendering.

        This is an extension beyond the ``BaseLanguageProvider`` contract,
        used by the integration layer for Qt rich-text tooltips.
        Returns ``None`` for Python keywords.
        """
        if not text:
            return None

        symbol = self._symbol_at(text, line, col)
        if not symbol:
            return None
        if keyword.iskeyword(symbol):
            return None

        context = self._build_context(text, line, col)

        hover_details = self._adapter.get_hover(context)
        if not hover_details:
            return None

        return HoverPresenter.to_html(hover_details)

    def get_definition_location(
        self, text: str, line: int, col: int
    ) -> Optional[Tuple[str, int, int]]:
        """Return ``(file_path, line, col)`` for the symbol's definition.

        Lines are returned as 1-indexed from Jedi.  The editor's
        ``open_file_at_line`` will use this directly.

        All values are严格ly typed: ``str``, ``int``, ``int``.
        This prevents segmentation faults in the C++ QScintilla backend.
        """
        context = self._build_context(text, line, col)

        cached_result = self._cache.get(context, "definition")
        if cached_result is not None:
            return cached_result

        location = self._adapter.get_definition(context)
        if not location:
            return None

        result = (
            str(location.file_path) if location.file_path else "",
            int(location.line),
            int(location.column),
        )
        self._cache.set(context, "definition", result)
        return result

    def format_source(self, source_code: str) -> str:
        """Pass-through.  Formatting is handled externally."""
        return source_code

    def get_semantic_highlights(self, text: str):
        """Return colour ranges for Python semantic tokens.

        Delegates to :func:`semantic_highlights.get_semantic_highlights`
        which uses the ``ast`` module for reliable detection of imports,
        function parameters, and variable definitions.
        """
        from .semantic_highlights import get_semantic_highlights

        return get_semantic_highlights(text)

    # ------------------------------------------------------------------
    # Extended plugin services (not in BaseLanguageProvider contract,
    # used by the integration layer).
    # ------------------------------------------------------------------

    def get_references(
        self, text: str, line: int, col: int, file_path: Optional[str] = None
    ):
        """Find all references to the symbol at the cursor position.

        Returns a list of ``ReferenceLocation`` domain models.
        """
        context = self._build_context(text, line, col, file_path)
        try:
            return self._adapter.get_references(context)
        except Exception as exc:
            logger.error("Failed to find references: %s", exc)
            return []

    def get_rename_changes(
        self,
        text: str,
        line: int,
        col: int,
        new_name: str,
        file_path: Optional[str] = None,
    ):
        """Calculate rename refactoring changes.

        Returns a list of ``RefactorChange`` domain models.
        """
        context = self._build_context(text, line, col, file_path)
        try:
            return self._adapter.get_rename_changes(context, new_name)
        except Exception as exc:
            logger.error("Failed to compute rename changes: %s", exc)
            return []

    def get_complexity(self, source_code: str):
        """Analyze source code complexity.

        Returns a ``ComplexityReport`` domain model.
        """
        try:
            from .complexity import ComplexityAnalysisService

            service = ComplexityAnalysisService()
            return service.analyze_source(source_code)
        except Exception as exc:
            logger.error("Failed to analyze complexity: %s", exc)
            return None
