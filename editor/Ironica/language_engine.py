"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Language support infrastructure for DreamStudio.
"""

from editor import *

from editor.Ironica.retheme import resolve_colour

logger = logging.getLogger(__name__)

_RE_WORD = re.compile(rb"[A-Za-z0-9_]+")


class LanguageLexer(QsciLexerCustom):
    """A generic keyword-based syntax highlighter driven by a JSON config."""

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
    """Abstract base class for language intelligence providers."""

    @abstractmethod
    def get_hover_hint(self, text: str, line: int, col: int) -> Optional[str]:
        """Return a documentation / signature string for the symbol under the cursor."""
        return None

    @abstractmethod
    def get_definition_location(
        self, text: str, line: int, col: int
    ) -> Optional[tuple]:
        """Return `(file_path, line, col)` for the symbol's definition."""
        return None

    @abstractmethod
    def format_source(self, source_code: str) -> str:
        """Format *source_code* and return the formatted text."""
        return source_code

    def get_hover_display(self, text: str, line: int, col: int) -> Optional[tuple]:
        """Return `(title_markdown, body_markdown)` for the symbol under the cursor."""
        return None

    def get_semantic_highlights(self, text: str):
        """Return colour ranges for semantic tokens, or `None`."""
        return None


    def has_folding(self) -> bool:
        """Return ``True`` if this provider supplies code fold regions."""
        return False

    def get_fold_regions(self, text: str) -> list:
        """Return fold regions as ``(start_line, end_line, header)`` tuples."""
        return []

    def has_diagnostics(self) -> bool:
        """Return ``True`` if this provider supplies background diagnostics."""
        return False

    def create_diagnostic_manager(self, editor, file_path, parent):
        """Create and return a diagnostic manager for *editor*."""
        return None


    def has_outline(self) -> bool:
        """Return ``True`` if this provider supplies file outline data."""
        return False

    def get_outline(self, source_code: str) -> Optional["OutlineResult"]:
        """Return an outline tree for *source_code*."""
        return None

    def post_fold_setup(self, editor, regions) -> None:
        """Called after fold regions are pushed to FoldManager."""
        pass


class LanguageRegistry:
    """Central, class-level registry for DreamStudio language support."""

    _configs: Dict[str, dict] = {}
    _providers: Dict[str, BaseLanguageProvider] = {}
    _extension_map: Dict[str, str] = {}
    _filename_map: Dict[str, str] = {}
    _snippet_paths: Dict[str, str] = {}


    @classmethod
    def _store_language(
        cls, config: dict, provider_instance: Optional[BaseLanguageProvider]
    ) -> bool:
        """Persist a validated config and provider into the registry."""
        lang_name = config["lang"]
        if lang_name in cls._configs:
            logger.warning("Language %r already registered — overwriting", lang_name)
        cls._configs[lang_name] = config
        for ext in config.get("extensions", []):
            normalized_ext = f".{str(ext).lstrip('.').lower()}"
            existing = cls._extension_map.get(normalized_ext)
            if existing and existing != lang_name:
                logger.warning(
                    "Extension %r already mapped to %r — replacing with %r",
                    normalized_ext,
                    existing,
                    lang_name,
                )
            cls._extension_map[normalized_ext] = lang_name
        for filename in config.get("filenames", []):
            normalized_name = str(filename).strip().lower()
            if not normalized_name:
                continue
            existing = cls._filename_map.get(normalized_name)
            if existing and existing != lang_name:
                logger.warning(
                    "Filename %r already mapped to %r — replacing with %r",
                    normalized_name,
                    existing,
                    lang_name,
                )
            cls._filename_map[normalized_name] = lang_name
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
        """Read a language configuration JSON file and bind its provider."""
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
        """Register a language from an already-parsed config dictionary."""
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
        """Remove a language and all its associated state."""
        if lang_name not in cls._configs:
            return False

        del cls._configs[lang_name]
        cls._providers.pop(lang_name, None)
        cls._snippet_paths.pop(lang_name, None)

        to_remove = [
            ext for ext, name in cls._extension_map.items() if name == lang_name
        ]
        for ext in to_remove:
            del cls._extension_map[ext]
        to_remove = [
            name for name, lang in cls._filename_map.items() if lang == lang_name
        ]
        for name in to_remove:
            del cls._filename_map[name]

        logger.info("Unregistered language: %s", lang_name)
        return True


    @classmethod
    def get_language_by_extension(cls, ext: str) -> Optional[str]:
        """Resolve a file extension to its language identifier."""
        if not isinstance(ext, str) or not ext:
            return None
        normalized = f".{ext.lstrip('.').lower()}"
        return cls._extension_map.get(normalized)

    @classmethod
    def get_language_for_file(cls, file_path: str) -> Optional[str]:
        """Resolve a file path to its language identifier."""
        if not isinstance(file_path, str) or not file_path:
            return None
        basename = os.path.basename(file_path).strip().lower()
        if basename and basename in cls._filename_map:
            return cls._filename_map[basename]
        _, ext = os.path.splitext(basename)
        if ext:
            return cls.get_language_by_extension(ext)
        return None

    @classmethod
    def get_config(cls, lang: str) -> Optional[dict]:
        """Return the configuration dictionary for *lang*, or `None`."""
        return cls._configs.get(lang)

    @classmethod
    def get_snippets(cls, lang: str) -> List[str]:
        """Return the snippet identifiers for *lang*."""
        config = cls._configs.get(lang)
        if config is None:
            return []
        return list(config.get("snippets", []))

    @classmethod
    def register_snippet_path(cls, lang: str, snippets_path: str) -> bool:
        """Remember where a language's snippet bodies live."""
        if lang not in cls._configs:
            logger.warning("Cannot attach snippets to unregistered language %r", lang)
            return False
        if not snippets_path or not os.path.isfile(snippets_path):
            logger.warning("Snippet file not found for %r: %s", lang, snippets_path)
            return False
        cls._snippet_paths[lang] = os.path.abspath(snippets_path)
        return True

    @classmethod
    def get_snippet_path(cls, lang: str) -> Optional[str]:
        """Return the snippet-body file for *lang*, or ``None``."""
        return cls._snippet_paths.get(lang)

    @classmethod
    def get_display_name(cls, lang: str) -> str:
        """Return the human-readable name for a language identifier."""
        config = cls._configs.get(lang) or {}
        display_name = config.get("display_name")
        if isinstance(display_name, str) and display_name.strip():
            return display_name.strip()
        return lang.replace("_", " ").replace("-", " ").title()

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

    @classmethod
    def get_all_filenames(cls) -> Dict[str, str]:
        """Return a copy of the exact-filename → language mapping."""
        return dict(cls._filename_map)


    @classmethod
    def reset(cls) -> None:
        """Clear all registrations."""
        cls._configs.clear()
        cls._providers.clear()
        cls._extension_map.clear()
        cls._filename_map.clear()
        cls._snippet_paths.clear()


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
        """Convert legacy config formats to the canonical format."""
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

        category_words: Dict[str, List[str]] = {}
        for word, category in words.items():
            category_words.setdefault(category, []).append(word)

        styles = {cat: hex_color for cat, hex_color in colors.items()}

        extensions = config.get("extensions", [])

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
        """Validate a (possibly normalised) config dict."""
        errors: List[str] = []

        lang_name = config.get("lang")
        if not lang_name:
            errors.append("Missing mandatory 'lang' key")

        extensions = config.get("extensions", [])
        if not extensions:
            errors.append(
                "No extensions defined — language will be unreachable by file type"
            )

        filenames = config.get("filenames", [])
        if filenames and not isinstance(filenames, list):
            errors.append("'filenames' must be a list of exact file names")

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
