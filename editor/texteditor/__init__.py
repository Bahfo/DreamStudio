import os

_KEYWORDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords")


def keywords_path(filename: str) -> str:
    return os.path.join(_KEYWORDS_DIR, filename)
