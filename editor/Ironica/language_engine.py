"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

Language support infrastructure for DreamStudio.

This module provides:

- ``LanguageLexer`` — a generic keyword-based QScintilla lexer driven
  by a JSON configuration dictionary.
- ``BaseLanguageProvider`` — the abstract contract that every language
  intelligence backend must implement.  Future LSP providers will
  subclass this.
- ``LanguageRegistry`` — a central, class-level registry that maps file
  extensions to language identifiers, stores parsed JSON configurations,
  and associates provider instances.

**LSP Integration Plan (not yet implemented):**

A future ``LSPProvider(BaseLanguageProvider)`` subclass will wrap a
language-server process and implement all four abstract methods using
the Language Server Protocol.  ``LanguageRegistry.register_language``
already accepts an optional ``provider_instance`` — an LSP provider
would simply be passed in at registration time.

No changes to the public API are required to add LSP support.
"""

import re
import json
import logging

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from PyQt6.QtGui import QColor
from PyQt6.Qsci import QsciLexerCustom

logger = logging.getLogger(__name__)


class LanguageLexer(QsciLexerCustom):
    """A generic keyword-based syntax highlighter driven by a JSON config.

    The *config* dictionary must contain:

    - ``"styles"``: ``{style_name: "#RRGGBB", ...}``
    - ``"keywords"``: ``{style_name: ["word1", ...], ...}``

    Each ``style_name`` in ``"keywords"`` must also appear in ``"styles"``.
    """

    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.config = config
        self.styles_map: Dict[str, int] = {}
        self.keywords_map: Dict[str, int] = {}
        self._setup_configuration()

    def _setup_configuration(self):
        """Parse the JSON config and populate style / keyword maps."""
        styles = self.config.get("styles", {})
        for idx, (style_name, color_hex) in enumerate(styles.items(), start=1):
            self.styles_map[style_name] = idx
            self.setColor(QColor(color_hex), idx)

        keywords = self.config.get("keywords", {})
        for style_name, kw_list in keywords.items():
            if style_name in self.styles_map:
                for kw in kw_list:
                    self.keywords_map[kw] = self.styles_map[style_name]

    def description(self, style: int) -> str:
        """Return the human-readable name for a style index."""
        for name, idx in self.styles_map.items():
            if idx == style:
                return name
        return ""

    def styleText(self, start: int, end: int):
        """Called by QScintilla to syntax-highlight a text range.

        Uses strict word-boundary regex (``\\b``) with exact match
        offsets.  This eliminates the substring-matching bug where
        ``re.split(r\"(\\W+)\", text)`` fragmented identifiers like
        ``STYLE_PAREN_3`` and caused partial-keyword collisions.
        """
        editor = self.editor()
        if not editor:
            return

        self.startStyling(start)
        text = editor.text()[start:end]

        # Strict word-boundary matching: each match is a whole word
        # with an exact start offset and length.  No substring matching.
        for m in re.finditer(r"\b\w+\b", text):
            word = m.group(0)
            length = m.end() - m.start()
            style_idx = self.keywords_map.get(word, 0)
            self.setStyling(length, style_idx)


class BaseLanguageProvider(ABC):
    """Abstract base class for language intelligence providers.

    Every language that wants autocomplete, hover, go-to-definition,
    or formatting must implement all four methods.  Future LSP
    providers will subclass this and delegate to a language server
    process.

    **Contract:**

    - Methods must never raise exceptions.  Callers catch broadly, so
      any internal failure should be logged and a safe default returned.
    - All text parameters use the raw editor buffer content.
    - Line and column numbers are 0-indexed.
    """

    @abstractmethod
    def get_hover_hint(self, text: str, line: int, col: int) -> Optional[str]:
        """Return a documentation / signature string for the symbol under the cursor.

        Args:
            text: The full editor buffer content.
            line: 0-indexed cursor line.
            col: 0-indexed cursor column.
        """
        return None

    @abstractmethod
    def get_definition_location(
        self, text: str, line: int, col: int
    ) -> Optional[tuple]:
        """Return ``(file_path, line, col)`` for the symbol's definition.

        Args:
            text: The full editor buffer content.
            line: 0-indexed cursor line.
            col: 0-indexed cursor column.
        """
        return None

    @abstractmethod
    def format_source(self, source_code: str) -> str:
        """Format *source_code* and return the formatted text.

        If formatting is not supported, return the input unchanged.
        """
        return source_code

    def get_hover_display(
        self, text: str, line: int, col: int
    ) -> Optional[tuple]:
        """Return ``(title_html, body_html)`` for the symbol under the cursor.

        The *title_html* is a short rich-text fragment shown in the flyout
        header.  The *body_html* is the full documentation body suitable
        for a ``QTextBrowser`` or ``QLabel`` with rich-text support.

        Optional method — return ``None`` when hover documentation is
        unavailable or the provider does not support it.
        """
        return None

    def get_semantic_highlights(self, text: str):
        """Return colour ranges for semantic tokens, or ``None``.

        Optional method — providers that implement it return a list of
        ``(start_offset, length, "#RRGGBB")`` tuples.  The editor uses
        these to paint Scintilla indicators on top of the lexer.

        Return ``None`` to indicate that the provider does not supply
        semantic highlights (the editor falls back to its built-in
        highlighting, if any).
        """
        return None


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------


class LanguageRegistry:
    """Central, class-level registry for DreamStudio language support.

    Maps file extensions to language identifiers, stores parsed JSON
    configuration dictionaries, and associates ``BaseLanguageProvider``
    instances with languages.

    All methods are ``@classmethod`` — no instantiation is required.
    Internal state is shared across the entire process.
    """

    _configs: Dict[str, dict] = {}
    _providers: Dict[str, BaseLanguageProvider] = {}
    _extension_map: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @classmethod
    def register_language(
        cls, json_path: str, provider_instance: Optional[BaseLanguageProvider] = None
    ) -> bool:
        """Read a language configuration JSON file and bind its provider.

        Args:
            json_path: Path to the JSON configuration file.
            provider_instance: Optional intelligence provider.

        Returns:
            ``True`` on success, ``False`` on any validation or I/O error.

        Raises nothing — all errors are logged and ``False`` is returned.

        **JSON format (canonical)::**

            {
                "lang": "python",
                "extensions": ["py", "pyw"],
                "styles": {"keyword": "#C586C0", "definition": "#4FC1FF"},
                "keywords": {"keyword": ["if", "else"], "definition": ["def", "class"]}
            }

        Alternatively, the legacy ``"words"`` / ``"colors_schema"`` format
        from older config files is auto-converted via ``_normalize_config``.
        """
        try:
            config = cls._load_json(json_path)
            if config is None:
                return False

            config = cls._normalize_config(config)
            errors = cls._validate_config(config)
            if errors:
                for err in errors:
                    logger.error("Language config validation error: %s", err)
                return False

            lang_name = config["lang"]

            # Duplicate registration guard.
            if lang_name in cls._configs:
                logger.warning(
                    "Language %r already registered — overwriting", lang_name
                )

            cls._configs[lang_name] = config

            extensions = config.get("extensions", [])
            for ext in extensions:
                normalized_ext = f".{ext.lstrip('.')}"
                existing = cls._extension_map.get(normalized_ext)
                if existing and existing != lang_name:
                    logger.warning(
                        "Extension %r already mapped to %r — "
                        "replacing with %r",
                        normalized_ext,
                        existing,
                        lang_name,
                    )
                cls._extension_map[normalized_ext] = lang_name

            if provider_instance is not None:
                if not isinstance(provider_instance, BaseLanguageProvider):
                    logger.error(
                        "Provider for %r must be a BaseLanguageProvider "
                        "instance, got %s",
                        lang_name,
                        type(provider_instance).__name__,
                    )
                    return False
                cls._providers[lang_name] = provider_instance

            logger.info("Registered language: %s", lang_name)
            return True

        except Exception as exc:
            logger.error("Failed to register language from %s: %s", json_path, exc)
            return False

    @classmethod
    def register_language_dict(
        cls,
        config: dict,
        provider_instance: Optional[BaseLanguageProvider] = None,
    ) -> bool:
        """Register a language from an already-parsed config dictionary.

        Args:
            config: Language configuration dictionary.
            provider_instance: Optional intelligence provider.

        Returns:
            ``True`` on success, ``False`` on validation error.
        """
        try:
            config = cls._normalize_config(config)
            errors = cls._validate_config(config)
            if errors:
                for err in errors:
                    logger.error("Language config validation error: %s", err)
                return False

            lang_name = config["lang"]
            cls._configs[lang_name] = config

            for ext in config.get("extensions", []):
                normalized_ext = f".{ext.lstrip('.')}"
                cls._extension_map[normalized_ext] = lang_name

            if provider_instance is not None:
                if not isinstance(provider_instance, BaseLanguageProvider):
                    logger.error(
                        "Provider must be a BaseLanguageProvider, got %s",
                        type(provider_instance).__name__,
                    )
                    return False
                cls._providers[lang_name] = provider_instance

            logger.info("Registered language (dict): %s", lang_name)
            return True

        except Exception as exc:
            logger.error("Failed to register language dict: %s", exc)
            return False

    @classmethod
    def unregister_language(cls, lang_name: str) -> bool:
        """Remove a language and all its associated state.

        Args:
            lang_name: The language identifier to remove.

        Returns:
            ``True`` if the language was found and removed.
        """
        if lang_name not in cls._configs:
            return False

        del cls._configs[lang_name]
        cls._providers.pop(lang_name, None)

        # Remove extensions that point to this language.
        to_remove = [
            ext for ext, name in cls._extension_map.items() if name == lang_name
        ]
        for ext in to_remove:
            del cls._extension_map[ext]

        logger.info("Unregistered language: %s", lang_name)
        return True

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    @classmethod
    def get_language_by_extension(cls, ext: str) -> Optional[str]:
        """Resolve a file extension to its language identifier.

        Args:
            ext: File extension including the leading dot (e.g. ``".py"``).
        """
        return cls._extension_map.get(ext)

    @classmethod
    def get_config(cls, lang: str) -> Optional[dict]:
        """Return the configuration dictionary for *lang*, or ``None``."""
        return cls._configs.get(lang)

    @classmethod
    def get_provider(cls, lang: str) -> Optional[BaseLanguageProvider]:
        """Return the intelligence provider for *lang*, or ``None``."""
        return cls._providers.get(lang)

    @classmethod
    def is_registered(cls, lang_name: str) -> bool:
        """Return ``True`` if *lang_name* is registered."""
        return lang_name in cls._configs

    @classmethod
    def list_languages(cls) -> List[str]:
        """Return a sorted list of all registered language identifiers."""
        return sorted(cls._configs.keys())

    @classmethod
    def get_all_extensions(cls) -> Dict[str, str]:
        """Return a copy of the extension → language mapping."""
        return dict(cls._extension_map)

    # ------------------------------------------------------------------
    # Reset (for testing)
    # ------------------------------------------------------------------

    @classmethod
    def reset(cls) -> None:
        """Clear all registrations.  Primarily used in tests."""
        cls._configs.clear()
        cls._providers.clear()
        cls._extension_map.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _load_json(cls, json_path: str) -> Optional[dict]:
        """Load and parse a JSON file, returning ``None`` on error."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            logger.error("Malformed JSON in %s: %s", json_path, exc)
            return None
        except FileNotFoundError:
            logger.error("Language config file not found: %s", json_path)
            return None
        except OSError as exc:
            logger.error("Cannot read %s: %s", json_path, exc)
            return None

    @classmethod
    def _normalize_config(cls, config: dict) -> dict:
        """Convert legacy config formats to the canonical format.

        Supports the ``words`` / ``colors_schema`` format used by
        older language JSON files (e.g. ``python.json``).

        The canonical format uses ``"styles"`` and ``"keywords"`` keys.
        """
        if "styles" in config and "keywords" in config:
            return config

        if "words" in config and "colors_schema" in config:
            logger.debug("Normalizing legacy language config for %r", config.get("lang"))
            return cls._convert_legacy_config(config)

        return config

    @classmethod
    def _convert_legacy_config(cls, config: dict) -> dict:
        """Convert a ``words``/``colors_schema`` config to canonical format."""
        words = config.get("words", {})
        colors = config.get("colors_schema", {})

        # Build reverse mapping: word → category, then category → [words].
        category_words: Dict[str, List[str]] = {}
        for word, category in words.items():
            category_words.setdefault(category, []).append(word)

        # Build styles from colors_schema.
        styles = {cat: hex_color for cat, hex_color in colors.items()}

        # Collect extensions if present.
        extensions = config.get("extensions", [])

        # Derive language name.
        lang_name = config.get("lang")
        if not lang_name:
            meta = config.get("meta", {})
            lang_name = meta.get("language", "unknown")

        normalized = {
            "lang": lang_name,
            "extensions": extensions,
            "styles": styles,
            "keywords": category_words,
        }
        return normalized

    @classmethod
    def _validate_config(cls, config: dict) -> List[str]:
        """Validate a (possibly normalised) config dict.

        Returns a list of error message strings.  An empty list means
        the config is valid.
        """
        errors: List[str] = []

        lang_name = config.get("lang")
        if not lang_name:
            errors.append("Missing mandatory 'lang' key")

        extensions = config.get("extensions", [])
        if not extensions:
            errors.append("No extensions defined — language will be unreachable by file type")

        styles = config.get("styles")
        if styles is None:
            errors.append("Missing 'styles' section — syntax highlighting will not work")
        elif not isinstance(styles, dict):
            errors.append("'styles' must be a dictionary")

        keywords = config.get("keywords")
        if keywords is None:
            errors.append("Missing 'keywords' section")
        elif not isinstance(keywords, dict):
            errors.append("'keywords' must be a dictionary")
        elif styles and isinstance(styles, dict):
            for cat in keywords:
                if cat not in styles:
                    errors.append(
                        f"Keyword category {cat!r} has no matching style"
                    )

        return errors
