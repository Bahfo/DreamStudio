"""
C/C++ language plugin for DreamStudio.

Exports the public API surface used by the editor's registration
and integration layers.  All internal modules remain decoupled
from the editor core; only the registration module bridges the two.
"""

from editor.Ironica.plugins.clang.provider import (
    CLanguageProvider,
    create_provider,
    CEditorIntegration,
)
from editor.Ironica.plugins.clang.clang_adapter import ClangAdapter
from editor.Ironica.plugins.clang.clang_domain_models import (
    CContext,
    HoverDetails,
    DefinitionLocation,
    CompletionDetails,
    CDiagnostic,
    ParameterInfo,
)
from editor.Ironica.plugins.clang.c_interfaces import IClangAdapter
from editor.Ironica.plugins.clang.c_folding import (
    compute_fold_regions,
    compute_folds_for_editor,
)
from editor.Ironica.plugins.clang.c_worker import (
    CDiagnosticManager,
    CCompletionManager,
)

__all__ = [
    "CLanguageProvider",
    "create_provider",
    "CEditorIntegration",
    "ClangAdapter",
    "CContext",
    "HoverDetails",
    "DefinitionLocation",
    "CompletionDetails",
    "CDiagnostic",
    "ParameterInfo",
    "IClangAdapter",
    "compute_fold_regions",
    "compute_folds_for_editor",
    "CDiagnosticManager",
    "CCompletionManager",
]
