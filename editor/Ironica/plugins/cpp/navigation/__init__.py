"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Navigation module for C++ GoTo functionality.
"""

from editor.Ironica.plugins.cpp.navigation.engine import (
    NavigationEngine,
    NavigationResult,
    SymbolContext,
)
from editor.Ironica.plugins.cpp.navigation.popup import (
    NavigationPopup,
    NavigationResultDelegate,
)

__all__ = [
    "NavigationEngine",
    "NavigationResult",
    "SymbolContext",
    "NavigationPopup",
    "NavigationResultDelegate",
]