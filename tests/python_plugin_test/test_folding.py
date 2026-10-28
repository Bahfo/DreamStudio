"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for indentation-based Python fold-region computation.
"""

from __future__ import annotations

import pytest

from editor.Ironica.plugins.python.folding import (
    _apply_import_fold_text,
    _indent_level,
    _is_block_header,
    compute_fold_regions,
)
from editor.Ironica.utils.folding import FoldRegion


def _spans(source: str) -> list[tuple[int, int, str]]:
    """Return ``(start, end, kind)`` for every fold region."""
    return [
        (region.start_line, region.end_line, region.kind)
        for region in compute_fold_regions(source)
    ]


class TestEmptyAndTrivialInput:
    """Tests for inputs that cannot produce fold regions."""

    @pytest.mark.parametrize("source", ["", "\n\n", "   \n"])
    def test_blank_source_has_no_regions(self, source):
        """Blank buffers produce nothing."""
        assert compute_fold_regions(source) == []

    @pytest.mark.parametrize(
        "source",
        [
            "x = 1\ny = 2\n",
            "if True:\n    pass\n",
            "while True:\n    pass\n",
            "for item in items:\n    pass\n",
            "try:\n    pass\n",
        ],
    )
    def test_non_python_block_statements_are_not_folded(self, source):
        """Only imports, classes, and functions are fold candidates."""
        assert compute_fold_regions(source) == []

    def test_single_line_definition_has_no_region(self):
        """A block header with no body lines is not foldable."""
        assert _spans("def f(): pass\n") == []
        assert _spans("class C: pass\n") == []

    def test_comments_without_blocks_have_no_regions(self):
        """A comment-only buffer is not foldable."""
        assert compute_fold_regions("# first\n# second\n") == []

    def test_bare_import_has_no_region(self):
        """A single import statement is not a foldable range."""
        assert _spans("import os\n") == []


class TestFunctionFolding:
    """Tests for def/async def fold regions."""

    def test_function_body_span(self):
        """A function region starts at the header and ends at its last body line."""
        source = "def f(x):\n    a = 1\n    return a\n\nafter = 2\n"

        assert _spans(source) == [(0, 2, "function")]

    def test_async_function_is_a_function_region(self):
        """Async definitions use the function kind."""
        assert _spans("async def fetch():\n    pass\n") == [(0, 1, "function")]

    def test_multiline_signature_starts_at_the_def_line(self):
        """A wrapped signature still begins at the ``def`` line."""
        source = "def f(\n    a,\n    b,\n):\n    return a\n"

        assert _spans(source) == [(0, 4, "function")]

    def test_indented_definition_uses_its_own_indent(self):
        """Nested functions are detected at their own indentation."""
        source = "def outer():\n    def inner():\n        return 1\n    return inner\n"

        assert _spans(source) == [(0, 3, "function"), (1, 2, "function")]

    def test_tab_indentation_is_supported(self):
        """Tabs are treated as four-space indentation steps."""
        source = "\tdef f():\n\t\tpass\n"

        assert _spans(source) == [(0, 1, "function")]

    def test_blank_line_inside_body_is_included(self):
        """A blank separator between body statements stays inside the fold."""
        source = "def f():\n    a = 1\n\n    b = 2\n"

        assert _spans(source) == [(0, 3, "function")]

    def test_trailing_blank_line_before_dedent_is_excluded(self):
        """A blank line before a dedented statement is outside the fold."""
        source = "def f():\n    a = 1\n\nvalue = 2\n"

        assert _spans(source) == [(0, 1, "function")]

    def test_trailing_comment_inside_body_is_included(self):
        """An indented trailing comment belongs to the function region."""
        source = "def f():\n    a = 1\n    # tail\n"

        assert _spans(source) == [(0, 2, "function")]

    def test_dedented_comment_ends_the_region(self):
        """A comment at column zero is outside the function."""
        source = "def f():\n    a = 1\n# outside\n"

        assert _spans(source) == [(0, 1, "function")]

    @pytest.mark.parametrize(
        "source",
        [
            'text = """\ndef fake():\n    pass\n"""\n',
            "text = '''\ndef fake():\n    pass\n'''\n",
        ],
    )
    def test_definitions_inside_strings_are_ignored(self, source):
        """Triple-quoted text never produces fold regions."""
        assert compute_fold_regions(source) == []

    def test_definitions_after_multiline_string_are_found(self):
        """String tracking resets after the closing triple quote."""
        source = 'text = """\ndef fake():\n    pass\n"""\ndef real():\n    pass\n'

        assert _spans(source) == [(4, 5, "function")]


class TestClassFolding:
    """Tests for class fold regions."""

    def test_class_body_span(self):
        """A class region covers its indented body."""
        source = "class C:\n    def m(self):\n        pass\n\n    x = 1\n\nafter = 1\n"

        assert _spans(source) == [(0, 4, "class"), (1, 2, "function")]

    def test_class_with_multiline_bases(self):
        """A wrapped base list still starts at the class line."""
        source = "class C(\n    Base,\n):\n    x = 1\n"

        assert _spans(source) == [(0, 3, "class")]

    def test_class_with_only_a_docstring_is_foldable(self):
        """Docstrings count as body content."""
        source = 'class C:\n    """Docs."""\n'

        assert _spans(source) == [(0, 1, "class")]

    def test_nested_class_and_method_regions(self):
        """Nested containers are sorted by their start line."""
        source = (
            "class Outer:\n"
            "    class Inner:\n"
            "        def method(self):\n"
            "            pass\n"
        )

        assert _spans(source) == [
            (0, 3, "class"),
            (1, 3, "class"),
            (2, 3, "function"),
        ]


class TestDecorators:
    """Tests for decorator handling in fold regions."""

    def test_decorator_is_included_in_the_region(self):
        """A directly preceding decorator extends the start line."""
        source = "@dec\ndef f():\n    pass\n"

        assert _spans(source) == [(0, 2, "function")]

    def test_blank_and_comment_lines_between_decorator_and_def_are_included(self):
        """Blank/comment lines between a decorator and def stay in the fold."""
        source = "@dec\n\n# note\ndef f():\n    pass\n"

        assert _spans(source) == [(0, 4, "function")]

    def test_multiple_decorators_extend_the_region(self):
        """Every adjacent decorator is included."""
        source = "@first\n@second(arg)\nclass C:\n    pass\n"

        assert _spans(source) == [(0, 3, "class")]

    def test_multiline_decorator_is_not_included(self):
        """Current contract: wrapped decorator calls are not detected."""
        source = "@dec(\n    1,\n)\ndef f():\n    pass\n"

        assert _spans(source) == [(3, 4, "function")]


class TestImportFolding:
    """Tests for import grouping."""

    def test_consecutive_imports_form_one_region(self):
        """Plain, aliased, and from-imports group together."""
        source = "import os\nimport sys\nfrom x import y\n\nvalue = 1\n"

        assert _spans(source) == [(0, 2, "import")]

    def test_single_import_group_requires_at_least_two_lines(self):
        """One import line is not foldable."""
        assert _spans("import os\n\nimport sys\n") == []

    def test_blank_line_ends_the_import_group(self):
        """A blank line at the same indentation terminates grouping."""
        source = "import os\nimport sys\n\n# comment\nvalue = 1\n"

        assert _spans(source) == [(0, 1, "import")]

    def test_indented_comment_does_not_end_the_group(self):
        """A comment indented under the imports is included."""
        source = "import os\n    # odd\nimport sys\n"

        assert _spans(source) == [(0, 2, "import")]

    def test_imports_inside_a_function_are_nested(self):
        """Indented imports form their own import region."""
        source = "def f():\n    import os\n    import sys\n    return 1\n"

        assert _spans(source) == [(0, 3, "function"), (1, 2, "import")]

    def test_multiline_parenthesised_import_is_not_folded(self):
        """Current contract: a wrapped from-import is not a fold region."""
        source = "from a import (\n    b,\n    c,\n)\n\nx = 1\n"

        assert _spans(source) == []

    def test_decorated_import_region_starts_at_the_decorator(self):
        """Decorator skip logic applies before import classification."""
        source = "@decorator\nimport os\nimport sys\n"

        assert _spans(source) == [(0, 2, "import")]


class TestRegionModel:
    """Tests for the returned ``FoldRegion`` objects."""

    def test_regions_are_sorted_and_unique(self):
        """Regions are deterministic, sorted, and have unique ids."""
        source = (
            "class C:\n"
            "    def first(self):\n"
            "        pass\n"
            "    def second(self):\n"
            "        pass\n"
            "def tail():\n"
            "    pass\n"
        )

        regions = compute_fold_regions(source)

        assert [region.start_line for region in regions] == [0, 1, 3, 5]
        assert len({region.uid for region in regions}) == len(regions)

    def test_region_defaults(self):
        """Computed regions start unfolded with a descriptive uid."""
        region = compute_fold_regions("def f():\n    pass\n")[0]

        assert region.folded is False
        assert region.uid == "function:0:1"

    def test_repeated_calls_return_equal_regions(self):
        """Fold computation has no hidden mutable state."""
        source = "class C:\n    def m(self):\n        pass\n"

        assert compute_fold_regions(source) == compute_fold_regions(source)

    def test_empty_result_is_a_list(self):
        """Callers can always iterate the result."""
        assert compute_fold_regions("") == []
        assert isinstance(compute_fold_regions(""), list)


class TestHeaderClassification:
    """Focused tests for the private header/indentation helpers."""

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("import os", "import"),
            ("  from package import name", "import"),
            ("    import os", "import"),
            ("class Widget:", "class"),
            ("  class Nested(Base):", "class"),
            ("def function():", "function"),
            ("async def fetch():", "function"),
            ("  async def method(self):", "function"),
            ("@decorator", None),
            ("value = 1", None),
            ("", None),
            ("# class NotAClass:", None),
        ],
    )
    def test_header_classification(self, line, expected):
        """Header detection is indentation-insensitive and prefix-based."""
        assert _is_block_header(line) == expected

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("", 0),
            ("value", 0),
            (" value", 1),
            ("    value", 4),
            ("\tvalue", 4),
            ("\t\tvalue", 8),
            (" \tvalue", 5),
            ("    ", 4),
        ],
    )
    def test_indent_level_counts_spaces_and_expands_tabs(self, line, expected):
        """Each tab contributes four columns."""
        assert _indent_level(line) == expected


class TestImportFoldLabels:
    """Tests for the editor hook that labels import folds."""

    class _Editor:
        def __init__(self, supports_text: bool = True) -> None:
            self.calls = []
            self.supports_text = supports_text

        def _setup_folding_display_text(self):
            self.calls.append("setup")

        def set_custom_import_fold_text(self, start_line, count):
            self.calls.append((start_line, count))

    def test_setup_is_called_even_without_import_regions(self):
        """Display-text setup runs for every editor that supports it."""
        editor = self._Editor()

        _apply_import_fold_text(editor, [FoldRegion(0, 2, kind="function")])

        assert editor.calls == ["setup"]

    def test_import_region_receives_its_line_count(self):
        """The label hook receives the start line and inclusive count."""
        editor = self._Editor()

        _apply_import_fold_text(
            editor,
            [
                FoldRegion(0, 2, kind="import"),
                FoldRegion(5, 9, kind="function"),
                FoldRegion(10, 12, kind="import"),
            ],
        )

        assert editor.calls == ["setup", (0, 3), (10, 3)]

    def test_editor_without_label_support_is_tolerated(self):
        """Only the optional setup hook is required."""
        editor = self._Editor(supports_text=False)
        editor.set_custom_import_fold_text = None

        _apply_import_fold_text(editor, [FoldRegion(0, 2, kind="import")])

        assert editor.calls == ["setup"]
