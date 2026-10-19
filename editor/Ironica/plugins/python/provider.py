"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Stateless PythonLanguageProvider bridging the editor UI expectations to the Jedi isolation adapter.
"""

import html as _html
import keyword
import logging
import re
from typing import Optional, Tuple

from editor.Ironica.language_engine import BaseLanguageProvider

from .domain_models import HoverDetails, PythonContext
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
    """Minimal HTML4 subset safe for ``QToolTip.showText()``."""
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


def _signature_is_redundant(signature: str, name: str, kind: str) -> bool:
    """Check whether *signature* adds nothing beyond ``name`` and ``kind``."""
    sig = (signature or "").strip().lower()
    label = (name or "").strip().lower()
    klabel = (kind or "").strip().lower()
    if not sig or not label:
        return False
    bare = sig[:-2].strip() if sig.endswith("()") else sig
    return bare in (label, f"{klabel} {label}".strip())


def _strip_signature_echo(docstring: str, name: str, kind: str, signature: str) -> str:
    """Drop a leading docstring line that only repeats the signature."""
    lines = (docstring or "").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    first = lines[0].strip()
    folded = first.lower()
    candidates = set()
    for raw in (signature, name):
        text = (raw or "").strip().lower()
        if text:
            candidates.add(text)
            if text.endswith("()"):
                candidates.add(text[:-2].strip())
    label = (name or "").strip()
    klabel = (kind or "").strip().lower()
    if label and klabel:
        candidates.add(f"{klabel} {label.lower()}")
        candidates.add(f"{klabel} {label.lower()}()")
    is_echo = folded in candidates or bool(
        label and re.match(rf"^{re.escape(label)}\s*\(.*\)\s*$", first)
    )
    if is_echo:
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def _format_hover_markdown(details: HoverDetails) -> str:
    """Rich Markdown suitable for ``QTextBrowser.setMarkdown()``."""
    parts: list[str] = []
    doc = _strip_signature_echo(
        _clean_docstring(details.docstring or "") if details.docstring else "",
        details.name,
        details.kind,
        details.signature,
    )

    if details.signature:
        sig = details.signature.strip().replace("```", "\\`\\`\\`")
        if sig and not _signature_is_redundant(sig, details.name, details.kind):
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

    if doc:
        parts.append(f"---\n\n{doc}" if parts else doc)

    if not parts:
        kind = (details.kind or "symbol").strip() or "symbol"
        parts.append(f"*{kind} — no documentation available.*")

    return "\n\n".join(parts)


class PythonLanguageProvider(BaseLanguageProvider):
    """Stateless provider."""

    remote_analysis: bool = True

    remote_kind: str = "analysis"

    language_id: str = "python"

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
        self._project_root: Optional[str] = None
        self._completion_manager = None

    @property
    def project_root(self) -> Optional[str]:
        """Get or set the project root handed to the Jedi adapter."""
        return self._project_root

    @project_root.setter
    def project_root(self, value: Optional[str]) -> None:
        """Get or set the project root handed to the Jedi adapter."""
        self._project_root = value

    @property
    def file_path(self) -> Optional[str]:
        """Get or set the buffer path handed to the Jedi adapter."""
        return self._file_path

    @file_path.setter
    def file_path(self, value: Optional[str]) -> None:
        """Get or set the buffer path handed to the Jedi adapter."""
        self._file_path = value


    def _build_context(
        self,
        text: str,
        line: int,
        col: int,
        file_path: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> PythonContext:
        """Build an immutable adapter context for a caret position."""
        effective_path = file_path or self._file_path
        effective_root = project_root or getattr(self, "_project_root", None)
        return PythonContext(
            source_code=text,
            line=line + 1,
            column=col,
            file_path=effective_path,
            project_root=effective_root,
        )


    def get_hover_details(
        self,
        text: str,
        line: int,
        col: int,
        file_path: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> Optional[HoverDetails]:
        """Return raw HoverDetails domain model for structured UI rendering."""
        if not text:
            return None

        symbol = self._symbol_at(text, line, col)
        if not symbol or keyword.iskeyword(symbol):
            return None

        context = self._build_context(text, line, col, file_path, project_root)
        return self._adapter.get_hover(context)

    def get_hover_hint(self, text: str, line: int, col: int) -> Optional[str]:
        """Return an HTML tooltip for the symbol under the cursor."""
        if not text:
            return None

        hover_details = self.get_hover_details(text, line, col)
        if not hover_details:
            return None

        return _format_qt_tooltip(hover_details)

    @staticmethod
    def _line_text_at(text: str, line: int) -> Optional[str]:
        """Extract one line without splitting the whole buffer."""
        if line < 0:
            return None
        start = 0
        current = 0
        while current < line:
            nxt = text.find("\n", start)
            if nxt == -1:
                return None
            start = nxt + 1
            current += 1
        end = text.find("\n", start)
        return text[start:] if end == -1 else text[start:end]

    @staticmethod
    def _symbol_at(text: str, line: int, col: int) -> Optional[str]:
        """Return the identifier under *col* on *line* without full split."""
        row = PythonLanguageProvider._line_text_at(text, line)
        if row is None:
            return None
        if col < 0 or col > len(row):
            return None

        if _is_inside_string(row, col):
            return None

        for match in re.finditer(r"[A-Za-z_]\w*", row):
            if match.start() <= col < match.end():
                return match.group(0)
        return None

    def get_hover_display(self, text: str, line: int, col: int) -> Optional[tuple]:
        """Return ``(title_markdown, body_markdown)`` for the DocumentationFlyout."""
        details = self.get_hover_details(text, line, col)
        if not details:
            return None

        if details.kind:
            title_markdown = f"## {details.name} ({details.kind.strip().capitalize()})"
        else:
            title_markdown = f"## {details.name}"
        body_markdown = _format_hover_markdown(details)
        return title_markdown, body_markdown

    def get_definition_location(
        self,
        text: str,
        line: int,
        col: int,
        file_path: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> Optional[Tuple[str, int, int]]:
        """Return ``(file_path, line, col)`` for the symbol under the cursor."""
        context = self._build_context(text, line, col, file_path, project_root)

        cached_result = self._cache.get(context, "definition")
        if cached_result is not None:
            return cached_result

        location = self._adapter.get_definition(context)
        if not location:
            return None

        result = (
            str(location.file_path) if location.file_path else "",
            max(0, int(location.line) - 1),
            int(location.column),
        )
        self._cache.set(context, "definition", result)
        return result


    def get_completions(
        self,
        text: str,
        cursor_position: tuple,
        prefix: str,
        file_path: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> list:
        """Return code-completion suggestions for the editor."""
        if not text:
            return []

        line, col = cursor_position
        context = self._build_context(text, line, col, file_path, project_root)

        try:
            return self._adapter.get_completions(context)
        except Exception as e:
            logger.warning("Completion request failed: %s", e)
            return []

    def format_source(self, source_code: str) -> str:
        """Format *source_code* using black."""
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
        """Return ``(start, length, color)`` overlay ranges for *text*."""
        from .semantic_highlights import get_semantic_highlights

        return get_semantic_highlights(text)

    def invalidate_cache(self) -> None:
        """Drop the semantic-highlight cache so overlay colours follow the currently active IDE theme on the next repaint."""
        from .semantic_highlights import invalidate_semantic_cache

        invalidate_semantic_cache()


    def has_folding(self) -> bool:
        """Return ``True`` — the Python plugin provides fold regions."""
        return True

    def get_fold_regions(self, text: str) -> list:
        """Return fold regions computed from Python source indentation."""
        from .folding import compute_fold_regions

        return compute_fold_regions(text)

    def has_diagnostics(self) -> bool:
        """Return ``True`` — the Python plugin provides background diagnostics."""
        return True

    def create_diagnostic_manager(self, editor, file_path, parent):
        """Create a Jedi-backed DiagnosticManager for *editor*."""
        from .jedi_worker import DiagnosticManager

        return DiagnosticManager(editor=editor, file_path=file_path, parent=parent)


    def has_outline(self) -> bool:
        """Return ``True`` — the Python plugin provides file outlines."""
        return True

    def get_outline(self, source_code: str):
        """Return an outline tree for Python source code."""
        from .outline_parser import parse_python_outline

        result = parse_python_outline(source_code)
        if result.root.name == "" and self._file_path:
            result.root.name = self._file_path
        return result

    @property
    def completion_manager(self):
        """Return the ``CompletionManager`` for this provider, or ``None``."""
        return self._completion_manager

    def create_completion_manager(self, editor, file_path, parent):
        """Create a Jedi-backed CompletionManager for *editor*."""
        from .jedi_worker import CompletionManager

        # NOTE: assign unconditionally — keeping the previous value for a
        self._file_path = file_path or None
        self._completion_manager = CompletionManager(
            editor=editor, file_path=file_path, parent=parent
        )
        return self._completion_manager

    def post_fold_setup(self, editor, regions) -> None:
        """Apply Python-specific fold display text labels."""
        from .folding import _apply_import_fold_text

        _apply_import_fold_text(editor, regions)


def create_provider() -> PythonLanguageProvider:
    """Create and return a fully wired PythonLanguageProvider."""
    from .jedi_adapter import JediAdapter
    from .cache import LanguageCache

    adapter = JediAdapter()
    cache = LanguageCache()
    return PythonLanguageProvider(adapter=adapter, cache=cache)
