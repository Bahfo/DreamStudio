"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Preprocessor directive completion for the C++ plugin.

Static table — no parse cost. libclang stays silent on directive lines,
so the engine owns this context outright.
"""

from __future__ import annotations

from typing import List, Tuple

from ..models import CppCompletion

#: (directive word, one-line doc). Insert text carries a trailing space so
#: header/macro completion continues naturally after acceptance.
_DIRECTIVES: Tuple[Tuple[str, str], ...] = (
    ("include", "include a header: #include <…> or #include \"…\""),
    ("define", "define a macro: #define NAME value"),
    ("undef", "undefine a macro: #undef NAME"),
    ("if", "conditional block: #if expression"),
    ("ifdef", "include block if macro is defined: #ifdef NAME"),
    ("ifndef", "include block if macro is not defined: #ifndef NAME"),
    ("elif", "alternative condition: #elif expression"),
    ("elifdef", "alternative if macro is defined: #elifdef NAME"),
    ("elifndef", "alternative if macro is not defined: #elifndef NAME"),
    ("else", "alternative block: #else"),
    ("endif", "close a conditional block: #endif"),
    ("pragma", "compiler directive: #pragma …"),
    ("error", "emit a compile error: #error message"),
    ("warning", "emit a compile warning: #warning message"),
    ("line", "override line reporting: #line number file"),
    ("import", "import a module header unit: #import <…>"),
)


def complete_directive(prefix: str) -> List[CppCompletion]:
    """Return directives starting with *prefix* (``#`` excluded).

    Args:
        prefix: Partial directive word without the leading ``#``.

    Returns:
        Directive completions whose insert text ends with a space.
    """
    lowered = (prefix or "").lower()
    out: List[CppCompletion] = []
    for word, doc in _DIRECTIVES:
        if not word.startswith(lowered):
            continue
        out.append(
            CppCompletion(
                text=word,
                insert_text="#" + word + " ",
                kind="decorator",
                signature=doc,
            )
        )
    return out
