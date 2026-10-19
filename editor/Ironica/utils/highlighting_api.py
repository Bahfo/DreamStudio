"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Core Highlighting API for DreamStudio.
"""

from __future__ import annotations

from editor import *

from editor.Ironica.retheme import is_hex_color

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenStyle:
    """Maps a semantic token type to a QScintilla style index and foreground colour."""

    style_id: int
    colour: str
    bold: bool = False
    italic: bool = False


STYLE_DEFAULT = TokenStyle(0, "#D4D4D4")

SEMANTIC_TO_CONFIG_KEY: Dict[str, str] = {
    "keyword": "keyword",
    "builtin": "builtin",
    "definition": "definition",
    "class": "class_def",
    "string": "string",
    "number": "number",
    "comment": "comment",
    "decorator": "decorator",
    "self": "additional",
    "operator": "operator",
    "variable": "variable",
    "module": "import",
    "function": "definition",
    "parameter": "additional",
    "constant": "additional",
    "bracket": "bracket",
    "bracket_2": "bracket_2",
    "bracket_3": "bracket_3",
    "exception": "exception",
    "header": "header",
}

_DEFAULT_COLOURS: Dict[str, str] = {
    "keyword": "#C586C0",
    "builtin": "#4FC1FF",
    "definition": "#DCDCAA",
    "class": "#4EC9B0",
    "class_def": "#4EC9B0",
    "string": "#CE9178",
    "number": "#B5CEA8",
    "comment": "#6A9955",
    "decorator": "#D7BA7D",
    "additional": "#569CD6",
    "operator": "#D4D4D4",
    "variable": "#9CDCFE",
    "module": "#4FC1FF",
    "function": "#DCDCAA",
    "parameter": "#9CDCFE",
    "constant": "#569CD6",
    "bracket": "#FFD700",
    "bracket_2": "#C678DD",
    "bracket_3": "#61AFEF",
    "exception": "#FF6B6B",
    "import": "#82AAFF",
    "header": "#4FC1FF",
}


def styles_from_config(config: dict) -> Dict[str, TokenStyle]:
    """Build a STYLES dict from a language configuration."""
    config_styles = config.get("styles", {})
    palette = config.get("palette", {}) or {}
    style_id = 1
    result: Dict[str, TokenStyle] = {}

    needed_keys: set = set(SEMANTIC_TO_CONFIG_KEY.values())

    config_key_to_id: Dict[str, int] = {}
    for key in config_styles:
        if key in needed_keys:
            config_key_to_id[key] = style_id
            style_id += 1

    for sem_type, config_key in SEMANTIC_TO_CONFIG_KEY.items():
        raw = config_styles.get(config_key)
        if raw is not None:
            colour = raw if is_hex_color(raw) else palette.get(raw)
            if not colour:
                colour = _DEFAULT_COLOURS.get(sem_type, "#D4D4D4")
        else:
            colour = _DEFAULT_COLOURS.get(sem_type, "#D4D4D4")
        sid = config_key_to_id.get(config_key, 0)
        result[sem_type] = TokenStyle(sid, colour)

    return result


STYLES: Dict[str, TokenStyle] = {}


@dataclass(frozen=True)
class Token:
    """A single styled token with exact byte boundaries."""

    start: int
    length: int
    style: TokenStyle
    kind: str


class ITokenProvider(ABC):
    """Abstract contract for language-aware token providers."""

    @abstractmethod
    def get_tokens(self, text: str) -> List[Token]:
        """Return styled tokens for the full document text."""
        return []

    @abstractmethod
    def get_semantic_ranges(self, text: str) -> List[Tuple[int, int, str]]:
        """Return ``(start_offset, length, "#RRGGBB")`` tuples for Scintilla indicator overlays."""
        return []


class HighlightingRegistry:
    """Class-level registry mapping language identifiers to their ``ITokenProvider`` implementations."""

    _providers: Dict[str, ITokenProvider] = {}

    @classmethod
    def register(cls, lang: str, provider: ITokenProvider) -> None:
        """Register a token provider for *lang*."""
        if lang in cls._providers:
            logger.warning("Overwriting token provider for %r", lang)
        cls._providers[lang] = provider
        logger.info("Registered token provider for %s", lang)

    @classmethod
    def unregister(cls, lang: str) -> bool:
        """Remove the provider for *lang*."""
        if lang not in cls._providers:
            return False
        del cls._providers[lang]
        logger.info("Unregistered token provider for %s", lang)
        return True

    @classmethod
    def get_provider(cls, lang: str) -> Optional[ITokenProvider]:
        """Return the provider for *lang*, or ``None``."""
        return cls._providers.get(lang)

    @classmethod
    def has_provider(cls, lang: str) -> bool:
        return lang in cls._providers

    @classmethod
    def reset(cls) -> None:
        """Clear all registrations (for testing)."""
        cls._providers.clear()

