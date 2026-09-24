"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

Language support infrastructure for DreamStudio.

This module provides:

- `LanguageLexer` — a generic keyword-based QScintilla lexer driven
  by a JSON configuration dictionary.
- `BaseLanguageProvider` — the abstract contract that every language
  intelligence backend must implement.  Future LSP providers will
  subclass this.
- `LanguageRegistry` — a central, class-level registry that maps file
  extensions to language identifiers, stores parsed JSON configurations,
  and associates provider instances.

**LSP Integration Plan (not yet implemented):**

A future `LSPProvider(BaseLanguageProvider)` subclass will wrap a
language-server process and implement all four abstract methods using
the Language Server Protocol.  `LanguageRegistry.register_language`
already accepts an optional `provider_instance` — an LSP provider
would simply be passed in at registration time.

No changes to the public API are required to add LSP support.
"""

from editor import *

from editor.Ironica.retheme import resolve_colour

logger = logging.getLogger(__name__)

_RE_WORD = re.compile(rb"[A-Za-z0-9_]+")


class LanguageLexer(QsciLexerCustom):
    """A generic keyword-based syntax highlighter driven by a JSON config.

    The *config* dictionary must contain:

    - `"styles"`: `{style_name: "#RRGGBB", ...}`
    - `"keywords"`: `{style_name: ["word1", ...], ...}`

    Each `style_name` in `"keywords"` must also appear in `"styles"`.
    """

    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.config = config
        self.styles_map: Dict[str, int] = {}
        self.keywords_map: Dict[str, int] = {}
        self._lex_state = 0
        self._lex_quote = 0
        self._lex_scanned_until = 0
        self._setup_configuration()

    def _setup_configuration(self):
        """Parse the JSON config and populate style / keyword maps."""
        styles = self.config.get("styles", {})
        palette = self.config.get("palette", {}) or {}
        for idx, (style_name, colour_value) in enumerate(styles.items(), start=1):
            self.styles_map[style_name] = idx
            self.setColor(QColor(resolve_colour(colour_value, palette, "#D4D4D4")), idx)

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

    def styleText(self, start: int, end: int) -> None:
        """Syntax-highlight a byte range with persistent C-style states."""
        editor = self.editor()
        if not editor or start < 0 or end <= start:
            return

        if start == self._lex_scanned_until:
            buffer = bytearray(end - start + 1)
            written = editor.SendScintilla(editor.SCI_GETTEXTRANGE, start, end, buffer)
            raw = bytes(buffer[:written])
            base = start
            state = self._lex_state
            quote = self._lex_quote
        else:
            raw = editor.text().encode("utf-8")
            end = min(end, len(raw))
            base = 0
            state = 0
            quote = 0
            if not raw:
                return

        self.startStyling(start)
        string_style = self.styles_map.get("string", 0)
        char_style = self.styles_map.get("string", 0)
        comment_style = self.styles_map.get("comment", 0)
        run_start = 0
        run_style = (
            comment_style if state in (3, 4) else string_style if state in (1, 2) else 0
        )
        length = len(raw)
        index = 0

        def flush(stop: int) -> None:
            nonlocal run_start, run_style
            overlap_start = max(base + run_start, start)
            overlap_end = min(base + stop, end)
            if overlap_end > overlap_start:
                self.setStyling(overlap_start - start, run_style)
            run_start = stop
            run_style = 0

        while index < length:
            byte = raw[index]

            if state == 1 or state == 2:
                if byte == 0x5C and index + 1 < length:
                    index += 2
                    continue
                index += 1
                if byte == quote:
                    flush(index)
                    state = 0
                continue

            if state == 3:
                if byte == 0x0A:
                    flush(index + 1)
                    state = 0
                    index += 1
                    continue
                index += 1
                continue

            if state == 4:
                index += 1
                if byte == 0x2A and index < length and raw[index] == 0x2F:
                    index += 1
                    flush(index)
                    state = 0
                continue

            if byte == 0x2F and index + 1 < length:
                marker = raw[index + 1]
                if marker == 0x2F:
                    flush(index)
                    run_style = comment_style
                    run_start = index
                    state = 3
                    index += 2
                    continue
                if marker == 0x2A:
                    flush(index)
                    run_style = comment_style
                    run_start = index
                    state = 4
                    index += 2
                    continue

            if byte in (0x22, 0x27):
                flush(index)
                quote = byte
                run_style = string_style if byte == 0x22 else char_style
                run_start = index
                state = 1
                index += 1
                continue

            match = _RE_WORD.match(raw, index)
            if match:
                word = raw[match.start() : match.end()].decode("ascii")
                style = self.keywords_map.get(word, 0)
                if style:
                    flush(index)
                    run_style = style
                    run_start = match.end()
                index = match.end()
                continue

            index += 1

        flush(length)
        self._lex_state = state
        self._lex_quote = quote
        self._lex_scanned_until = base + length


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
        """Return `(file_path, line, col)` for the symbol's definition.

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

    def get_hover_display(self, text: str, line: int, col: int) -> Optional[tuple]:
        """Return `(title_markdown, body_markdown)` for the symbol under the cursor.

        The *title_markdown* is a short Markdown fragment (typically a
        heading) shown in the flyout header.  The *body_markdown* is the
        full documentation body rendered via ``QTextDocument.setMarkdown()``.

        Optional method — return `None` when hover documentation is
        unavailable or the provider does not support it.
        """
        return None

    def get_semantic_highlights(self, text: str):
        """Return colour ranges for semantic tokens, or `None`.

        Optional method — providers that implement it return a list of
        `(start_offset, length, "#RRGGBB")` tuples.  The editor uses
        these to paint Scintilla indicators on top of the lexer.

        Return `None` to indicate that the provider does not supply
        semantic highlights (the editor falls back to its built-in
        highlighting, if any).
        """
        return None

    # ------------------------------------------------------------------
    # Capability flags (optional features)
    # ------------------------------------------------------------------

    def has_folding(self) -> bool:
        """Return ``True`` if this provider supplies code fold regions.

        Providers that override ``get_fold_regions`` should return
        ``True`` here so the editor calls them on text changes.
        """
        return False

    def get_fold_regions(self, text: str) -> list:
        """Return fold regions as ``(start_line, end_line, header)`` tuples.

        *start_line* and *end_line* are 0-indexed line numbers.
        *header* is a short display string shown when the region is
        collapsed (e.g. ``"def foo"`` or ``"import ..."``).

        Called by the editor when ``has_folding()`` returns ``True``.
        """
        return []

    def has_diagnostics(self) -> bool:
        """Return ``True`` if this provider supplies background diagnostics.

        Providers that override ``create_diagnostic_manager`` should
        return ``True`` here so the editor attaches a diagnostic
        worker when a file is opened.
        """
        return False

    def create_diagnostic_manager(self, editor, file_path, parent):
        """Create and return a diagnostic manager for *editor*.

        Called by the tab editor when ``has_diagnostics()`` returns
        ``True`` and a file is opened.  The manager should connect
        to the editor's ``textChanged`` signal and call
        ``editor.add_diagnostic_underline()`` / ``clear_diagnostic_underlines()``.

        Returns ``None`` by default.
        """
        return None

    # ------------------------------------------------------------------
    # Outline support (optional)
    # ------------------------------------------------------------------

    def has_outline(self) -> bool:
        """Return ``True`` if this provider supplies file outline data.

        Providers that override ``get_outline`` should return ``True``
        here so the IDE wires up the outline panel automatically.
        """
        return False

    def get_outline(self, source_code: str) -> Optional["OutlineResult"]:
        """Return an outline tree for *source_code*.

        Called by the IDE when the outline panel is visible and the
        active editor changes or the source text is modified.

        Args:
            source_code: The full editor buffer content.

        Returns:
            An ``OutlineResult`` or ``None`` if outline is unavailable.
        """
        return None

    def post_fold_setup(self, editor, regions) -> None:
        """Called after fold regions are pushed to FoldManager.

        Override for language-specific fold display text or other
        post-processing (e.g. Python's ``(... +N imports)`` ghost text).

        Args:
            editor: The ``CodeEditor`` instance.
            regions: The fold regions that were just applied.
        """
        pass


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------


class LanguageRegistry:
    """Central, class-level registry for DreamStudio language support.

    Maps file extensions to language identifiers, stores parsed JSON
    configuration dictionaries, and associates `BaseLanguageProvider`
    instances with languages.

    All methods are `@classmethod` — no instantiation is required.
    Internal state is shared across the entire process.
    """

    _configs: Dict[str, dict] = {}
    _providers: Dict[str, BaseLanguageProvider] = {}
    _extension_map: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @classmethod
    def _store_language(
        cls, config: dict, provider_instance: Optional[BaseLanguageProvider]
    ) -> bool:
        """Persist a validated config and provider into the registry.

        Handles duplicate-language warnings, extension-map warnings and
        provider type checking. Returns False only on provider type mismatch.
        """
        lang_name = config["lang"]
        if lang_name in cls._configs:
            logger.warning("Language %r already registered — overwriting", lang_name)
        cls._configs[lang_name] = config
        for ext in config.get("extensions", []):
            normalized_ext = f".{ext.lstrip('.')}"
            existing = cls._extension_map.get(normalized_ext)
            if existing and existing != lang_name:
                logger.warning(
                    "Extension %r already mapped to %r — replacing with %r",
                    normalized_ext,
                    existing,
                    lang_name,
                )
            cls._extension_map[normalized_ext] = lang_name
        if provider_instance is not None:
            if not isinstance(provider_instance, BaseLanguageProvider):
                logger.error(
                    "Provider for %r must be a BaseLanguageProvider instance, got %s",
                    lang_name,
                    type(provider_instance).__name__,
                )
                return False
            cls._providers[lang_name] = provider_instance
        return True

    @classmethod
    def register_language(
        cls, json_path: str, provider_instance: Optional[BaseLanguageProvider] = None
    ) -> bool:
        """Read a language configuration JSON file and bind its provider.

        Args:
            json_path: Path to the JSON configuration file.
            provider_instance: Optional intelligence provider.

        Returns:
            `True` on success, `False` on any validation or I/O error.

        Raises nothing — all errors are logged and `False` is returned.

        **JSON format (canonical)::**
            ```
            {
                "lang": "python",
                "extensions": ["py", "pyw"],
                "styles": {"keyword": "#C586C0", "definition": "#4FC1FF"},
                "keywords": {"keyword": ["if", "else"], "definition": ["def", "class"]}
            }
            ```

        Alternatively, the legacy `"words"` / `"colors_schema"` format
        from older config files is auto-converted via `_normalize_config`.
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
            if not cls._store_language(config, provider_instance):
                return False
            logger.info("Registered language: %s", config["lang"])
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
            `True` on success, `False` on validation error.
        """
        try:
            config = cls._normalize_config(config)
            errors = cls._validate_config(config)
            if errors:
                for err in errors:
                    logger.error("Language config validation error: %s", err)
                return False
            if not cls._store_language(config, provider_instance):
                return False
            logger.info("Registered language (dict): %s", config["lang"])
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
            `True` if the language was found and removed.
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
            ext: File extension including the leading dot (e.g. `".py"`).
        """
        return cls._extension_map.get(ext)

    @classmethod
    def get_config(cls, lang: str) -> Optional[dict]:
        """Return the configuration dictionary for *lang*, or `None`."""
        return cls._configs.get(lang)

    @classmethod
    def get_snippets(cls, lang: str) -> List[str]:
        """Return the snippet identifiers for *lang*.

        Args:
            lang: The language identifier (e.g. ``"python"``).

        Returns:
            A list of snippet name strings (e.g. ``["/Class", "/Main"]``).
            Returns an empty list when the language has no snippets defined.
        """
        config = cls._configs.get(lang)
        if config is None:
            return []
        return list(config.get("snippets", []))

    @classmethod
    def get_provider(cls, lang: str) -> Optional[BaseLanguageProvider]:
        """Return the intelligence provider for *lang*, or `None`."""
        return cls._providers.get(lang)

    @classmethod
    def is_registered(cls, lang_name: str) -> bool:
        """Return `True` if *lang_name* is registered."""
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
        """Load and parse a JSON file, returning `None` on error."""
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

        Supports the `words` / `colors_schema` format used by
        older language JSON files (e.g. `python.json`).

        The canonical format uses `"styles"` and `"keywords"` keys.
        """
        if "styles" in config and "keywords" in config:
            return config

        if "words" in config and "colors_schema" in config:
            logger.debug(
                "Normalizing legacy language config for %r", config.get("lang")
            )
            return cls._convert_legacy_config(config)

        return config

    @classmethod
    def _convert_legacy_config(cls, config: dict) -> dict:
        """Convert a `words`/`colors_schema` config to canonical format."""
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
            errors.append(
                "No extensions defined — language will be unreachable by file type"
            )

        styles = config.get("styles")
        if styles is None:
            errors.append(
                "Missing 'styles' section — syntax highlighting will not work"
            )
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
                    errors.append(f"Keyword category {cat!r} has no matching style")

        return errors
