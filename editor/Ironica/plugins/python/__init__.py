"""
Python language plugin for DreamStudio.

Exports the public API surface used by the editor's registration
and integration layers.  All internal modules remain decoupled
from the editor core; only the registration module bridges the two.
"""

from editor.Ironica.plugins.python.provider import PythonLanguageProvider
from editor.Ironica.plugins.python.jedi_adapter import JediAdapter
from editor.Ironica.plugins.python.cache import LanguageCache
from editor.Ironica.plugins.python.navigation import (
    NavigationService,
    ReferenceFinderService,
)
from editor.Ironica.plugins.python.refactoring import RenameRefactoringService
from editor.Ironica.plugins.python.complexity import ComplexityAnalysisService
from editor.Ironica.plugins.python.hover_presenter import HoverPresenter
from editor.Ironica.plugins.python.semantic_highlights import (
    get_semantic_highlights,
)
from editor.Ironica.plugins.python.views import (
    ReferenceViewerWidget,
    RefactorDialog,
    ComplexityDashboard,
)
from editor.Ironica.plugins.python.editor_integration import (
    PythonIntegrationLayer,
    ContextBuilder,
    ResultTranslator,
)
from editor.Ironica.plugins.python.folding import (
    compute_fold_regions,
    compute_folds_for_editor,
)
from editor.Ironica.plugins.python.highlighter import install

__all__ = [
    "PythonLanguageProvider",
    "JediAdapter",
    "LanguageCache",
    "NavigationService",
    "ReferenceFinderService",
    "RenameRefactoringService",
    "ComplexityAnalysisService",
    "HoverPresenter",
    "get_semantic_highlights",
    "ReferenceViewerWidget",
    "RefactorDialog",
    "ComplexityDashboard",
    "PythonIntegrationLayer",
    "ContextBuilder",
    "ResultTranslator",
    "compute_fold_regions",
    "compute_folds_for_editor",
    "install",
]
