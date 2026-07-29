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

import html as _html
import keyword
import logging
import re
from typing import Optional, Tuple

try:
    from editor.Ironica.language_engine import BaseLanguageProvider
except ImportError:
    # Fallback stub when running outside the editor context (e.g. standalone tests).
    from abc import ABC, abstractmethod

    class BaseLanguageProvider(ABC):
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


# ------------------------------------------------------------------
# Hover formatting (language-specific, lives in the plugin)
# ------------------------------------------------------------------


def _clean_docstring(docstring: str) -> str:
    """Strip common leading indentation from a docstring."""
    lines = docstring.expandtabs(4).splitlines()
    if not lines:
        return ""

    margin = 99999
    for line in lines[1:]:
        content = len(line) - len(line.lstrip())
        if line.strip() and content < margin:
            margin = content

    trimmed = [lines[0].strip()]
    if margin < 99999:
        for line in lines[1:]:
            trimmed.append(line[margin:].rstrip())

    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    while trimmed and not trimmed[-1]:
        trimmed.pop()

    return "\n".join(trimmed)


def _format_qt_tooltip(details: HoverDetails) -> str:
    """Minimal HTML4 subset safe for ``QToolTip.showText()``.

    Qt's tooltip renderer only supports ``<b>``, ``<i>``, ``<u>``,
    ``<font>``, ``<br>``, ``<p>``, and ``<table>``/``<tr>``/``<td>``.
    """
    parts = []

    kind_label = _html.escape(details.kind.upper() if details.kind else "SYMBOL")
    name_esc = _html.escape(details.name)
    parts.append(
        f'<b style="color:#569CD6;">{name_esc}</b>'
        f' <font style="color:#888888;">({kind_label})</font>'
    )

    sig_esc = (
        _html.escape(details.signature)
        .replace("\n", "<br/>")
        .replace("  ", "&nbsp;&nbsp;")
    )
    parts.append(
        '<table style="margin-top:4px;" cellspacing="0" cellpadding="4">'
        "<tr>"
        f'<td style="background-color:#1E1E1E; color:#D4D4D4; '
        f'font-family:monospace; font-size:12px;">'
        f"{sig_esc}"
        "</td>"
        "</tr>"
        "</table>"
    )

    if details.parameters:
        parts.append("<br/><b>Parameters:</b>")
        for param in details.parameters:
            p_name = _html.escape(param.name)
            line = f"<br/>&nbsp;&nbsp;&#8226;&nbsp;<b>{p_name}</b>"
            if param.type_hint:
                line += (
                    f' <font color="#4EC9B0;">'
                    f"{_html.escape(param.type_hint)}</font>"
                )
            if param.default_value is not None:
                line += (
                    f' = <font color="#B5CEA8">'
                    f"{_html.escape(param.default_value)}</font>"
                )
            parts.append(line)

    if details.return_type:
        ret_esc = _html.escape(details.return_type)
        parts.append(
            f'<br/><b>Returns:</b> <font color="#4EC9B0;">{ret_esc}</font>'
        )

    if details.docstring:
        cleaned = _clean_docstring(details.docstring)
        doc_esc = _html.escape(cleaned).replace("\n", "<br/>")
        parts.append(
            '<br/><font color="#555555">──────────────────────</font><br/>'
        )
        parts.append(
            f'<font style="color:#A9A9A9; font-style:italic;">' f"{doc_esc}</font>"
        )

    return "".join(parts)


def _format_hover_html(details: HoverDetails) -> str:
    """Rich HTML suitable for ``QTextBrowser`` or ``QLabel`` with rich-text."""
    parts = []

    kind_label = _html.escape(details.kind.upper() if details.kind else "SYMBOL")
    name_esc = _html.escape(details.name)
    parts.append(
        f'<p style="margin:0;">'
        f'<b style="color:#569CD6; font-size:14px;">{name_esc}</b>'
        f' <span style="color:#888888; font-size:12px;">({kind_label})</span>'
        f"</p>"
    )

    sig_esc = _html.escape(details.signature)
    parts.append(
        '<table style="margin:4px 0;" cellspacing="0" cellpadding="6" '
        'width="100%">'
        "<tr>"
        f'<td style="background-color:#1E1E1E; color:#D4D4D4; '
        f'font-family:monospace; font-size:12px; border-radius:4px;">'
        f'<pre style="margin:0; white-space:pre-wrap;">{sig_esc}</pre>'
        "</td>"
        "</tr>"
        "</table>"
    )

    if details.parameters:
        parts.append('<p style="margin:8px 0 4px 0;"><b>Parameters:</b></p>')
        parts.append('<table style="margin:0;" cellspacing="0" cellpadding="2">')
        for param in details.parameters:
            p_name = _html.escape(param.name)
            cells = f'<td style="padding-right:8px;"><b style="color:#9CDCFE;">{p_name}</b></td>'
            if param.type_hint:
                cells += (
                    f'<td style="padding-right:8px;">'
                    f'<font color="#4EC9B0;">'
                    f"{_html.escape(param.type_hint)}</font></td>"
                )
            else:
                cells += "<td></td>"
            if param.default_value is not None:
                cells += (
                    f'<td><font color="#B5CEA8">'
                    f"= {_html.escape(param.default_value)}</font></td>"
                )
            parts.append(f"<tr>{cells}</tr>")
        parts.append("</table>")

    if details.return_type:
        ret_esc = _html.escape(details.return_type)
        parts.append(
            f'<p style="margin:8px 0 4px 0;"><b>Returns:</b> '
            f'<font color="#4EC9B0;">{ret_esc}</font></p>'
        )

    if details.docstring:
        cleaned = _clean_docstring(details.docstring)
        doc_esc = _html.escape(cleaned).replace("\n", "<br/>")
        parts.append(
            '<hr style="border:0; border-top:1px solid #444444; ' 'margin:8px 0;"/>'
        )
        parts.append(
            f'<p style="color:#A9A9A9; font-style:italic;">' f"{doc_esc}</p>"
        )

    return "\n".join(parts)


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

    def get_hover_hint(self, text: str, line: int, col: int) -> Optional[str]:
        if not text:
            return None

        hover_details = self.get_hover_details(text, line, col)
        if not hover_details:
            return None

        return _format_qt_tooltip(hover_details)

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

    def get_hover_display(
        self, text: str, line: int, col: int
    ) -> Optional[tuple]:
        """Return ``(title_html, body_html)`` for the DocumentationFlyout."""
        details = self.get_hover_details(text, line, col)
        if not details:
            return None

        kind_str = f"<i>({details.kind})</i>" if details.kind else ""
        title_html = (
            f'<span style="font-weight:bold; font-size:13px;">{details.name}</span> '
            f'<span style="color:#888888; font-style:italic;">{kind_str}</span>'
        )
        body_html = _format_hover_html(details)
        return title_html, body_html

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


