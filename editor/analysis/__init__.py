"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Analysis package — diagnostic backends are auto-registered on import.
"""

# Auto-register language backends from their plugin folders
from editor.Ironica.plugins.python import diagnostic_backend as _py_backend  # noqa: F401
from editor.Ironica.plugins.cpp import diagnostic_backend as _cpp_backend  # noqa: F401
