import logging
from pathlib import Path
from PyQt6.QtGui import QFont, QFontDatabase

logger = logging.getLogger(__name__)

FONTS_DIR = Path(__file__).parent


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


class Fonts:
    """
    Container for application fonts.
    """

    FONT_SPACE_MONO: str = "Space Mono"
    FONT_MONTSERRAT: str = "Montserrat"
    FONT_SEGOE_UI: str = "Segoe UI"
    FONT_INTER: str = "Inter"
    FONT_CASCADIA_CODE: str = "Cascadia Code"
    FONT_FIRA_CODE: str = "Fira Code"

    @classmethod
    def init(cls):
        """Register all bundled fonts with Qt's font database.

        Safe to call multiple times — individual ``load_font`` calls are
        idempotent and failures are logged without raising.
        """
        _FONT_FILES = [
            FONTS_DIR / "Space_Mono" / "SpaceMono-Regular.ttf",
            FONTS_DIR / "Montserrat" / "Montserrat-Regular.ttf",
            FONTS_DIR / "Montserrat" / "Montserrat-Bold.ttf",
            FONTS_DIR / "Montserrat" / "Montserrat-Italic.ttf",
            FONTS_DIR / "Montserrat" / "Montserrat-SemiBold.ttf",
            FONTS_DIR / "SegoeUI" / "Segoe UI 400.ttf",
            FONTS_DIR / "SegoeUI" / "Segoe UI Italique 400.ttf",
            FONTS_DIR / "inter" / "Inter-VariableFont_opsz,wght.ttf",
            FONTS_DIR / "inter" / "Inter-Italic-VariableFont_opsz,wght.ttf",
            FONTS_DIR / "Cascadia_Code" / "CascadiaCode-VariableFont_wght.ttf",
            FONTS_DIR / "Cascadia_Code" / "CascadiaCode-Italic-VariableFont_wght.ttf",
            FONTS_DIR / "Fira_Code" / "FiraCode-VariableFont_wght.ttf",
            FONTS_DIR / "Fira_Code" / "static" / "FiraCode-Light.ttf",
            FONTS_DIR / "Fira_Code" / "static" / "FiraCode-Regular.ttf",
            FONTS_DIR / "Fira_Code" / "static" / "FiraCode-Medium.ttf",
            FONTS_DIR / "Fira_Code" / "static" / "FiraCode-SemiBold.ttf",
            FONTS_DIR / "Fira_Code" / "static" / "FiraCode-Bold.ttf",
        ]
        for path in _FONT_FILES:
            load_font(path)

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
