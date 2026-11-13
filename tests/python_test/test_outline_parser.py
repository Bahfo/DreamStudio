"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the AST-backed Python outline parser.
"""

from __future__ import annotations

import ast

import pytest

from editor.Ironica.plugins.python.outline_parser import parse_python_outline
from editor.utils.file_properties.outline import SymbolKind


def _names(result) -> list[str]:
    """Return the names of the root's direct children."""
    return [child.name for child in result.root.children]


def _child(result, name: str):
    """Return the first direct child with *name*."""
    for child in result.root.children:
        if child.name == name:
            return child
    raise AssertionError(f"missing outline child {name!r}")


class TestEmptyAndInvalidSource:
    """Tests for the parser's graceful-degradation paths."""

    @pytest.mark.parametrize("source", ["", "   ", "\n\n", "\t\n  "])
    def test_blank_source_yields_an_empty_file_root(self, source):
        """Blank buffers produce a file root without symbols."""
        result = parse_python_outline(source)

        assert result.language == "python"
        assert result.root.kind is SymbolKind.FILE
        assert result.root.name == ""
        assert result.root.children == []

    def test_syntax_error_yields_an_empty_file_root(self):
        """Invalid syntax degrades to an empty outline instead of raising."""
        result = parse_python_outline("def broken(:\n    pass\n")

        assert result.language == "python"
        assert result.root.children == []

    def test_partial_syntax_error_discards_all_symbols(self):
        """The parser is all-or-nothing on syntax errors."""
        result = parse_python_outline("class Valid:\n    pass\n\ndef broken(:\n")

        assert result.root.children == []


class TestImports:
    """Tests for import and from-import outline entries."""

    def test_plain_imports_are_listed_per_alias(self):
        """Each imported module becomes its own import node."""
        result = parse_python_outline("import os\nimport sys\n")

        assert _names(result) == ["os", "sys"]
        assert all(child.kind is SymbolKind.IMPORT for child in result.root.children)

    def test_aliased_import_uses_the_module_name(self):
        """Current contract: aliases are not reflected in the node name."""
        result = parse_python_outline("import numpy as np\n")

        assert _names(result) == ["numpy"]

    def test_from_import_joins_the_imported_names(self):
        """A from-import node lists its comma-separated names."""
        result = parse_python_outline(
            "from collections import OrderedDict, defaultdict\n"
        )

        node = _child(result, "OrderedDict, defaultdict")
        assert node.kind is SymbolKind.IMPORT
        assert (node.line_start, node.line_end) == (0, 0)

    def test_multiline_from_import_spans_all_lines(self):
        """Multi-line imports report their full source span."""
        source = "from package import (\n    first,\n    second,\n)\n"

        node = _child(parse_python_outline(source), "first, second")

        assert (node.line_start, node.line_end) == (0, 3)

    def test_imports_interleave_with_other_symbols_in_source_order(self):
        """Outline children preserve top-level source order."""
        source = "import os\nVALUE = 1\ndef f():\n    pass\nimport sys\n"

        assert _names(parse_python_outline(source)) == ["os", "VALUE", "f", "sys"]


class TestAssignments:
    """Tests for variable and constant extraction."""

    @pytest.mark.parametrize(
        ("statement", "name", "kind"),
        [
            ("VALUE = 1", "VALUE", SymbolKind.CONSTANT),
            ("value = 1", "value", SymbolKind.VARIABLE),
            ("MAX_SIZE: int = 10", "MAX_SIZE", SymbolKind.CONSTANT),
            ("name: str = 'x'", "name", SymbolKind.VARIABLE),
            ("MiXeD = 1", "MiXeD", SymbolKind.VARIABLE),
        ],
    )
    def test_assignments_are_classified_by_casing(self, statement, name, kind):
        """All-uppercase names are constants; everything else is a variable."""
        node = _child(parse_python_outline(statement + "\n"), name)

        assert node.kind is kind
        assert (node.line_start, node.line_end) == (0, 0)

    def test_annotation_is_recorded_as_detail(self):
        """Annotated assignments keep their annotation text."""
        node = _child(parse_python_outline("name: dict[str, int] = {}\n"), "name")

        assert node.detail == "dict[str, int]"

    def test_annotation_without_value_is_still_listed(self):
        """A bare annotated statement produces a variable node."""
        node = _child(parse_python_outline("pending: bool\n"), "pending")

        assert node.kind is SymbolKind.VARIABLE
        assert node.detail == "bool"

    def test_chained_assignment_creates_one_node_per_target(self):
        """Every simple name in a chained assignment is listed."""
        result = parse_python_outline("first = second = 1\n")

        assert _names(result) == ["first", "second"]

    def test_attribute_and_subscript_targets_are_ignored(self):
        """Only simple names can be represented in the outline."""
        result = parse_python_outline("obj.attr = 1\nitems[0] = 2\n")

        assert result.root.children == []

    def test_tuple_assignment_is_ignored(self):
        """Tuple unpacking is not a single named symbol."""
        assert parse_python_outline("left, right = 1, 2\n").root.children == []

    def test_multiline_annotation_reports_the_full_span(self):
        """A multi-line annotated assignment keeps its full extent."""
        source = "value: dict[\n    str,\n    int,\n] = {}\n"

        node = _child(parse_python_outline(source), "value")

        assert (node.line_start, node.line_end) == (0, 3)
        assert node.detail == "dict[\n    str,\n    int,\n]"


class TestFunctions:
    """Tests for top-level function and async-function signatures."""

    def test_simple_function_signature(self):
        """A plain function records its rendered signature."""
        node = _child(parse_python_outline("def greet(name):\n    pass\n"), "greet")

        assert node.kind is SymbolKind.FUNCTION
        assert node.detail == "def greet(name)"
        assert (node.line_start, node.line_end) == (0, 1)

    def test_async_function_is_marked_in_the_signature(self):
        """Async functions keep the ``async`` prefix."""
        node = _child(parse_python_outline("async def fetch():\n    pass\n"), "fetch")

        assert node.kind is SymbolKind.FUNCTION
        assert node.detail == "async def fetch()"

    def test_defaults_and_annotations_are_rendered(self):
        """Positional defaults and annotations appear in the detail."""
        source = "def f(count: int = 3, label: str = 'x') -> bool:\n    pass\n"

        node = _child(parse_python_outline(source), "f")

        assert node.detail == "def f(count: int=3, label: str='x') -> bool"

    def test_non_constant_default_is_elided(self):
        """Complex default expressions are abbreviated."""
        source = "def f(value=DEFAULT, other=CALL()):\n    pass\n"

        node = _child(parse_python_outline(source), "f")

        assert node.detail == "def f(value=..., other=...)"

    def test_varargs_kwargs_and_keyword_only_arguments(self):
        """Variadic and keyword-only parameters are all represented."""
        source = "def f(a, *args, flag: bool = True, **kwargs):\n    pass\n"

        node = _child(parse_python_outline(source), "f")

        assert node.detail == "def f(a, *args, flag: bool=..., **kwargs)"

    def test_keyword_only_separator_without_varargs(self):
        """A lone ``*`` marker is retained for keyword-only parameters."""
        source = "def f(a, *, flag: bool = True):\n    pass\n"

        node = _child(parse_python_outline(source), "f")

        assert node.detail == "def f(a, *, flag: bool=...)"

    def test_positional_only_arguments_are_rendered_without_slash(self):
        """Current contract: positional-only parameters merge into the list."""
        source = "def f(a, b, /, c):\n    pass\n"

        node = _child(parse_python_outline(source), "f")

        assert node.detail == "def f(a, b, c)"

    def test_multiline_signature_keeps_normalized_spacing(self):
        """Annotations spanning lines are preserved verbatim."""
        source = (
            "def f(\n"
            "    value: dict[\n"
            "        str,\n"
            "        int,\n"
            "    ],\n"
            ") -> tuple[int, str]:\n"
            "    pass\n"
        )

        node = _child(parse_python_outline(source), "f")

        assert "dict[\n        str,\n        int,\n    ]" in node.detail
        assert node.detail.endswith(") -> tuple[int, str]")

    def test_decorators_are_child_nodes(self):
        """Decorator names are attached to the function node."""
        source = "@first\n@second(arg)\n@module.third\ndef f():\n    pass\n"

        node = _child(parse_python_outline(source), "f")

        assert [child.name for child in node.children] == [
            "@first",
            "@second",
            "@third",
        ]
        assert all(child.kind is SymbolKind.DECORATOR for child in node.children)

    @pytest.mark.parametrize(
        ("decorator", "expected"),
        [
            ("@plain", "@plain"),
            ("@call(1, 2)", "@call"),
            ("@namespace.call()", "@call"),
            ("@(decorators[0])", "@..."),
        ],
    )
    def test_decorator_forms_are_normalized(self, decorator, expected):
        """Name, call, and attribute decorators are reduced to a label."""
        source = f"{decorator}\ndef f():\n    pass\n"

        node = _child(parse_python_outline(source), "f")

        assert node.children[0].name == expected


class TestClasses:
    """Tests for class nodes, bases, methods, and nesting."""

    def test_class_with_bases_records_the_base_list(self):
        """Base expressions are shown in the class detail."""
        source = "class Widget(Base, mixins.Other[T]):\n    pass\n"

        node = _child(parse_python_outline(source), "Widget")

        assert node.kind is SymbolKind.CLASS
        assert node.detail == "(Base, mixins.Other[T])"
        assert (node.line_start, node.line_end) == (0, 1)

    def test_class_without_bases_has_empty_detail(self):
        """A base-less class has no detail suffix."""
        node = _child(parse_python_outline("class Plain:\n    pass\n"), "Plain")

        assert node.detail == ""

    def test_methods_are_nested_under_the_class(self):
        """Methods are ``METHOD`` children of the class node."""
        source = "class C:\n    def method(self):\n        pass\n"

        node = _child(parse_python_outline(source), "C")

        assert [child.kind for child in node.children] == [SymbolKind.METHOD]
        assert node.children[0].detail == "def method(self)"

    def test_async_method_is_a_method(self):
        """Async methods use the method kind, not function."""
        source = "class C:\n    async def method(self):\n        pass\n"

        node = _child(parse_python_outline(source), "C")

        assert node.children[0].kind is SymbolKind.METHOD
        assert node.children[0].detail.startswith("async def method")

    def test_class_attributes_are_nested(self):
        """Class-level assignments become constant/variable children."""
        source = "class C:\n    LIMIT = 3\n    name: str = 'x'\n"

        node = _child(parse_python_outline(source), "C")

        assert [(child.name, child.kind) for child in node.children] == [
            ("LIMIT", SymbolKind.CONSTANT),
            ("name", SymbolKind.VARIABLE),
        ]
        assert node.children[1].detail == "str"

    def test_nested_classes_are_nested_nodes(self):
        """Nested classes keep their hierarchy."""
        source = (
            "class Outer:\n"
            "    class Inner:\n"
            "        def method(self):\n"
            "            pass\n"
        )

        outer = _child(parse_python_outline(source), "Outer")
        inner = outer.children[0]

        assert inner.kind is SymbolKind.CLASS
        assert inner.name == "Inner"
        assert inner.children[0].kind is SymbolKind.METHOD

    def test_class_decorators_are_recorded(self):
        """Class decorators are child nodes."""
        source = "@register\n@config(flag=True)\nclass C:\n    pass\n"

        node = _child(parse_python_outline(source), "C")

        assert [child.name for child in node.children] == ["@register", "@config"]

    def test_method_decorators_are_nested_under_the_method(self):
        """Method decorators belong to the method node."""
        source = (
            "class C:\n"
            "    @property\n"
            "    def label(self) -> str:\n"
            "        return ''\n"
        )

        method = _child(parse_python_outline(source), "C").children[0]

        assert method.children[0].name == "@property"
        assert method.children[0].kind is SymbolKind.DECORATOR


class TestPositionsAndEncoding:
    """Tests for line/column reporting across encodings and line endings."""

    def test_lines_are_zero_based_and_columns_preserve_indentation(self):
        """Positions follow the editor's 0-based row contract."""
        source = "class C:\n    def method(self):\n        pass\n"

        cls = _child(parse_python_outline(source), "C")
        method = cls.children[0]

        assert (cls.line_start, cls.line_end, cls.col_start) == (0, 2, 0)
        assert (method.line_start, method.line_end, method.col_start) == (1, 2, 4)

    def test_unicode_annotations_are_preserved(self):
        """Non-ASCII identifiers and annotations survive parsing."""
        source = "def grüß(name: 'ünïcode') -> 'str':\n    pass\n"

        node = _child(parse_python_outline(source), "grüß")

        assert node.detail == "def grüß(name: 'ünïcode') -> 'str'"

    def test_unicode_before_annotations_does_not_corrupt_offsets(self):
        """Byte offsets and character offsets are not confused."""
        source = "marker = 'é'\ndef f(value: int = 1) -> str:\n    pass\n"

        node = _child(parse_python_outline(source), "f")

        assert node.detail == "def f(value: int=1) -> str"

    def test_crlf_source_is_parsed(self):
        """Windows line endings do not shift symbol spans."""
        source = "class C:\r\n    def method(self):\r\n        pass\r\n"

        cls = _child(parse_python_outline(source), "C")

        assert (cls.line_start, cls.line_end) == (0, 2)
        assert cls.children[0].detail == "def method(self)"

    def test_no_trailing_newline_is_supported(self):
        """The final statement is addressable without a trailing newline."""
        node = _child(parse_python_outline("def last():\n    pass"), "last")

        assert (node.line_start, node.line_end) == (0, 1)


class TestSourceSegmentRegression:
    """Regression coverage for the outline parser's O(file size) segment lookup.

    The original implementation called ``ast.get_source_segment`` for every
    annotation and base, re-splitting the whole source each time. On a 10k-line
    annotated module that took ~23 seconds.
    """

    def test_parser_never_calls_ast_get_source_segment(self, monkeypatch):
        """Annotation and base rendering must not use the slow AST helper."""
        source = (
            "class Widget(Base, mixins.Other[T]):\n"
            "    value: dict[str, int] = {}\n"
            "    def method(self, name: str = 'x') -> tuple[int, str]:\n"
            "        pass\n"
        )

        def forbidden(*args, **kwargs):
            raise AssertionError("ast.get_source_segment must not be used")

        monkeypatch.setattr(ast, "get_source_segment", forbidden)

        result = parse_python_outline(source)

        widget = _child(result, "Widget")
        assert widget.detail == "(Base, mixins.Other[T])"
        assert widget.children[0].detail == "dict[str, int]"
        assert (
            widget.children[1].detail
            == "def method(self, name: str='x') -> tuple[int, str]"
        )

    def test_segments_match_ast_get_source_segment_semantics(self):
        """The fast segment helper preserves the documented AST semantics."""
        source = (
            "class C(\n"
            "    Base,\n"
            "    Other[T],\n"
            "):\n"
            "    value: dict[\n"
            "        str,\n"
            "        int,\n"
            "    ] = {}\n"
        )
        tree = ast.parse(source)
        expected = {
            node: ast.get_source_segment(source, node)
            for node in ast.walk(tree)
            if getattr(node, "lineno", None) is not None
        }

        result = parse_python_outline(source)

        cls = _child(result, "C")
        annotation = cls.children[0].detail
        assert annotation == expected[tree.body[0].body[0].annotation]
        assert "Base" in cls.detail and "Other[T]" in cls.detail

    def test_very_long_annotation_does_not_drop_detail(self):
        """Long annotation text is fully preserved."""
        annotation = "dict[" + ", ".join(f"Key{i}" for i in range(40)) + "]"
        source = f"value: {annotation} = {{}}\n"

        node = _child(parse_python_outline(source), "value")

        assert node.detail == annotation
