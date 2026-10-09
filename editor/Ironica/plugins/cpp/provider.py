"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

New C++ provider (Feature 1: completion only).
"""

from __future__ import annotations

import logging

# Base Language Provider
from editor.Ironica.language_engine import BaseLanguageProvider

logger = logging.getLogger("DreamStudio.Cpp.Provider")

# Local Imports: the full plugin surface, loaded as one watched unit.
from .models import CppContext
from .intellisense import args as cpp_args
from .intellisense import CppEngine
from .autocompletion import (
    classify,
    CppCompletionManager,
)


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
        self._fold_engine = None
        self._highlight_cache = None

    def get_semantic_highlights(self, text: str, theme_name: str | None = None):
        """Return libclang identifier overlays for the buffer.

        Args:
            text: Full editor buffer content.
            theme_name: Active IDE theme; resolved automatically when omitted.

        Returns:
            List of ``(start, length, "#RRGGBB")`` overlay ranges.
        """
        import hashlib

        from .highlighting.tokens import compute_highlights, _resolve_colors

        if not text or not text.strip():
            return []
        try:
            from editor.Ironica.language_engine import LanguageRegistry
            from editor.Ironica.retheme import active_theme_name

            config = LanguageRegistry.get_config("cpp") or {}
            theme = theme_name or active_theme_name()
        except Exception:
            config = {}
            theme = theme_name or "dark"
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
        key = (digest, theme, self._file_path)
        cached = self._highlight_cache
        if cached is not None and cached[0] == key:
            return list(cached[1])
        try:
            if self._fold_engine is None:
                self._fold_engine = self._make_engine()
            engine = self._fold_engine
            file_path = self._file_path
            context = CppContext(
                source_code=text,
                line=1,
                col=1,
                file_path=file_path,
                compile_args=cpp_args.args_for_file(file_path, text),
            )
            try:
                tu = engine._tu(context)
            except Exception:
                tu = None
            colors = _resolve_colors(config, theme)
            ranges = compute_highlights(
                text, tu, colors,
                file_path or cpp_args.unsaved_name())
        except Exception:
            return []
        self._highlight_cache = (key, ranges)
        return list(ranges)

    def get_semantic_ranges(self, text: str, theme_name: str | None = None):
        """Return ``(start, length, color)`` ranges (token-provider alias)."""
        return self.get_semantic_highlights(text, theme_name)

    def invalidate_cache(self) -> None:
        """Drop cached highlight styles and token ranges (retheme)."""
        self._highlight_cache = None

    def get_hover_hint(self, text, line, col):
        return None

    def get_definition_location(self, text, line, col):
        return None

    def format_source(self, source_code):
        return source_code

    def has_diagnostics(self):
        return False

    def has_folding(self) -> bool:
        return True

    def get_fold_regions(self, text: str) -> list:
        """Return AST-accurate fold regions for the buffer."""
        from .folding.regions import compute_fold_regions

        if not text or not text.strip():
            return []
        try:
            if self._fold_engine is None:
                self._fold_engine = self._make_engine()
            engine = self._fold_engine
            file_path = self._file_path
            context = CppContext(
                source_code=text,
                line=1,
                col=1,
                file_path=file_path,
                compile_args=cpp_args.args_for_file(file_path, text),
            )
            try:
                tu = engine._tu(context)
            except Exception:
                tu = None
            regions = compute_fold_regions(
                text, tu,
                file_path or cpp_args.unsaved_name())
        except Exception:
            from .folding.regions import compute_fold_regions as fallback

            regions = fallback(text)
        return regions

    def post_fold_setup(self, editor, regions) -> None:
        """Label collapsed include runs with their line counts."""
        setup = getattr(editor, "_setup_folding_display_text", None)
        if callable(setup):
            try:
                setup()
            except Exception:
                pass
        set_text = getattr(editor, "set_custom_import_fold_text", None)
        if callable(set_text):
            for region in regions or []:
                kind = getattr(region, "kind", "")
                if kind != "include":
                    continue
                count = (getattr(region, "end_line", 0)
                         - getattr(region, "start_line", 0) + 1)
                try:
                    set_text(getattr(region, "start_line", 0), count,
                             "includes")
                except Exception:
                    continue

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
            from .autocompletion.includes import complete_include, parse_include

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
        from .intellisense.engine import CppEngine

        return CppEngine(shared_index=self._shared_index)

    def create_completion_manager(self, editor, file_path, parent):
        """
        Called by tab_editor.py:597. Editor-scoped, never singleton.
        """

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
