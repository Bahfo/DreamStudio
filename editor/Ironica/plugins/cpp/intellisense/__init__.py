"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Intellisense mission: libclang completion engine and compile-flag
resolution backing every semantic query of the plugin.
"""

from editor.Ironica.plugins.cpp.intellisense.args import (
    args_for_file,
    is_cpp,
    resource_args,
    unsaved_name,
)
from editor.Ironica.plugins.cpp.intellisense.engine import CppEngine

__all__ = [
    "CppEngine",
    "args_for_file",
    "is_cpp",
    "resource_args",
    "unsaved_name",
]
