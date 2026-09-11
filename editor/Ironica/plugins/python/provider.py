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

from editor import *

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


from .domain_models import PythonContext, HoverDetails, CompletionDetails
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
        parts.append(f'<br/><b>Returns:</b> <font color="#4EC9B0;">{ret_esc}</font>')

    if details.docstring:
        cleaned = _clean_docstring(details.docstring)
        doc_esc = _html.escape(cleaned).replace("\n", "<br/>")
        parts.append('<br/><font color="#555555">──────────────────────</font><br/>')
        parts.append(
            f'<font style="color:#A9A9A9; font-style:italic;">' f"{doc_esc}</font>"
        )

    return "".join(parts)


def _format_hover_markdown(details: HoverDetails) -> str:
    """Rich Markdown suitable for ``QTextBrowser.setMarkdown()``.

    Qt's Markdown engine renders headings, code fences, bullet lists,
    horizontal rules and tables.  The output deliberately avoids raw HTML
    so the flyout can render it through ``QTextDocument.setMarkdown()``
    using the IDE-controlled stylesheet.
    """
    parts: list[str] = []

    if details.signature:
        sig = details.signature.strip()
        # Use fenced code block; escape triple-backticks inside signature.
        sig = sig.replace("```", "\\`\\`\\`")
        parts.append(f"```python\n{sig}\n```")

    if details.parameters:
        parts.append(f"### Parameters ({len(details.parameters)})")
        for param in details.parameters:
            name = param.name
            type_hint = f"`{param.type_hint}`" if param.type_hint else "`any`"
            if param.default_value is not None:
                parts.append(f"- **{name}** {type_hint} = `{param.default_value}`")
            else:
                parts.append(f"- **{name}** {type_hint}")

    if details.return_type:
        parts.append(f"**Returns:** `{details.return_type}`")

    if details.docstring:
        cleaned = _clean_docstring(details.docstring)
        # Keep docstring as blockquote/italic paragraph; escape not needed
        # because Markdown renders plain text naturally.
        parts.append(f"---\n\n{cleaned}")

    if not parts:
        parts.append("*No additional documentation available.*")

    return "\n\n".join(parts)


class PythonLanguageProvider(BaseLanguageProvider):
    """
    Stateless provider. Handles coordinate transformations and caching,
    delegating source code analysis tasks entirely to an IJediAdapter.
    """

    #: Semantic highlights + folding are computed in a dedicated analysis
    #: subprocess so the GIL never stalls the main thread on large files.
    remote_analysis: bool = True

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
        self._completion_manager = None

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

    def get_hover_display(self, text: str, line: int, col: int) -> Optional[tuple]:
        """Return ``(title_markdown, body_markdown)`` for the DocumentationFlyout.

        The flyout renders both fragments through ``QTextDocument.setMarkdown()``
        so the provider must emit clean Markdown rather than pre-rendered HTML.
        """
        details = self.get_hover_details(text, line, col)
        if not details:
            return None

        # Markdown heading — the flyout strips heading syntax for the header
        # label but keeps the structure for rendering.
        if details.kind:
            title_markdown = f"## {details.name} ({details.kind})"
        else:
            title_markdown = f"## {details.name}"
        body_markdown = _format_hover_markdown(details)
        return title_markdown, body_markdown

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

    # ------------------------------------------------------------------
    # Completion Support
    # ------------------------------------------------------------------

    def get_completions(
        self, text: str, cursor_position: tuple, prefix: str
    ) -> list:
        """Return code-completion suggestions for the editor.

        The signature matches the duck-typed contract expected by
        ``CompletionController`` — the editor never imports plugin
        types, and this method never imports UI types.

        Args:
            text: Full editor buffer content.
            cursor_position: ``(line, col)`` tuple (0-indexed).
            prefix: The identifier prefix the user has typed.

        Returns:
            A list of ``CompletionDetails`` domain objects.
        """
        if not text:
            return []

        line, col = cursor_position
        context = self._build_context(text, line, col)

        try:
            return self._adapter.get_completions(context)
        except Exception as e:
            logger.warning("Completion request failed: %s", e)
            return []

    def format_source(self, source_code: str) -> str:
        """Format *source_code* using black.

        Uses the ``black`` PyPI module installed in the IDE venv.
        Keeps the operation minimalistic — delegates to the existing
        ``CodeEditor.format_current_file`` / right-click ``Format Code``
        flow without adding any new files.

        Args:
            source_code: Raw Python source from the editor buffer.

        Returns:
            Formatted source, or the original text if ``black`` is
            missing or the code has a syntax error.
        """
        if not source_code or not source_code.strip():
            return source_code
        try:
            import black

            mode = black.FileMode(line_length=110)
            return black.format_str(source_code, mode=mode)
        except ImportError:
            logger.debug("black not installed, skipping format")
            return source_code
        except Exception as exc:
            logger.debug("black formatting failed: %s", exc)
            return source_code

    def get_semantic_highlights(self, text: str):
        from .semantic_highlights import get_semantic_highlights

        return get_semantic_highlights(text)

    def invalidate_cache(self) -> None:
        """Drop the semantic-highlight cache so overlay colours follow
        the currently active IDE theme on the next repaint.

        The editor calls this on every ``retheme``; without it the
        cached tokens keep the palette of the theme that was active the
        first time a buffer was highlighted.
        """
        from .semantic_highlights import invalidate_semantic_cache

        invalidate_semantic_cache()

    # ------------------------------------------------------------------
    # Capability flags
    # ------------------------------------------------------------------

    def has_folding(self) -> bool:
        """Return ``True`` — the Python plugin provides fold regions."""
        return True

    def get_fold_regions(self, text: str) -> list:
        """Return fold regions computed from Python source indentation.

        Args:
            text: The full editor buffer content.

        Returns:
            A list of ``FoldRegion`` objects.
        """
        from .folding import compute_fold_regions

        return compute_fold_regions(text)

    def has_diagnostics(self) -> bool:
        """Return ``True`` — the Python plugin provides background diagnostics."""
        return True

    def create_diagnostic_manager(self, editor, file_path, parent):
        """Create a Jedi-backed DiagnosticManager for *editor*.

        Args:
            editor: The ``CodeEditor`` instance.
            file_path: Path to the file on disk.
            parent: Qt parent for the manager's thread.

        Returns:
            A ``DiagnosticManager`` instance.
        """
        from .jedi_worker import DiagnosticManager

        return DiagnosticManager(
            editor=editor, file_path=file_path, parent=parent
        )

    # ------------------------------------------------------------------
    # Outline support
    # ------------------------------------------------------------------

    def has_outline(self) -> bool:
        """Return ``True`` — the Python plugin provides file outlines."""
        return True

    def get_outline(self, source_code: str):
        """Return an outline tree for Python source code.

        Args:
            source_code: Full Python source from the editor buffer.

        Returns:
            An ``OutlineResult`` from the outline backend, or ``None``
            if parsing fails.
        """
        from editor.utils.file_properties.outline import build_outline

        return build_outline(source_code, "python", filename=self._file_path or "")

    @property
    def completion_manager(self):
        """Return the ``CompletionManager`` for this provider, or ``None``."""
        return self._completion_manager

    def create_completion_manager(self, editor, file_path, parent):
        """Create a Jedi-backed CompletionManager for *editor*.

        Args:
            editor: The ``CodeEditor`` instance.
            file_path: Path to the file on disk.
            parent: Qt parent for the manager's thread.

        Returns:
            A ``CompletionManager`` instance.
        """
        from .jedi_worker import CompletionManager

        self._completion_manager = CompletionManager(
            editor=editor, file_path=file_path, parent=parent
        )
        return self._completion_manager

    def post_fold_setup(self, editor, regions) -> None:
        """Apply Python-specific fold display text labels.

        Enables the Scintilla fold display-text feature and tags import
        fold regions with ``( ... +N imports)`` labels.
        """
        from .folding import _apply_import_fold_text

        _apply_import_fold_text(editor, regions)


# ------------------------------------------------------------------
# Factory function (called dynamically by the plugin registration system)
# ------------------------------------------------------------------


def create_provider() -> PythonLanguageProvider:
    """Create and return a fully wired PythonLanguageProvider.

    This factory is invoked by the dynamic plugin registration system
    via ``importlib`` when loading the Python language plugin.

    Returns:
        A ``PythonLanguageProvider`` backed by Jedi.
    """
    from .jedi_adapter import JediAdapter
    from .cache import LanguageCache

    adapter = JediAdapter()
    cache = LanguageCache()
    return PythonLanguageProvider(adapter=adapter, cache=cache)
