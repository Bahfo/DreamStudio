"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Autocompletion mission: trigger classification, threaded completion
bridging, preprocessor completion sources, buffer symbol table, and
call-site intelligence used for ranking.
"""

from editor.Ironica.plugins.cpp.autocompletion.callsite import (
    CallSite,
    buffer_declared_types,
    candidate_type,
    declared_init_type,
    enclosing_return_type,
    find_call,
    in_condition,
    normalize_type,
    overload_param_types,
    param_type,
    resolve,
    signature_params,
    type_tier,
)
from editor.Ironica.plugins.cpp.autocompletion.completion import (
    CppCompletionManager,
)
from editor.Ironica.plugins.cpp.autocompletion.context import (
    classify,
    macro_params,
)
from editor.Ironica.plugins.cpp.autocompletion.directives import (
    complete_directive,
)
from editor.Ironica.plugins.cpp.autocompletion.includes import (
    complete_include,
    parse_include,
    project_include_dirs,
    system_include_dirs,
)
from editor.Ironica.plugins.cpp.autocompletion.macros import (
    buffer_macros,
    collect_macros,
    complete_guards,
    complete_macro_body,
)
from editor.Ironica.plugins.cpp.autocompletion.symbols import (
    Symbol,
    SymbolsCache,
    buffer_symbols,
    scan_symbols,
)

__all__ = [
    "CallSite",
    "CppCompletionManager",
    "Symbol",
    "SymbolsCache",
    "buffer_declared_types",
    "buffer_macros",
    "buffer_symbols",
    "candidate_type",
    "classify",
    "collect_macros",
    "complete_directive",
    "complete_guards",
    "complete_include",
    "complete_macro_body",
    "declared_init_type",
    "enclosing_return_type",
    "find_call",
    "in_condition",
    "macro_params",
    "normalize_type",
    "overload_param_types",
    "param_type",
    "parse_include",
    "project_include_dirs",
    "resolve",
    "scan_symbols",
    "signature_params",
    "system_include_dirs",
    "type_tier",
]
