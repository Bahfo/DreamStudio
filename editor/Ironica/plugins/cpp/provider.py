"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

New C++ provider (Feature 1: completion only).
"""

from __future__ import annotations

# Base Language Provider
from editor.Ironica.language_engine import BaseLanguageProvider

# Local Imports
from .models import CppContext
from . import args as cpp_args
from .context import classify
from .engine import CppEngine


class CppProvider(BaseLanguageProvider):
    """
    Stateless provider; per-editor state lives in the manager.
    """

    language_id: str = "cpp"
    slash_snippets_only: bool = True
    cpp_member_triggers: bool = True
    suppress_token_fallback: bool = True

    def __init__(self) -> None:
        super().__init__()
        self._shared_index = None
        self._file_path: str | None = None
        self._completion_manager = None

    def get_hover_hint(self, text, line, col):
        return None

    def get_definition_location(self, text, line, col):
        return None

    def format_source(self, source_code):
        return source_code

    def has_diagnostics(self):
        return False

    def get_completions(
        self,
        text,
        cursor_position,
        prefix,
        file_path=None,
        project_root=None,
    ) -> list:
        """
        Sync path (used when manager is dead). Never raises.
        """

        if not text:
            return []
        if prefix and prefix.startswith("/"):
            return []
        line0, col0 = cursor_position
        lines = text.splitlines()
        row = lines[line0] if 0 <= line0 < len(lines) else ""
        if not row:
            return []
        kind, _ = classify(row, col0)
        if kind in ("none", "comment", "preprocessor"):
            return []
        if kind == "include":
            from .includes import complete_include, parse_include

            try:
                parsed = parse_include(row, col0)
                if not parsed:
                    return []
                open_char, partial = parsed
                items = complete_include(
                    partial,
                    open_char,
                    file_path=file_path or self._file_path,
                    compile_args=cpp_args.args_for_file(
                        file_path or self._file_path, text
                    ),
                )
            except Exception:
                return []
            if prefix:
                partial_lower = prefix.lower()
                items = [c for c in items if c.text.lower().startswith(partial_lower)]
            return items

        ctx = CppContext(
            source_code=text,
            line=line0 + 1,
            col=col0 + 1,
            file_path=file_path or self._file_path,
            compile_args=cpp_args.args_for_file(file_path or self._file_path, text),
            prefix=prefix or "",
        )
        try:
            items = self._make_engine().complete(ctx) or []
        except Exception:
            return []
        if prefix:
            pl = prefix.lower()
            items = [c for c in items if c.text.lower().startswith(pl)]
        return items

    def _make_engine(self):
        """Return a shared-index engine (TU cache lives per editor)."""
        from .engine import CppEngine

        return CppEngine(shared_index=self._shared_index)

    def create_completion_manager(self, editor, file_path, parent):
        """
        Called by tab_editor.py:597. Editor-scoped, never singleton.
        """

        from .completion import CppCompletionManager
        from .engine import CppEngine

        if file_path:
            self._file_path = file_path
        engine = CppEngine(
            shared_index=self._shared_index,
            owner_id=id(editor),
        )
        if self._shared_index is None:
            self._shared_index = engine.shared_index
        self._completion_manager = CppCompletionManager(
            editor=editor, engine=engine, file_path=file_path, parent=parent
        )
        return self._completion_manager

    @property
    def completion_manager(self):
        return self._completion_manager


def create_provider() -> CppProvider:
    """
    Factory named in plugin.json.
    """
    return CppProvider()
