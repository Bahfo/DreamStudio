"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Deterministic helpers shared by the Python-plugin tests.
# ruff: noqa: UP045
"""

from __future__ import annotations

from typing import Any

from editor.Ironica.plugins.python.domain_models import (
    CompletionDetails,
    DefinitionLocation,
    HoverDetails,
    PythonContext,
)
from editor.Ironica.plugins.python.interfaces import IJediAdapter


class RecordingAdapter(IJediAdapter):
    """Deterministic adapter double that records every request context."""

    def __init__(
        self,
        hover: HoverDetails | None = None,
        definition: DefinitionLocation | None = None,
        completions: list[CompletionDetails] | None = None,
        hover_error: Exception | None = None,
        definition_error: Exception | None = None,
        completions_error: Exception | None = None,
    ) -> None:
        self.hover = hover
        self.definition = definition
        self.completions = completions if completions is not None else []
        self.hover_error = hover_error
        self.definition_error = definition_error
        self.completions_error = completions_error
        self.calls: list[tuple[str, PythonContext]] = []

    def get_hover(self, context: PythonContext) -> HoverDetails | None:
        self.calls.append(("hover", context))
        if self.hover_error is not None:
            raise self.hover_error
        return self.hover

    def get_definition(self, context: PythonContext) -> DefinitionLocation | None:
        self.calls.append(("definition", context))
        if self.definition_error is not None:
            raise self.definition_error
        return self.definition

    def get_completions(self, context: PythonContext) -> list[CompletionDetails]:
        self.calls.append(("completions", context))
        if self.completions_error is not None:
            raise self.completions_error
        return list(self.completions)


def build_large_python_module(
    class_count: int = 60,
    methods_per_class: int = 24,
) -> str:
    """Build a deterministic, annotated Python module with >10,000 lines."""
    parts = [
        '"""Synthetic module used to measure large-file plugin behaviour."""',
        "import os",
        "import sys",
        "from collections import OrderedDict",
        "",
        "CONSTANT_VALUE = 42",
        "",
    ]
    for class_index in range(class_count):
        parts.append(f"class Widget{class_index}(object):")
        parts.append(f'    """Widget {class_index} documentation string."""')
        parts.append("")
        for method_index in range(methods_per_class):
            parts.append(
                f"    def method_{method_index}(self, value: int = {method_index}) -> int:"
            )
            parts.append(
                f'        """Method {method_index} of widget {class_index}."""'
            )
            parts.append("        result = value + CONSTANT_VALUE")
            parts.append("        for index in range(result):")
            parts.append("            if index % 2 == 0:")
            parts.append("                result += index")
            parts.append("        return result")
            parts.append("")
    return "\n".join(parts)


def build_flat_python_module(line_target: int = 10_000) -> str:
    """Build a flat module of simple functions with at least *line_target* lines."""
    parts = [
        '"""Flat module used for Jedi throughput measurements."""',
        "import os",
        "",
    ]
    function_count = max(1, line_target // 4)
    for index in range(function_count):
        parts.append(f"def function_{index}(value: int = {index}) -> int:")
        parts.append(f'    """Return value plus {index}."""')
        parts.append(f"    return value + {index}")
        parts.append("")
    parts.append("result = function_0()")
    parts.append("")
    return "\n".join(parts)


def slice_bytes(source: str, start: int, length: int) -> str:
    """Decode the UTF-8 byte range used by semantic tokens."""
    return source.encode("utf-8")[start : start + length].decode("utf-8")


def python_language_config() -> dict[str, Any]:
    """Return a minimal valid Python language configuration dictionary."""
    return {
        "lang": "python",
        "extensions": ["py", "pyw", "pyi"],
        "styles": {
            "keyword": "#C586C0",
            "builtin": "#4FC1FF",
            "definition": "#DCDCAA",
            "class_def": "#4EC9B0",
            "string": "#CE9178",
            "number": "#B5CEA8",
            "comment": "#6A9955",
            "decorator": "#D7BA7D",
            "additional": "#569CD6",
            "operator": "#D4D4D4",
            "bracket": "#FFD700",
            "bracket_2": "#C678DD",
            "bracket_3": "#61AFEF",
            "exception": "#FF6B6B",
            "import": "#82AAFF",
            "variable": "#9CDCFE",
        },
        "keywords": {
            "keyword": [
                "def",
                "class",
                "return",
                "import",
                "from",
                "for",
                "with",
            ],
            "builtin": ["print"],
            "definition": [],
            "class_def": [],
            "string": [],
            "number": [],
            "comment": [],
            "decorator": [],
            "additional": ["self", "cls", "None"],
            "operator": [],
            "exception": [],
            "import": [],
        },
    }
