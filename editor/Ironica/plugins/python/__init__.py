"""
Python language plugin for DreamStudio.

Exports the public API surface used by the editor's registration
and integration layers.  All internal modules remain decoupled
from the editor core; only the registration module bridges the two.
"""

from editor.Ironica.plugins.python.provider import PythonLanguageProvider
from editor.Ironica.plugins.python.provider import create_provider
from editor.Ironica.plugins.python.jedi_adapter import JediAdapter
from editor.Ironica.plugins.python.cache import LanguageCache
from editor.Ironica.plugins.python.semantic_highlights import (
    get_semantic_highlights,
    invalidate_semantic_cache,
)
from editor.Ironica.plugins.python.folding import compute_fold_regions

__all__ = [
    "PythonLanguageProvider",
    "create_provider",
    "JediAdapter",
    "LanguageCache",
    "get_semantic_highlights",
    "invalidate_semantic_cache",
    "compute_fold_regions",
]
