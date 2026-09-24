"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

C/C++ Language Provider for DreamStudio.
Implements the stateless BaseLanguageProvider interface for the editor core,
and provides per-editor integration via diagnostic/completion managers.
"""

from __future__ import annotations
import logging
import re
from typing import List, Optional, Tuple, Any

from editor import *

try:
    from editor.Ironica.language_engine import BaseLanguageProvider
except ImportError:
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


from .clang_domain_models import CContext, DefinitionLocation, HoverDetails
from .clang_adapter import ClangAdapter
from .c_worker import CDiagnosticManager, CCompletionManager
from .c_folding import compute_fold_regions, compute_folds_for_editor
from .c_semantic_highlights import (
    get_semantic_highlights,
    invalidate_semantic_cache,
)

logger = logging.getLogger("DreamStudio.CSupport.LanguageProvider")


def _is_inside_string(line_text: str, col: int) -> bool:
    """Return True if col falls inside a string literal on line_text."""
    i = 0
    n = len(line_text)
    while i < n:
        ch = line_text[i]
        if ch in ('"', "'"):
            quote = ch
            if i <= col < i + 1:
                return True
            end = line_text.find(quote, i + 1)
            while end != -1 and line_text[end - 1] == "\\":
                end = line_text.find(quote, end + 1)
            if end == -1:
                return col >= i
            if i + 1 <= col <= end:
                return True
            i = end + 1
        else:
            i += 1
    return False


class CLanguageProvider(BaseLanguageProvider):
    """
    Stateless provider for C/C++ language support.
    Handles coordinate transformations and caching, delegating analysis
    to the ClangAdapter. Per-editor state is created via manager factories.
    """

    remote_analysis: bool = False

    def __init__(
        self,
        adapter: Optional[ClangAdapter] = None,
        clang_library_path: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._adapter = adapter or ClangAdapter(library_path=clang_library_path)
        self._file_path: Optional[str] = None
        self._completion_manager: Optional[CCompletionManager] = None

    @property
    def file_path(self) -> Optional[str]:
        return self._file_path

    @file_path.setter
    def file_path(self, value: Optional[str]) -> None:
        self._file_path = value

    @staticmethod
    def _friendly_kind(kind: str) -> str:
        """Return a concise human-readable label for a libclang cursor kind."""
        labels = {
            "FUNCTION_DECL": "Function",
            "CXX_METHOD": "Method",
            "FUNCTION_TEMPLATE": "Function template",
            "VAR_DECL": "Variable",
            "PARM_DECL": "Parameter",
            "FIELD_DECL": "Field",
            "STRUCT_DECL": "Struct",
            "UNION_DECL": "Union",
            "ENUM_DECL": "Enum",
            "ENUM_CONSTANT_DECL": "Enumerator",
            "TYPEDEF_DECL": "Type alias",
            "TYPE_ALIAS_DECL": "Type alias",
            "MACRO_DEFINITION": "Macro",
            "MACRO_INSTANTIATION": "Macro",
            "NAMESPACE": "Namespace",
            "CLASS_DECL": "Class",
        }
        if kind in labels:
            return labels[kind]
        return kind.replace("_", " ").title() if kind else "Symbol"

    @staticmethod
    def _clean_c_documentation(raw: Optional[str]) -> Optional[str]:
        """Convert a C comment into readable Markdown."""
        if not raw:
            return None

        text = raw.strip()
        if text.startswith("/*"):
            text = text[2:]
        if text.endswith("*/"):
            text = text[:-2]
        text = re.sub(r"^///+!?\s?", "", text)

        text = re.sub(
            r"@param\s+(\w+)",
            lambda match: f"\n\n**{match.group(1)}** — ",
            text,
        )
        text = re.sub(
            r"@(?:return|returns)\b",
            "\n\n**Returns:** ",
            text,
        )
        text = re.sub(
            r"@(?:throw|throws)\b",
            "\n\n**Throws:** ",
            text,
        )
        text = re.sub(r"(\*\*\w+\*\* —)\s+", r"\1 ", text)
        text = re.sub(r"(\*\*(?:Returns|Throws):\*\*)\s+", r"\1 ", text)
        text = re.sub(
            r"@(?:brief|short|note|warning|see)\b\s*",
            "\n\n",
            text,
        )

        lines: List[str] = []
        for source_line in text.splitlines():
            line = source_line.strip()
            if line.startswith("***/") or line.startswith("*/"):
                continue
            if line.startswith("*") and not line.startswith("**"):
                line = line[1:].lstrip()
            if not line:
                if lines and lines[-1] != "":
                    lines.append("")
                continue
            lines.append(line)

        cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
        return cleaned or None

    def _build_context(
        self, text: str, line: int, col: int, file_path: Optional[str] = None
    ) -> CContext:
        effective_path = file_path or self._file_path
        return CContext(
            source_code=text,
            line=line + 1,  # Clang uses 1-indexed lines
            col=col + 1,  # Clang uses 1-indexed columns
            file_path=effective_path,
            compile_args=[],  # Could be enhanced with compile_commands.json
        )

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

        import re

        for match in re.finditer(r"[A-Za-z_]\w*", row):
            if match.start() <= col < match.end():
                return match.group(0)
        return None

    def get_hover_details(
        self, text: str, line: int, col: int
    ) -> Optional[HoverDetails]:
        if not text:
            return None

        symbol = self._symbol_at(text, line, col)
        if not symbol:
            return None

        context = self._build_context(text, line, col)
        return self._adapter.get_hover(context)

    def get_hover_hint(self, text: str, line: int, col: int) -> Optional[str]:
        if not text:
            return None

        hover_details = self.get_hover_details(text, line, col)
        if not hover_details:
            return None

        parts = []
        kind = self._friendly_kind(hover_details.kind)
        if kind:
            parts.append(f"{hover_details.name} ({kind})")
        else:
            parts.append(hover_details.name)
        if hover_details.signature:
            parts.append(hover_details.signature)
        documentation = self._clean_c_documentation(hover_details.docstring)
        if documentation:
            parts.append(documentation)
        return "\n".join(parts)

    def get_hover_display(self, text: str, line: int, col: int) -> Optional[tuple]:
        details = self.get_hover_details(text, line, col)
        if not details:
            return None

        friendly_kind = self._friendly_kind(details.kind)
        title_markdown = (
            f"## {details.name} ({friendly_kind})"
            if friendly_kind
            else f"## {details.name}"
        )

        body_parts = []
        if details.signature:
            body_parts.append(f"```c\n{details.signature}\n```")
        if details.parameters:
            body_parts.append(f"### Parameters ({len(details.parameters)})")
            for param in details.parameters:
                body_parts.append(f"- **{param.name}** `{param.type_str}`")
        if details.return_type:
            body_parts.append(f"**Returns:** `{details.return_type}`")
        documentation = self._clean_c_documentation(details.docstring)
        if documentation:
            body_parts.append(f"---\n\n{documentation}")

        body_markdown = (
            "\n\n".join(body_parts)
            if body_parts
            else "*No additional documentation available.*"
        )
        return title_markdown, body_markdown

    def get_definition_location(
        self, text: str, line: int, col: int
    ) -> Optional[Tuple[str, int, int]]:
        context = self._build_context(text, line, col)
        location = self._adapter.get_definition(context)
        if not location:
            return None

        return (
            str(location.file_path) if location.file_path else "",
            max(0, int(location.line) - 1),
            max(0, int(location.column) - 1),
        )

    def get_completions(self, text: str, cursor_position: tuple, prefix: str) -> list:
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
        if not source_code or not source_code.strip():
            return source_code
        try:
            import subprocess

            result = subprocess.run(
                ["clang-format", "-style=file"],
                input=source_code.encode(),
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.decode()
        except Exception as exc:
            logger.debug("clang-format failed: %s", exc)
        return source_code

    def get_semantic_highlights(self, text: str):
        """Return semantic C/C++ overlay ranges for the active buffer."""
        return get_semantic_highlights(text, self._file_path)

    def invalidate_cache(self) -> None:
        """Invalidate C semantic tokens after a theme or buffer change."""
        invalidate_semantic_cache()

    def has_folding(self) -> bool:
        return True

    def get_fold_regions(self, text: str) -> list:
        return compute_fold_regions(text)

    def has_diagnostics(self) -> bool:
        return True

    def create_diagnostic_manager(self, editor, file_path, parent):
        """Create the C diagnostics manager for an editor instance."""
        if file_path:
            self._file_path = file_path
        return CDiagnosticManager(
            editor=editor,
            adapter=ClangAdapter(),
            file_path=file_path,
            compile_args=[],
            parent=parent,
        )

    @property
    def completion_manager(self):
        """Return the completion manager used by the active editor."""
        return self._completion_manager

    def create_completion_manager(self, editor, file_path, parent):
        """Create the C completion manager for an editor instance."""
        if file_path:
            self._file_path = file_path
        self._completion_manager = CCompletionManager(
            editor=editor,
            adapter=ClangAdapter(),
            file_path=file_path,
            compile_args=[],
            parent=parent,
        )
        return self._completion_manager

    def has_outline(self) -> bool:
        return False

    def post_fold_setup(self, editor, regions) -> None:
        from .c_folding import _apply_include_fold_text

        _apply_include_fold_text(editor, regions)


class CEditorIntegration:
    """
    Per-editor C language integration (QObject).
    Created by the editor when opening a C/C++ file.
    """

    def __init__(
        self,
        editor,
        file_path: Optional[str] = None,
        compile_args: Optional[List[str]] = None,
        clang_library_path: Optional[str] = None,
        parent: Optional[Any] = None,
    ) -> None:
        from PyQt6.QtCore import QObject, pyqtSlot

        self._editor = editor
        self._file_path = file_path
        self._compile_args = compile_args or []

        self._adapter = ClangAdapter(library_path=clang_library_path)
        self._diagnostic_manager = CDiagnosticManager(
            editor=self._editor,
            adapter=self._adapter,
            file_path=self._file_path,
            compile_args=self._compile_args,
            parent=parent,
        )

        self._completion_manager = CCompletionManager(
            editor=self._editor,
            adapter=self._adapter,
            file_path=self._file_path,
            compile_args=self._compile_args,
            parent=parent,
        )

        self._completion_manager.completions_ready.connect(self._on_completions_ready)
        self.update_folding()
        self._editor.textChanged.connect(self._on_text_changed)

    def set_compile_args(self, args: List[str]) -> None:
        self._compile_args = args
        self._diagnostic_manager.set_compile_args(args)
        self._completion_manager._compile_args = args

    def set_file_path(self, path: str) -> None:
        self._file_path = path
        self._diagnostic_manager._file_path = path
        self._completion_manager._file_path = path

    def get_hover_info(self, line: int, col: int) -> Optional[HoverDetails]:
        ctx = CContext(
            source_code=self._editor.text(),
            line=line + 1,
            col=col + 1,
            file_path=self._file_path,
            compile_args=self._compile_args,
        )
        return self._adapter.get_hover(ctx)

    def goto_definition(self, line: int, col: int) -> Optional[DefinitionLocation]:
        ctx = CContext(
            source_code=self._editor.text(),
            line=line + 1,
            col=col + 1,
            file_path=self._file_path,
            compile_args=self._compile_args,
        )
        return self._adapter.get_definition(ctx)

    def request_completions(self, line: int, col: int) -> None:
        self._completion_manager.request(
            source=self._editor.text(),
            line=line,
            col=col,
            file_path=self._file_path,
        )

    def update_folding(self) -> None:
        try:
            compute_folds_for_editor(self._editor)
        except Exception as exc:
            logger.error("Failed to compute C fold regions: %s", exc)

    def _on_text_changed(self) -> None:
        self.update_folding()

    def _on_completions_ready(self, request_id: int, completions: list) -> None:
        show_popup = getattr(self._editor, "show_completion_popup", None)
        if show_popup is not None:
            show_popup(completions)

    def shutdown(self) -> None:
        self._diagnostic_manager.shutdown()
        self._completion_manager.shutdown()


def create_provider() -> CLanguageProvider:
    """Create and return a fully wired CLanguageProvider.

    This factory is invoked by the dynamic plugin registration system
    via importlib when loading the C language plugin.
    """
    from .clang_adapter import ClangAdapter

    adapter = ClangAdapter()
    return CLanguageProvider(adapter=adapter)
