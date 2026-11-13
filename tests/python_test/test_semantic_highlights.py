"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the two-path Python lexical/semantic highlighting pipeline.
"""

from __future__ import annotations

import ast
import tokenize

import pytest

from editor.Ironica.plugins.python import semantic_highlights as highlights
from editor.Ironica.plugins.python.semantic_highlights import (
    PythonSemanticProvider,
    _build_exclusions_from_stream,
    _build_line_index,
    _build_line_offsets,
    _in_exclusion,
    _iter_param_args,
    _tokenize_char_to_byte,
)
from editor.Ironica.utils.highlighting_api import Token, TokenStyle
from tests.python_plugin_test.helpers import slice_bytes


def _lexical_texts(
    provider: PythonSemanticProvider, source: str
) -> list[tuple[str, str]]:
    """Return ``(kind, text)`` for every lexical token."""
    return [
        (token.kind, slice_bytes(source, token.start, token.length))
        for token in provider.get_tokens(source)
    ]


def _kinds_at(provider: PythonSemanticProvider, source: str) -> dict[str, list[str]]:
    """Map each highlighted text to the kinds reported for it."""
    raw = source.encode("utf-8")
    result: dict[str, list[str]] = {}
    for token in provider._cache_semantic:
        text = raw[token.start : token.start + token.length].decode("utf-8")
        result.setdefault(text, []).append(token.kind)
    return result


class TestEmptyInput:
    """Tests for blank-buffer shortcuts."""

    @pytest.mark.parametrize("source", ["", " ", "\n\n", "\t"])
    def test_blank_source_has_no_tokens(self, source):
        """Whitespace-only buffers produce no lexical or semantic tokens."""
        provider = PythonSemanticProvider()

        assert provider.get_tokens(source) == []
        assert provider.get_semantic_ranges(source) == []

    def test_blank_source_does_not_replace_the_cache(self):
        """A blank query must not evict a previously computed buffer."""
        provider = PythonSemanticProvider()
        source = "value = 1\n"
        provider.get_tokens(source)
        cached_text = provider._cache_text

        assert provider.get_tokens("   ") == []
        assert provider._cache_text == cached_text


class TestLexicalTokens:
    """Tests for the tokenize-backed lexical pass."""

    def test_keywords_strings_numbers_and_comments(self):
        """The lexical pass classifies the core token categories."""
        source = 'def f():\n    text = "value"  # note\n    return 42\n'
        provider = PythonSemanticProvider()

        tokens = _lexical_texts(provider, source)

        assert ("keyword", "def") in tokens
        assert ("keyword", "return") in tokens
        assert ("string", '"value"') in tokens
        assert ("comment", "# note") in tokens
        assert ("number", "42") in tokens

    def test_names_are_not_emitted_by_the_lexer(self):
        """Plain identifiers are left to the semantic pass."""
        provider = PythonSemanticProvider()

        tokens = _lexical_texts(provider, "value = other\n")

        assert all(kind != "name" for kind, _text in tokens)

    def test_operators_are_grouped_into_single_tokens(self):
        """Multi-character operators keep their full width."""
        provider = PythonSemanticProvider()

        tokens = _lexical_texts(provider, "x = a // b ** c\n")

        texts = {text for kind, text in tokens if kind == "operator"}
        assert {"=", "//", "**"} <= texts

    def test_decorator_at_sign_has_its_own_kind(self):
        """``@`` is styled as a decorator rather than a generic operator."""
        provider = PythonSemanticProvider()

        tokens = _lexical_texts(provider, "@decorator\ndef f():\n    pass\n")

        assert ("decorator", "@") in tokens
        assert ("operator", "@") not in tokens

    def test_triple_quoted_string_is_one_token(self):
        """A multi-line string is a single lexical span."""
        source = 'text = """first\nsecond\nthird"""\n'
        provider = PythonSemanticProvider()

        string_tokens = [
            text for kind, text in _lexical_texts(provider, source) if kind == "string"
        ]

        assert string_tokens == ['"""first\nsecond\nthird"""']

    def test_fstrings_are_styled_as_strings(self):
        """F-string segments participate in the string token category."""
        provider = PythonSemanticProvider()

        tokens = _lexical_texts(provider, 'text = f"value {name}"\n')

        assert any(kind == "string" for kind, _text in tokens)

    def test_comments_win_over_embedded_keywords(self):
        """Keywords inside comments are not separately tokenized."""
        provider = PythonSemanticProvider()

        tokens = _lexical_texts(provider, "# def class return\nvalue = 1\n")

        assert ("comment", "# def class return") in tokens
        assert ("keyword", "def") not in tokens

    def test_byte_offsets_correct_for_unicode_prefixes(self):
        """Offsets are UTF-8 byte positions, not character indices."""
        source = 'label = "héllo"\nvalue = 1\n'
        provider = PythonSemanticProvider()

        tokens = _lexical_texts(provider, source)

        assert ("string", '"héllo"') in tokens
        assert ("number", "1") in tokens

    def test_every_token_has_a_positive_length_and_hex_colour(self):
        """Lexical tokens are well formed and styled."""
        provider = PythonSemanticProvider()

        tokens = provider.get_tokens('def f(x: int = 1):\n    return "text"\n')

        assert tokens
        assert all(token.length > 0 for token in tokens)
        assert all(token.start >= 0 for token in tokens)
        assert all(
            token.style.colour.startswith("#") and len(token.style.colour) == 7
            for token in tokens
        )


class TestSemanticTokens:
    """Tests for AST-derived overlay tokens."""

    def test_function_and_parameter_names(self):
        """Definitions and parameters receive semantic highlights."""
        source = "def greet(name, count=1):\n    return name\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["greet"] == ["function"]
        assert kinds["name"] == ["parameter"]
        assert kinds["count"] == ["parameter"]

    def test_self_and_cls_are_distinct_from_parameters(self):
        """``self``/``cls`` use the dedicated receiver kind."""
        source = (
            "class C:\n"
            "    def method(self, value):\n"
            "        return self.value + value\n"
        )
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["C"] == ["class"]
        assert kinds["method"] == ["function"]
        assert kinds["self"] == ["self", "self"]
        assert kinds["value"] == ["parameter"]

    def test_async_function_is_highlighted(self):
        """Async definitions use the same function styling."""
        source = "async def fetch(url):\n    return url\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        assert _kinds_at(provider, source)["fetch"] == ["function"]

    def test_lambda_parameters_are_highlighted(self):
        """Lambda arguments are parameters without a name token."""
        source = "callback = lambda item, index: item + index\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["item"] == ["parameter"]
        assert kinds["index"] == ["parameter"]

    def test_class_name_is_highlighted(self):
        """Class definitions receive the class kind."""
        provider = PythonSemanticProvider()
        source = "class Widget(Base):\n    pass\n"
        provider.get_semantic_ranges(source)

        assert _kinds_at(provider, source)["Widget"] == ["class"]

    def test_plain_import_uses_the_module_kind(self):
        """Imported dotted modules are highlighted as module names."""
        source = "import os.path\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        assert _kinds_at(provider, source)["os.path"] == ["module"]

    def test_from_import_module_and_names(self):
        """The source module and each imported name are highlighted."""
        source = "from collections import OrderedDict, defaultdict\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["collections"] == ["module"]
        assert kinds["OrderedDict"] == ["definition"]
        assert kinds["defaultdict"] == ["definition"]

    def test_star_import_skips_the_wildcard(self):
        """``*`` is not an importable symbol and is not highlighted."""
        source = "from package import *\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        assert "*" not in _kinds_at(provider, source)

    def test_assignment_and_annotated_assignment(self):
        """Assignments highlight every simple target."""
        source = "MAX = 1\nname: str = 'x'\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["MAX"] == ["variable"]
        assert kinds["name"] == ["variable"]

    def test_chained_assignment_highlights_both_targets(self):
        """Chained assignment targets are all variables."""
        source = "left = right = 1\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["left"] == ["variable"]
        assert kinds["right"] == ["variable"]

    def test_self_attribute_assignment_highlights_the_attribute(self):
        """``self.attr =`` highlights ``attr`` as a variable."""
        source = "class C:\n    def set(self, value):\n        self.attr = value\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["attr"] == ["variable"]

    def test_plain_object_attribute_assignment_is_not_highlighted(self):
        """Only ``self``/``cls`` receivers produce variable tokens."""
        source = "obj.attr = 1\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        assert "attr" not in _kinds_at(provider, source)

    def test_for_and_with_targets(self):
        """Loop and context-manager bindings are variables."""
        source = 'for item in values:\n    pass\nwith open("x") as handle:\n    pass\n'
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["item"] == ["variable"]
        assert kinds["handle"] == ["variable"]

    def test_exception_type_and_alias(self):
        """Exception classes and their ``as`` aliases are highlighted."""
        source = "try:\n    pass\nexcept ValueError as error:\n    pass\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["ValueError"] == ["exception"]
        assert kinds["error"] == ["variable"]

    def test_exception_without_alias(self):
        """A bare except clause still highlights the exception type."""
        source = "try:\n    pass\nexcept RuntimeError:\n    pass\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        assert _kinds_at(provider, source)["RuntimeError"] == ["exception"]

    def test_string_contents_are_not_highlighted(self):
        """Identifiers that only appear inside strings are excluded."""
        source = 'def f():\n    return "def hidden(value): pass"\n'
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["f"] == ["function"]
        assert "hidden" not in kinds

    def test_comment_contents_are_not_highlighted(self):
        """Identifiers inside comments are excluded."""
        source = "# def hidden(value): pass\nvalue = 1\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert kinds["value"] == ["variable"]
        assert "hidden" not in kinds

    def test_attribute_reads_are_not_emitted(self):
        """Attribute reads such as ``self.value`` are left to the editor."""
        source = "class C:\n    def read(self):\n        return self.value\n"
        provider = PythonSemanticProvider()
        provider.get_semantic_ranges(source)

        kinds = _kinds_at(provider, source)

        assert "value" not in kinds
        assert kinds["self"] == ["self", "self"]

    def test_ranges_are_sorted_and_non_overlapping(self):
        """Semantic overlays are deterministic and never overlap."""
        source = (
            "import os\n"
            "class C:\n"
            "    def method(self, value):\n"
            "        result = value\n"
            "        return self.value\n"
        )
        provider = PythonSemanticProvider()

        ranges = provider.get_semantic_ranges(source)

        assert ranges == sorted(ranges, key=lambda item: item[0])
        previous_end = -1
        for start, length, _colour in ranges:
            assert start >= previous_end
            previous_end = start + length

    def test_unicode_identifiers_have_byte_accurate_spans(self):
        """Unicode definitions and parameters are measured in UTF-8 bytes."""
        source = 'x = "héllo"\ndef grüß(name):\n    return name\n'
        provider = PythonSemanticProvider()

        ranges = provider.get_semantic_ranges(source)
        highlighted = [
            slice_bytes(source, start, length) for start, length, _colour in ranges
        ]

        assert highlighted == ["x", "grüß", "name"]

    def test_colours_come_from_the_resolved_style_map(self):
        """Semantic colours match the provider's token style table."""
        provider = PythonSemanticProvider()
        source = "def f(value):\n    return value\n"

        ranges = provider.get_semantic_ranges(source)
        styles = provider._get_styles()

        colours = {
            slice_bytes(source, start, length): colour
            for start, length, colour in ranges
        }
        assert colours["f"] == styles["function"].colour
        assert colours["value"] == styles["parameter"].colour


class TestSyntaxFallback:
    """Tests for the lexical fallback used when ``ast.parse`` fails."""

    def test_def_name_is_still_highlighted(self):
        """A broken definition still receives a function-coloured name."""
        provider = PythonSemanticProvider()

        provider.get_semantic_ranges("def broken(:\n    pass\n")

        assert _kinds_at(provider, "def broken(:\n    pass\n")["broken"] == ["function"]

    def test_class_name_is_still_highlighted(self):
        """A broken class still receives a class-coloured name."""
        source = "class Broken(:\n    pass\n"
        provider = PythonSemanticProvider()

        provider.get_semantic_ranges(source)

        assert _kinds_at(provider, source)["Broken"] == ["class"]

    def test_import_names_are_still_highlighted(self):
        """Import statements are highlighted without a valid AST."""
        source = "import os\nfrom package import name\nvalue = (\n"
        provider = PythonSemanticProvider()

        provider.get_semantic_ranges(source)
        kinds = _kinds_at(provider, source)

        assert kinds["os"] == ["definition"]
        assert kinds["package"] == ["definition"]
        assert kinds["name"] == ["definition"]

    def test_self_is_still_highlighted(self):
        """The receiver has a dedicated style even in fallback mode."""
        source = "def broken(:\n    self.value = 1\n"
        provider = PythonSemanticProvider()

        provider.get_semantic_ranges(source)

        assert _kinds_at(provider, source)["self"] == ["self"]

    def test_fallback_does_not_raise_on_unbalanced_source(self):
        """Deeply broken source is tolerated."""
        source = "def f((((:\n    '''unterminated\n"

        provider = PythonSemanticProvider()

        assert isinstance(provider.get_semantic_ranges(source), list)

    def test_fallback_marks_parameters_inside_parentheses(self):
        """Names inside a broken signature are parameter-coloured."""
        source = "def broken(:\n    pass\n"
        provider = PythonSemanticProvider()

        provider.get_semantic_ranges(source)

        assert _kinds_at(provider, source)["pass"] == ["parameter"]


class TestCacheLifecycle:
    """Tests for per-provider caching and invalidation."""

    def test_repeated_tokens_return_the_same_cached_list(self):
        """The lexical list is cached by object identity."""
        provider = PythonSemanticProvider()
        source = "value = 1\n"

        assert provider.get_tokens(source) is provider.get_tokens(source)

    def test_repeated_semantic_ranges_are_equal(self):
        """The semantic overlay is stable across calls."""
        provider = PythonSemanticProvider()
        source = "def f(value):\n    return value\n"

        first = provider.get_semantic_ranges(source)
        second = provider.get_semantic_ranges(source)

        assert first == second

    def test_changed_source_recomputes_the_cache(self):
        """A new buffer replaces the cached token stream."""
        provider = PythonSemanticProvider()
        provider.get_tokens("first = 1\n")

        assert provider.get_tokens("second = 2\n")
        assert provider._cache_text == "second = 2\n"

    def test_switching_back_recomputes(self):
        """Only the most recent buffer is cached."""
        provider = PythonSemanticProvider()
        first = provider.get_tokens("first = 1\n")
        provider.get_tokens("second = 2\n")

        assert provider.get_tokens("first = 1\n") == first
        assert provider._cache_text == "first = 1\n"

    def test_invalidate_clears_text_tokens_and_styles(self):
        """invalidate_cache drops every cached layer."""
        provider = PythonSemanticProvider()
        provider.get_tokens("value = 1\n")
        assert provider._cache_text

        provider.invalidate_cache()

        assert provider._cache_text == ""
        assert provider._cache_lexical == []
        assert provider._cache_semantic == []
        assert provider._styles == {}

    def test_invalidate_is_idempotent(self):
        """Invalidating an unused provider is safe."""
        provider = PythonSemanticProvider()

        provider.invalidate_cache()
        provider.invalidate_cache()

        assert provider.get_tokens("value = 1\n")

    def test_styles_are_resolved_once(self):
        """The resolved style table is cached between calls."""
        provider = PythonSemanticProvider()

        assert provider._get_styles() is provider._get_styles()

    def test_invalidate_forces_style_resolution(self):
        """After invalidation a fresh style table is produced."""
        provider = PythonSemanticProvider()
        first = provider._get_styles()

        provider.invalidate_cache()
        second = provider._get_styles()

        assert first is not second
        assert first == second

    def test_theme_registry_change_is_picked_up_after_invalidation(self, monkeypatch):
        """Theme changes only take effect after an explicit invalidation."""
        provider = PythonSemanticProvider()
        provider._get_styles()

        monkeypatch.setattr(
            highlights,
            "styles_from_config",
            lambda config: {"custom": TokenStyle(1, "#123456")},
        )
        provider.invalidate_cache()

        assert provider._get_styles() == {"custom": TokenStyle(1, "#123456")}


class TestModuleLevelApi:
    """Tests for the singleton entry points used by the language provider."""

    def test_get_semantic_highlights_returns_ranges(self):
        """The module-level function returns semantic ranges."""
        highlights.invalidate_semantic_cache()

        ranges = highlights.get_semantic_highlights("def f():\n    pass\n")

        assert any(
            start == 4 and length == 1 and colour.startswith("#")
            for start, length, colour in ranges
        )

    def test_invalidating_drops_the_legacy_cache(self):
        """The module-level invalidation clears the singleton provider."""
        highlights.get_semantic_highlights("value = 1\n")
        assert highlights._legacy_provider._cache_text

        highlights.invalidate_semantic_cache()

        assert highlights._legacy_provider._cache_text == ""
        assert highlights._legacy_provider._styles == {}

    def test_blank_module_input_is_empty(self):
        """The module-level function honours the blank-buffer shortcut."""
        assert highlights.get_semantic_highlights("   ") == []


class TestInternalHelpers:
    """Focused tests for the module's byte-offset and span helpers."""

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("", [0, 0]),
            ("abc", [0, 3]),
            ("a\nb", [0, 2, 3]),
            ("a\nb\n", [0, 2, 4]),
            ("é", [0, 2]),
            ("é\n", [0, 3]),
            ("aé\nb\n", [0, 4, 6]),
        ],
    )
    def test_line_offsets_are_utf8_byte_positions(self, source, expected):
        """Line starts are cumulative UTF-8 byte offsets."""
        assert _build_line_offsets(source) == expected

    def test_char_to_byte_clamps_ascii_columns(self):
        """An over-long ASCII column is clamped to the line width."""
        assert _tokenize_char_to_byte([0, 0], "abc", 1, 99) == 3

    def test_char_to_byte_converts_unicode_columns(self):
        """Unicode character columns are converted to byte widths."""
        assert _tokenize_char_to_byte([0, 0], "héllo", 1, 2) == 3

    def test_char_to_byte_rejects_invalid_rows(self):
        """Out-of-range rows return ``-1``."""
        assert _tokenize_char_to_byte([0], "abc", 0, 0) == -1
        assert _tokenize_char_to_byte([0], "abc", 2, 0) == -1

    @pytest.mark.parametrize(
        ("pos", "length", "expected"),
        [
            (0, 5, False),
            (4, 1, False),
            (5, 5, True),
            (9, 2, True),
            (10, 2, False),
            (12, 1, False),
        ],
    )
    def test_exclusion_overlap_semantics(self, pos, length, expected):
        """Exclusion is a half-open interval overlap test."""
        assert _in_exclusion(pos, length, [(5, 10)]) is expected

    def test_exclusion_with_empty_table(self):
        """An empty exclusion table never excludes anything."""
        assert _in_exclusion(0, 5, []) is False

    def test_exclusion_uses_binary_search_order(self):
        """Multiple sorted spans are searched correctly."""
        table = [(0, 3), (10, 15), (20, 25)]

        assert _in_exclusion(11, 2, table) is True
        assert _in_exclusion(16, 2, table) is False
        assert _in_exclusion(24, 1, table) is True

    def test_param_iteration_order(self):
        """Parameters are yielded positional, vararg, keyword-only, kwarg."""
        source = "def f(a, b, /, c, *args, d, **kwargs):\n    pass\n"
        function = ast.parse(source).body[0]

        assert [arg.arg for arg in _iter_param_args(function.args)] == [
            "a",
            "b",
            "c",
            "args",
            "d",
            "kwargs",
        ]

    def test_token_line_index_groups_in_stream_order(self):
        """The line index preserves token stream order per row."""
        tokens = [
            SimpleToken(tokenize.NAME, "first", (1, 0)),
            SimpleToken(tokenize.NAME, "second", (2, 0)),
            SimpleToken(tokenize.NAME, "third", (1, 6)),
        ]

        index = _build_line_index(tokens)

        assert [token.string for token in index[1]] == ["first", "third"]
        assert [token.string for token in index[2]] == ["second"]

    def test_exclusions_include_comments_and_strings(self):
        """Comment and string spans are excluded from semantic overlays."""
        source = 'value = "text"  # note\n'
        line_offsets = _build_line_offsets(source)
        stream = list(tokenize.generate_tokens(iter([source]).__next__))

        exclusions = _build_exclusions_from_stream(stream, line_offsets)

        raw = source.encode("utf-8")
        spans = [raw[start:end].decode("utf-8") for start, end in exclusions]
        assert '"text"' in spans
        assert "# note" in spans

    def test_dedupe_keeps_the_longest_token_at_a_position(self):
        """Overlapping tokens are removed, preferring the longer span."""
        provider = PythonSemanticProvider()
        style = TokenStyle(0, "#FFFFFF")
        tokens = [
            Token(0, 5, style, "long"),
            Token(0, 2, style, "short"),
            Token(2, 4, style, "overlap"),
            Token(5, 2, style, "next"),
        ]

        deduped = provider._dedupe(tokens)

        assert [(token.start, token.length, token.kind) for token in deduped] == [
            (0, 5, "long"),
            (5, 2, "next"),
        ]

    def test_dedupe_of_empty_input(self):
        """No tokens means an empty result."""
        assert PythonSemanticProvider()._dedupe([]) == []


class SimpleToken:
    """Minimal tokenize-token stand-in for line-index tests."""

    def __init__(self, token_type: int, string: str, start: tuple[int, int]) -> None:
        self.type = token_type
        self.string = string
        self.start = start
