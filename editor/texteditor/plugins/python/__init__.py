"""
Python language plugin for DreamStudio.

Exports the public API surface used by the editor's registration
and integration layers.  All internal modules remain decoupled
from the editor core; only the registration module bridges the two.
"""

from editor.texteditor.plugins.python.provider import PythonLanguageProvider
from editor.texteditor.plugins.python.jedi_adapter import JediAdapter
from editor.texteditor.plugins.python.cache import LanguageCache
from editor.texteditor.plugins.python.navigation import (
    NavigationService,
    ReferenceFinderService,
)
from editor.texteditor.plugins.python.refactoring import RenameRefactoringService
from editor.texteditor.plugins.python.complexity import ComplexityAnalysisService
from editor.texteditor.plugins.python.hover_presenter import HoverPresenter
from editor.texteditor.plugins.python.semantic_highlights import (
    get_semantic_highlights,
)
from editor.texteditor.plugins.python.views import (
    ReferenceViewerWidget,
    RefactorDialog,
    ComplexityDashboard,
)
from editor.texteditor.plugins.python.editor_integration import (
    PythonIntegrationLayer,
    ContextBuilder,
    ResultTranslator,
)
from editor.texteditor.plugins.python.folding import (
    compute_fold_regions,
    compute_folds_for_editor,
)

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
]
