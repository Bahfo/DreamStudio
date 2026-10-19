"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Minimal CMake provider:
"""

from __future__ import annotations

import logging
import re

from editor.Ironica.language_engine import BaseLanguageProvider, LanguageRegistry

logger = logging.getLogger("DreamStudio.CMake.Provider")

_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")


class CmakeProvider(BaseLanguageProvider):
    """Stateless CMake provider (keywords + snippets only)."""

    language_id: str = "cmake"

    def get_hover_hint(self, text: str, line: int, col: int):
        """CMake has no hover support; always ``None``."""
        return None

    def get_definition_location(self, text: str, line: int, col: int):
        """CMake has no go-to-definition; always ``None``."""
        return None

    def format_source(self, source_code: str) -> str:
        """Return *source_code* unchanged (no CMake formatter)."""
        return source_code

    def has_diagnostics(self) -> bool:
        """CMake ships no background diagnostics."""
        return False

    def has_folding(self) -> bool:
        """CMake ships no fold regions."""
        return False

    def get_completions(
        self,
        text,
        cursor_position,
        prefix,
        file_path=None,
        project_root=None,
    ) -> list:
        """Complete CMake commands, variables and snippets by prefix."""
        try:
            return self._complete(text, cursor_position, prefix or "")
        except Exception as exc:
            logger.debug("cmake completion failed: %s", exc)
            return []

    def _complete(self, text: str, cursor_position, prefix: str) -> list:
        """Build prefix matches over the registered cmake vocabulary."""
        line0, _col0 = cursor_position
        lines = (text or "").splitlines()
        row = lines[line0] if 0 <= line0 < len(lines) else ""
        stripped = row.lstrip()
        if stripped.startswith("#"):
            return []
        match = _WORD_RE.search(prefix) if prefix else None
        needle = (match.group(0) if match else prefix or "").lower()
        if not needle:
            return []

        config = LanguageRegistry.get_config("cmake") or {}
        keywords = config.get("keywords") or {}
        words: dict[str, str] = {}
        for category, names in keywords.items():
            if not isinstance(names, list):
                continue
            for name in names:
                words.setdefault(str(name), category)

        items = []
        for word, category in words.items():
            if word.lower().startswith(needle):
                items.append(
                    {
                        "text": word,
                        "kind": "keyword",
                        "signature": f"cmake {category}",
                    }
                )
        for trigger in LanguageRegistry.get_snippets("cmake"):
            name = trigger.lstrip("/")
            if name.lower().startswith(needle) and name not in words:
                items.append(
                    {"text": trigger, "kind": "snippet", "signature": "snippet"}
                )
        items.sort(key=lambda item: item["text"].lower())
        return items[:100]


def create_provider() -> CmakeProvider:
    """Factory named in plugin.json."""
    return CmakeProvider()
