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


from .domain_models import PythonContext, HoverDetails
from .interfaces import IJediAdapter
from .cache import LanguageCache
from .hover_presenter import HoverPresenter

logger = logging.getLogger("DreamStudio.PythonSupport.Provider")


def _is_inside_string(line_text: str, col: int) -> bool:
    """Return ``True`` if *col* falls inside a string literal on *line_text*."""
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
                return col >= i
            if i + q_len <= col <= end:
                return True
            i = end + q_len
        elif ch == "#":
            break
        else:
            i += 1
    return False


class PythonLanguageProvider(BaseLanguageProvider):
    """
    Stateless provider. Handles coordinate transformations and caching,
    delegating source code analysis tasks entirely to an IJediAdapter.
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

    @property
    def file_path(self) -> Optional[str]:
        return self._file_path

    @file_path.setter
    def file_path(self, value: Optional[str]) -> None:
        self._file_path = value

    # ------------------------------------------------------------------
    # Provider Initialization & UI Setup Helper
    # ------------------------------------------------------------------

    def setup_hover_engine(self, editor) -> Tuple[object, object]:
        """
        Instantiates and wires up DocumentationFlyout and HoverController
        directly onto the target editor instance.
        """
        from editor.Ironica.utils.documentation_flayout import DocumentationFlyout
        from editor.Ironica.utils.hover_controller import HoverController

        flyout = DocumentationFlyout(parent=editor)
        controller = HoverController(editor=editor, flyout=flyout, provider=self)

        # Wire Jump-To-Declaration toolbar action
        flyout.jump_to_source_requested.connect(
            lambda: self._handle_flyout_jump(editor, controller)
        )

        return flyout, controller

    def _handle_flyout_jump(self, editor, controller) -> None:
        """Handle definition jump triggered from the flyout toolbar."""
        controller.flyout.dismiss(force=True)
        line = controller._target_line
        col = controller._target_col
        text = editor.text()

        if line >= 0 and col >= 0:
            loc = self.get_definition_location(text, line, col)
            if loc and loc[0]:
                file_path, target_line, target_col = loc
                if hasattr(editor, "open_file_at_line"):
                    editor.open_file_at_line(file_path, target_line, target_col)
                else:
                    editor.setCursorPosition(target_line, target_col)
                    editor.ensureLineVisible(target_line)

    # ------------------------------------------------------------------
    # Context translation
    # ------------------------------------------------------------------

    def _build_context(
        self, text: str, line: int, col: int, file_path: Optional[str] = None
    ) -> PythonContext:
        effective_path = file_path or self._file_path
        return PythonContext(
            source_code=text,
            line=line + 1,
            column=col,
            file_path=effective_path,
        )

    # ------------------------------------------------------------------
    # Domain Hover Support
    # ------------------------------------------------------------------

    def get_hover_details(
        self, text: str, line: int, col: int
    ) -> Optional[HoverDetails]:
        """Return raw HoverDetails domain model for structured UI rendering."""
        if not text:
            return None

        symbol = self._symbol_at(text, line, col)
        if not symbol or keyword.iskeyword(symbol):
            return None

        context = self._build_context(text, line, col)
        return self._adapter.get_hover(context)

    def get_auto_completions(self, text: str, line: int, col: int) -> List[str]:
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
        if not text:
            return None

        hover_details = self.get_hover_details(text, line, col)
        if not hover_details:
            return None

        return HoverPresenter.to_qt_tooltip(hover_details)

    @staticmethod
    def _symbol_at(text: str, line: int, col: int) -> Optional[str]:
        lines = text.split("\n")
        if line < 0 or line >= len(lines):
            return None
        row = lines[line]
        if col < 0 or col > len(row):
            return None

        if _is_inside_string(row, col):
            return None

        for match in re.finditer(r"[A-Za-z_]\w*", row):
            if match.start() <= col < match.end():
                return match.group(0)
        return None

    def get_hover_html(self, text: str, line: int, col: int) -> Optional[str]:
        if not text:
            return None

        hover_details = self.get_hover_details(text, line, col)
        if not hover_details:
            return None

        return HoverPresenter.to_html(hover_details)

    def get_definition_location(
        self, text: str, line: int, col: int
    ) -> Optional[Tuple[str, int, int]]:
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
        return source_code

    def get_semantic_highlights(self, text: str):
        from .semantic_highlights import get_semantic_highlights

        return get_semantic_highlights(text)

    # ------------------------------------------------------------------
    # Extended plugin services
    # ------------------------------------------------------------------

    def get_references(
        self, text: str, line: int, col: int, file_path: Optional[str] = None
    ):
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
        context = self._build_context(text, line, col, file_path)
        try:
            return self._adapter.get_rename_changes(context, new_name)
        except Exception as exc:
            logger.error("Failed to compute rename changes: %s", exc)
            return []

    def get_complexity(self, source_code: str):
        try:
            from .complexity import ComplexityAnalysisService

            service = ComplexityAnalysisService()
            return service.analyze_source(source_code)
        except Exception as exc:
            logger.error("Failed to analyze complexity: %s", exc)
            return None
