import logging
from pathlib import Path
from PyQt6.QtGui import QFont, QFontDatabase

logger = logging.getLogger(__name__)

FONTS_DIR = Path(__file__).parent

_FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}

# Monospace font families — excluded from UI font lists.
_MONOSPACE_FAMILIES: set[str] = {
    "Space Mono",
    "Cascadia Code",
    "Fira Code",
    "JetBrains Mono",
    "Consolas",
    "Courier New",
    "Noto Sans Mono",
}


def load_font(path_to_font: Path) -> str | None:
    """Safely registers a font file and returns its family name."""
    if not path_to_font.exists():
        logger.error(f"Font file does not exist: {path_to_font}")
        return None

    font_id = QFontDatabase.addApplicationFont(str(path_to_font))

    if font_id == -1:
        logger.error(f"Failed to load font from {path_to_font}")
        return None

    font_families = QFontDatabase.applicationFontFamilies(font_id)
    if not font_families:
        logger.error(f"No valid font families found in {path_to_font}")
        return None

    return font_families[0]


def _discover_font_files() -> list[Path]:
    """Recursively discover all font files under FONTS_DIR."""
    font_files: list[Path] = []
    for ext in _FONT_EXTENSIONS:
        font_files.extend(FONTS_DIR.rglob(f"*{ext}"))
    return sorted(font_files)


class Fonts:
    """Container for application fonts.

    Fonts are dynamically discovered from the ``fonts/`` directory at
    init time.  The ``available_families()`` class method returns every
    family that was successfully registered, and ``ui_families()``
    filters out monospace families so they can be offered as UI font
    choices.
    """

    FONT_SPACE_MONO: str = "Space Mono"
    FONT_MONTSERRAT: str = "Montserrat"
    FONT_SEGOE_UI: str = "Segoe UI"
    FONT_INTER: str = "Inter"
    FONT_CASCADIA_CODE: str = "Cascadia Code"
    FONT_FIRA_CODE: str = "Fira Code"

    _registered_families: list[str] = []

    @classmethod
    def init(cls):
        """Register all bundled fonts with Qt's font database.

        Discovers every font file under ``fonts/`` recursively and
        registers it.  Safe to call multiple times — individual
        ``load_font`` calls are idempotent and failures are logged
        without raising.
        """
        cls._registered_families.clear()
        seen: set[str] = set()

        for path in _discover_font_files():
            family = load_font(path)
            if family and family not in seen:
                seen.add(family)
                cls._registered_families.append(family)

        logger.info(
            "Registered %d font families: %s",
            len(cls._registered_families),
            cls._registered_families,
        )

    @classmethod
    def available_families(cls) -> list[str]:
        """Return all font families registered via ``init()``."""
        return list(cls._registered_families)

    @classmethod
    def ui_families(cls) -> list[str]:
        """Return registered families suitable for UI use (non-monospace)."""
        return [
            f for f in cls._registered_families
            if f not in _MONOSPACE_FAMILIES
        ]

    @classmethod
    def ensure_font(cls, family: str) -> str | None:
        """Load a single font file from fonts/ by family name at runtime.

        Searches the fonts directory for a file whose path contains the
        family name (case-insensitive) and registers it on the fly.
        Returns the resolved family name, or ``None`` if not found.
        """
        if family in cls._registered_families:
            return family

        search_key = family.lower().replace(" ", "_").replace("-", "_")
        for path in _discover_font_files():
            path_key = path.stem.lower().replace(" ", "_").replace("-", "_")
            if search_key in path_key:
                result = load_font(path)
                if result:
                    cls._registered_families.append(result)
                    logger.info("Dynamically loaded font: %s", result)
                    return result

        logger.warning("Font not found in fonts/ directory: %s", family)
        return None

    @classmethod
    def space_mono(cls, size: int = 10) -> QFont:
        return QFont("Space Mono", size)

    @classmethod
    def montserrat_regular(cls, size: int = 10) -> QFont:
        return QFont("Montserrat", size)

    @classmethod
    def montserrat_bold(cls, size: int = 10) -> QFont:
        font = QFont("Montserrat", size)
        font.setWeight(QFont.Weight.Bold)
        return font

    @classmethod
    def montserrat_semibold(cls, size: int = 10) -> QFont:
        font = QFont("Montserrat", size)
        font.setWeight(QFont.Weight.DemiBold)
        return font

    @classmethod
    def montserrat_italic(cls, size: int = 10) -> QFont:
        font = QFont("Montserrat", size)
        font.setItalic(True)
        return font

    @classmethod
    def segoe_ui(cls, size: int = 10) -> QFont:
        return QFont("Segoe UI", size)

    @classmethod
    def segoe_ui_italic(cls, size: int = 10) -> QFont:
        font = QFont("Segoe UI", size)
        font.setItalic(True)
        return font

    @classmethod
    def inter(cls, size: int = 10) -> QFont:
        return QFont("Inter", size)

    @classmethod
    def inter_italic(cls, size: int = 10) -> QFont:
        font = QFont("Inter", size)
        font.setItalic(True)
        return font

    @classmethod
    def inter_bold(cls, size: int = 10) -> QFont:
        font = QFont("Inter", size)
        font.setWeight(QFont.Weight.Bold)
        return font

    @classmethod
    def cascadia_code(cls, size: int = 10) -> QFont:
        font = QFont("Cascadia Code", size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    @classmethod
    def cascadia_code_italic(cls, size: int = 10) -> QFont:
        font = QFont("Cascadia Code", size)
        font.setItalic(True)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    @classmethod
    def fira_code(cls, size: int = 10) -> QFont:
        font = QFont("Fira Code", size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    @classmethod
    def fira_code_light(cls, size: int = 10) -> QFont:
        font = QFont("Fira Code", size)
        font.setWeight(QFont.Weight.Light)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    @classmethod
    def fira_code_medium(cls, size: int = 10) -> QFont:
        font = QFont("Fira Code", size)
        font.setWeight(QFont.Weight.Medium)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    @classmethod
    def fira_code_semibold(cls, size: int = 10) -> QFont:
        font = QFont("Fira Code", size)
        font.setWeight(QFont.Weight.DemiBold)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    @classmethod
    def fira_code_bold(cls, size: int = 10) -> QFont:
        font = QFont("Fira Code", size)
        font.setWeight(QFont.Weight.Bold)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    @classmethod
    def make_font(cls, family: str, size: int = 10, **kwargs) -> QFont:
        """Create a QFont for any registered or system font family.

        Args:
            family: Font family name (e.g. ``"Inter"``, ``"Montserrat"``).
            size: Point size for the font.
            **kwargs: Optional QFont properties — ``bold`` (bool),
                ``italic`` (bool), ``weight`` (``QFont.Weight``),
                ``monospace`` (bool, adds ``Monospace`` style hint).

        Returns:
            A configured ``QFont`` instance.
        """
        cls.ensure_font(family)
        font = QFont(family, size)
        if kwargs.get("bold"):
            font.setWeight(QFont.Weight.Bold)
        if kwargs.get("italic"):
            font.setItalic(True)
        if "weight" in kwargs:
            font.setWeight(kwargs["weight"])
        if kwargs.get("monospace"):
            font.setStyleHint(QFont.StyleHint.Monospace)
        return font
