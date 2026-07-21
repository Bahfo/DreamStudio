import os

# Ironica APIs and Modules
from editor.Ironica.api import *
from editor.Ironica.regex import *
from editor.Ironica.minimap import *
from editor.Ironica.folding import *
from editor.Ironica.tab_editor import *
from editor.Ironica.code_editor import *
from editor.Ironica.language_engine import *
from editor.Ironica.highlighting_api import *
from editor.Ironica.autocomplete_menu import *

_KEYWORDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords")


def keywords_path(filename: str) -> str:
    return os.path.join(_KEYWORDS_DIR, filename)
