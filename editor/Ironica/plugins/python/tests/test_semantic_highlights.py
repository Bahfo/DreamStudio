"""
Tests for the simplified Python semantic highlighting provider.

The provider has two independent paths:

1. Lexer path (``get_tokens``): pure ``tokenize`` output.
2. Overlay path (``get_semantic_ranges``): a small whitelist of
   AST-derived spans — definition names, parameters, imports,
   self/cls.

Run with: pytest test_semantic_highlights.py -v
"""

import os
import json as _json
import pytest

from editor.Ironica.utils.highlighting_api import (
    HighlightingRegistry,
    styles_from_config,
    Token,
)
from editor.Ironica.plugins.python.semantic_highlights import (
    PythonSemanticProvider,
    get_semantic_highlights,
)
from editor.Ironica.language_engine import LanguageRegistry

# Build STYLES from the python.json config (single source of truth).
_PYTHON_JSON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "keywords", "python.json")
)
if os.path.isfile(_PYTHON_JSON):
    with open(_PYTHON_JSON) as _f:
        _PYTHON_CONFIG = _json.load(_f)
    STYLES = styles_from_config(_PYTHON_CONFIG)
else:
    STYLES = styles_from_config({})


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _overlay_kinds(provider, text):
    """Return the set of kind strings emitted by the overlay path."""
    provider._compute(text)
    return {t.kind for t in provider._cache_semantic}


def _named_spans(provider, text, kind):
    """Return set of name strings for tokens of a given kind."""
    provider._compute(text)
    return {
        text[t.start : t.start + t.length]
        for t in provider._cache_semantic
        if t.kind == kind
    }


def _colours(ranges):
    """Extract colour strings from [(start, length, colour), ...]."""
    return [c for _, _, c in ranges]


# ------------------------------------------------------------------
# 1. Lexer path: pure tokenize output
# ------------------------------------------------------------------


class TestLexerPath:
    """get_tokens() returns only lexical tokens — no AST inference."""

    def test_tokens_are_lexical_only(self):
        p = PythonSemanticProvider()
        code = "def foo(): pass"
        tokens = p.get_tokens(code)
        # Only keywords (def) — no function name, no parameter
        kinds = {t.kind for t in tokens}
        assert "keyword" in kinds
        assert "function" not in kinds
        assert "parameter" not in kinds
        assert "self" not in kinds

    def test_tokens_cover_keywords(self):
        p = PythonSemanticProvider()
        code = "if True:\n    return x"
        tokens = p.get_tokens(code)
        kw_tokens = [t for t in tokens if t.kind == "keyword"]
        names = {code[t.start : t.start + t.length] for t in kw_tokens}
        assert "if" in names
        assert "return" in names

    def test_tokens_cover_strings(self):
        p = PythonSemanticProvider()
        code = "x = 'hello'"
        tokens = p.get_tokens(code)
        kinds = {t.kind for t in tokens}
        assert "string" in kinds

    def test_tokens_cover_comments(self):
        p = PythonSemanticProvider()
        code = "# a comment"
        tokens = p.get_tokens(code)
        kinds = {t.kind for t in tokens}
        assert "comment" in kinds

    def test_tokens_cover_numbers(self):
        p = PythonSemanticProvider()
        code = "x = 42"
        tokens = p.get_tokens(code)
        kinds = {t.kind for t in tokens}
        assert "number" in kinds

    def test_tokens_cover_operators(self):
        p = PythonSemanticProvider()
        code = "x = 1 + 2"
        tokens = p.get_tokens(code)
        kinds = {t.kind for t in tokens}
        assert "operator" in kinds

    def test_tokens_cover_decorator_sign(self):
        p = PythonSemanticProvider()
        code = "@decorator\ndef foo(): pass"
        tokens = p.get_tokens(code)
        kinds = {t.kind for t in tokens}
        assert "decorator" in kinds

    def test_tokens_empty_text(self):
        p = PythonSemanticProvider()
        assert p.get_tokens("") == []
        assert p.get_tokens("  ") == []

    def test_tokens_incomplete_code(self):
        """Incomplete code still produces lexical tokens."""
        p = PythonSemanticProvider()
        tokens = p.get_tokens("def foo(")
        # Should get at least the 'def' keyword
        assert any(t.kind == "keyword" for t in tokens)


# ------------------------------------------------------------------
# 2. Overlay whitelist: definitions, params, imports, self/cls
# ------------------------------------------------------------------


class TestOverlayWhitelist:
    """The overlay only emits the small whitelist of AST-derived spans."""

    def test_overlay_only_whitelist_kinds(self):
        p = PythonSemanticProvider()
        code = (
            "import os\n"
            "from os import path\n"
            "class Foo:\n"
            "    def bar(self, x):\n"
            "        return self.val\n"
        )
        kinds = _overlay_kinds(p, code)
        allowed = {"function", "class", "parameter", "self", "module", "definition", "variable", "exception"}
        assert kinds.issubset(allowed), f"Unexpected kinds: {kinds - allowed}"

    def test_function_def_name(self):
        p = PythonSemanticProvider()
        code = "def foo(): pass"
        func_names = _named_spans(p, code, "function")
        assert "foo" in func_names

    def test_class_def_name(self):
        p = PythonSemanticProvider()
        code = "class MyClass: pass"
        class_names = _named_spans(p, code, "class")
        assert "MyClass" in class_names

    def test_async_def_name(self):
        p = PythonSemanticProvider()
        code = "async def fetch(): pass"
        func_names = _named_spans(p, code, "function")
        assert "fetch" in func_names

    def test_parameters(self):
        p = PythonSemanticProvider()
        code = "def foo(a, b, c): pass"
        param_names = _named_spans(p, code, "parameter")
        assert param_names == {"a", "b", "c"}

    def test_self_parameter(self):
        p = PythonSemanticProvider()
        code = "class X:\n    def m(self): pass"
        self_names = _named_spans(p, code, "self")
        assert "self" in self_names

    def test_cls_parameter(self):
        p = PythonSemanticProvider()
        code = "class X:\n    @classmethod\n    def m(cls): pass"
        self_names = _named_spans(p, code, "self")
        assert "cls" in self_names

    def test_self_in_body(self):
        p = PythonSemanticProvider()
        code = "class X:\n    def m(self):\n        return self.val"
        self_names = _named_spans(p, code, "self")
        assert "self" in self_names

    def test_import_module(self):
        p = PythonSemanticProvider()
        code = "import os"
        mod_names = _named_spans(p, code, "module")
        assert "os" in mod_names

    def test_from_import_module(self):
        p = PythonSemanticProvider()
        code = "from os.path import join"
        mod_names = _named_spans(p, code, "module")
        assert "os.path" in mod_names

    def test_from_import_aliases(self):
        p = PythonSemanticProvider()
        code = "from collections import OrderedDict, defaultdict"
        def_names = _named_spans(p, code, "definition")
        assert "OrderedDict" in def_names
        assert "defaultdict" in def_names

    def test_lambda_params(self):
        p = PythonSemanticProvider()
        code = "f = lambda x, y: x + y"
        param_names = _named_spans(p, code, "parameter")
        assert param_names == {"x", "y"}


# ------------------------------------------------------------------
# 3. Things that must NOT be in the overlay
# ------------------------------------------------------------------


class TestOverlayExclusions:
    """The overlay must not emit call sites, attributes, constants,
    builtins, or decorators."""

    def test_no_call_sites(self):
        p = PythonSemanticProvider()
        code = "def foo(): pass\nfoo()"
        kinds = _overlay_kinds(p, code)
        # "function" is present from the def, but no extra "function"
        # from the call site — verify by checking span count
        func_names = _named_spans(p, code, "function")
        assert func_names == {"foo"}  # only the def, not the call

    def test_no_attribute_chains(self):
        p = PythonSemanticProvider()
        code = "import os\nos.sep"
        kinds = _overlay_kinds(p, code)
        assert "variable" not in kinds

    def test_no_constants(self):
        p = PythonSemanticProvider()
        code = "x = None\ny = True\nz = False"
        kinds = _overlay_kinds(p, code)
        assert "constant" not in kinds

    def test_no_builtin_detection(self):
        p = PythonSemanticProvider()
        code = "len([1, 2, 3])\nhasattr(x, 'y')"
        kinds = _overlay_kinds(p, code)
        assert "builtin" not in kinds

    def test_no_decorator_names(self):
        p = PythonSemanticProvider()
        code = "@my_decorator\ndef foo(): pass"
        kinds = _overlay_kinds(p, code)
        assert "decorator" not in kinds


# ------------------------------------------------------------------
# 4. Lexer-only content stays lexer-owned
# ------------------------------------------------------------------


class TestLexerOwnership:
    """Keywords, strings, comments, numbers, operators, decorators
    are never in the overlay."""

    def test_overlay_no_keywords(self):
        p = PythonSemanticProvider()
        code = "def class return if else while for in not and or"
        kinds = _overlay_kinds(p, code)
        assert "keyword" not in kinds

    def test_overlay_no_strings(self):
        p = PythonSemanticProvider()
        code = "x = 'hello'"
        kinds = _overlay_kinds(p, code)
        assert "string" not in kinds

    def test_overlay_no_comments(self):
        p = PythonSemanticProvider()
        code = "# comment"
        kinds = _overlay_kinds(p, code)
        assert "comment" not in kinds

    def test_overlay_no_numbers(self):
        p = PythonSemanticProvider()
        code = "x = 42"
        kinds = _overlay_kinds(p, code)
        assert "number" not in kinds

    def test_overlay_no_operators(self):
        p = PythonSemanticProvider()
        code = "x = 1 + 2"
        kinds = _overlay_kinds(p, code)
        assert "operator" not in kinds

    def test_overlay_no_decorators(self):
        p = PythonSemanticProvider()
        code = "@dec\ndef f(): pass"
        kinds = _overlay_kinds(p, code)
        assert "decorator" not in kinds


# ------------------------------------------------------------------
# 5. Incomplete / broken code
# ------------------------------------------------------------------


class TestIncompleteCode:
    """SyntaxError during live typing must not crash the provider."""

    def test_incomplete_def(self):
        p = PythonSemanticProvider()
        # Fallback parser can still highlight function names
        ranges = p.get_semantic_ranges("def foo(")
        assert len(ranges) == 1
        assert ranges[0][:2] == (4, 3)

    def test_incomplete_import(self):
        p = PythonSemanticProvider()
        # Fallback parser can still highlight module names
        ranges = p.get_semantic_ranges("from os import")
        assert len(ranges) == 1
        assert ranges[0][:2] == (5, 2)

    def test_completely_broken(self):
        p = PythonSemanticProvider()
        assert p.get_semantic_ranges("{{{???") == []

    def test_empty_text(self):
        p = PythonSemanticProvider()
        assert p.get_semantic_ranges("") == []
        assert p.get_semantic_ranges("   ") == []
        assert p.get_semantic_ranges("\n\n\n") == []


# ------------------------------------------------------------------
# 6. Dotted chains stay lexer-only
# ------------------------------------------------------------------


class TestDottedChains:
    """Dotted attribute chains must not trigger semantic coloring."""

    def test_long_chain_no_overlay(self):
        p = PythonSemanticProvider()
        code = "class X:\n    def m(self):\n        return self.hero_window._text_editor_center.tabs"
        p.invalidate_cache()
        kinds = _overlay_kinds(p, code)
        assert "variable" not in kinds
        # self is still colored (whitelist), but attribute tails are not
        self_names = _named_spans(p, code, "self")
        assert "self" in self_names

    def test_repeated_chains_no_overlay(self):
        p = PythonSemanticProvider()
        code = (
            "a.b.c.d.e\n"
            "x.y.z\n"
        )
        kinds = _overlay_kinds(p, code)
        assert kinds == set()  # no definitions, params, imports, or self

    def test_class_style_dotted_name_no_overlay(self):
        p = PythonSemanticProvider()
        code = "ConfirmDialog.DialogCode.Accepted"
        kinds = _overlay_kinds(p, code)
        assert kinds == set()


# ------------------------------------------------------------------
# 7. getattr / hasattr debug-style code
# ------------------------------------------------------------------


class TestGetattrHasattr:
    """getattr/hasattr with string args must stay lexical."""

    def test_getattr_string_not_colored(self):
        p = PythonSemanticProvider()
        code = 'getattr(self, "_active_debug_session", None)'
        p.invalidate_cache()
        p._compute(code)
        for t in p._cache_semantic:
            span_text = code[t.start : t.start + t.length]
            assert span_text != "_active_debug_session"

    def test_hasattr_string_not_colored(self):
        p = PythonSemanticProvider()
        code = 'hasattr(widget, "isModified")'
        p.invalidate_cache()
        p._compute(code)
        for t in p._cache_semantic:
            span_text = code[t.start : t.start + t.length]
            assert span_text != "isModified"

    def test_getattr_self_still_colored(self):
        p = PythonSemanticProvider()
        code = 'getattr(self, "x", None)'
        self_names = _named_spans(p, code, "self")
        assert "self" in self_names


# ------------------------------------------------------------------
# 8. Multiline from-imports
# ------------------------------------------------------------------


class TestMultilineImports:
    """from imports spanning multiple lines."""

    def test_multiline_from_import(self):
        p = PythonSemanticProvider()
        code = (
            "from os.path import (\n"
            "    join,\n"
            "    exists,\n"
            "    dirname,\n"
            ")\n"
        )
        def_names = _named_spans(p, code, "definition")
        assert "join" in def_names
        assert "exists" in def_names
        assert "dirname" in def_names

    def test_multiline_from_import_module(self):
        p = PythonSemanticProvider()
        code = (
            "from os.path import (\n"
            "    join,\n"
            ")\n"
        )
        mod_names = _named_spans(p, code, "module")
        assert "os.path" in mod_names


# ------------------------------------------------------------------
# 9. Cache invalidation
# ------------------------------------------------------------------


class TestCacheInvalidation:
    """The cache must bust on invalidate_cache()."""

    def test_warm_cache_returns_same_result(self):
        p = PythonSemanticProvider()
        code = "def foo(): pass"
        r1 = p.get_semantic_ranges(code)
        r2 = p.get_semantic_ranges(code)
        assert r1 == r2

    def test_invalidate_forces_recompute(self):
        p = PythonSemanticProvider()
        code = "def foo(): pass"
        p.get_semantic_ranges(code)
        assert p._cache_text == code
        p.invalidate_cache()
        assert p._cache_text == ""
        assert p._cache_lexical == []
        assert p._cache_semantic == []

    def test_different_text_busts_cache(self):
        p = PythonSemanticProvider()
        p.get_semantic_ranges("def foo(): pass")
        p.get_semantic_ranges("def bar(): pass")
        assert p._cache_text == "def bar(): pass"


# ------------------------------------------------------------------
# 10. Keyword stability across files
# ------------------------------------------------------------------


class TestKeywordStability:
    """Same keyword always gets the same colour, no file-to-file drift."""

    def test_keyword_never_in_overlay(self):
        p = PythonSemanticProvider()
        files = [
            "def foo(): pass",
            "class Bar: pass",
            "if x:\n    return y",
            "# comment\ndef baz(): pass",
        ]
        for f in files:
            p.invalidate_cache()
            kinds = _overlay_kinds(p, f)
            assert "keyword" not in kinds

    def test_two_files_back_to_back(self):
        p = PythonSemanticProvider()
        file_a = "import os\nx = os.getcwd()"
        file_b = "def greet(name): return name"

        p.get_semantic_ranges(file_a)
        p.invalidate_cache()
        p.get_semantic_ranges(file_b)

        func_names = _named_spans(p, file_b, "function")
        assert "greet" in func_names

        # keyword colour never leaks
        colours_a = _colours(p.get_semantic_ranges(file_a))
        colours_b = _colours(p.get_semantic_ranges(file_b))
        assert STYLES["keyword"].colour not in colours_a
        assert STYLES["keyword"].colour not in colours_b


# ------------------------------------------------------------------
# 11. Registration
# ------------------------------------------------------------------


class TestRegistration:
    """Provider must be registered and retrievable."""

    def test_provider_registered(self):
        HighlightingRegistry.reset()
        p = PythonSemanticProvider()
        HighlightingRegistry.register("python", p)
        assert HighlightingRegistry.has_provider("python")
        assert HighlightingRegistry.get_provider("python") is p

    def test_provider_unregister(self):
        HighlightingRegistry.reset()
        p = PythonSemanticProvider()
        HighlightingRegistry.register("python", p)
        assert HighlightingRegistry.unregister("python")
        assert not HighlightingRegistry.has_provider("python")

    def test_legacy_wrapper_matches_provider(self):
        HighlightingRegistry.reset()
        p = PythonSemanticProvider()
        HighlightingRegistry.register("python", p)
        code = "def foo(): pass"
        legacy = get_semantic_highlights(code)
        provider_ranges = p.get_semantic_ranges(code)
        assert legacy == provider_ranges


# ------------------------------------------------------------------
# 12. Normal Python file
# ------------------------------------------------------------------


class TestNormalPythonFile:
    """A realistic Python file highlights cleanly."""

    def test_normal_file(self):
        p = PythonSemanticProvider()
        code = (
            "import os\n"
            "from typing import List, Optional\n"
            "\n"
            "\n"
            "class App:\n"
            "    def __init__(self, name: str) -> None:\n"
            "        self.name = name\n"
            "        self.config = {}\n"
            "\n"
            "    def run(self) -> None:\n"
            "        print(f'Running {self.name}')\n"
            "\n"
            "\n"
            "def main() -> None:\n"
            "    app = App('demo')\n"
            "    app.run()\n"
            "\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )
        kinds = _overlay_kinds(p, code)
        allowed = {"function", "class", "parameter", "self", "module", "definition", "variable", "exception"}
        assert kinds.issubset(allowed)

        func_names = _named_spans(p, code, "function")
        assert "__init__" in func_names
        assert "run" in func_names
        assert "main" in func_names

        class_names = _named_spans(p, code, "class")
        assert "App" in class_names

        param_names = _named_spans(p, code, "parameter")
        assert "name" in param_names

        self_names = _named_spans(p, code, "self")
        assert "self" in self_names

        mod_names = _named_spans(p, code, "module")
        assert "os" in mod_names
        assert "typing" in mod_names

        def_names = _named_spans(p, code, "definition")
        assert "List" in def_names
        assert "Optional" in def_names


# ------------------------------------------------------------------
# 13. Debug-management snippet (getattr/hasattr + dotted chains)
# ------------------------------------------------------------------


class TestDebugManagementSnippet:
    """Debug-style code with getattr/hasattr and deep dotted chains
    must stay fully lexical — no false positives in the overlay."""

    def test_getattr_hasattr_in_class_method(self):
        p = PythonSemanticProvider()
        code = (
            "class DebugSession:\n"
            "    def _update_state(self):\n"
            '        if not hasattr(self, "_active_debug_session"):\n'
            "            return\n"
            '        session = getattr(self, "_active_debug_session")\n'
            "        session.status_bar.showMessage(\n"
            '            getattr(session, "current_status", "Ready")\n'
            "        )\n"
        )
        p.invalidate_cache()
        overlay = p.get_semantic_ranges(code)
        overlay_texts = {code[s : s + l] for s, l, _ in overlay}
        assert "_active_debug_session" not in overlay_texts
        assert "current_status" not in overlay_texts
        assert "status_bar" not in overlay_texts
        assert "showMessage" not in overlay_texts
        assert "self" in overlay_texts
        assert "DebugSession" in overlay_texts
        assert "_update_state" in overlay_texts

    def test_long_dotted_chain_lexical_only(self):
        p = PythonSemanticProvider()
        code = "result = obj.attr1.attr2.attr3.attr4.method()"
        p.invalidate_cache()
        tokens = p.get_tokens(code)
        id_tokens = [t for t in tokens if t.kind == "identifier"]
        assert id_tokens == []
        overlay = p.get_semantic_ranges(code)
        # result is highlighted as a variable definition
        assert len(overlay) == 1
        assert overlay[0][2] in ("#9CDCFE",)  # variable colour


# ------------------------------------------------------------------
# 14. Repeated keywords across two files
# ------------------------------------------------------------------


class TestRepeatedKeywordsAcrossFiles:
    """Keywords must always render the same colour regardless of
    which file was processed first (no file-to-file drift)."""

    def test_def_keyword_stable_across_files(self):
        p = PythonSemanticProvider()
        file_a = "def alpha(): pass"
        file_b = "def beta(): pass"

        tokens_a = p.get_tokens(file_a)
        kw_a = [t for t in tokens_a if t.kind == "keyword"]
        def_kw_a = [t for t in kw_a if file_a[t.start : t.start + t.length] == "def"]
        assert len(def_kw_a) == 1
        assert def_kw_a[0].style.colour == STYLES["keyword"].colour

        tokens_b = p.get_tokens(file_b)
        kw_b = [t for t in tokens_b if t.kind == "keyword"]
        def_kw_b = [t for t in kw_b if file_b[t.start : t.start + t.length] == "def"]
        assert len(def_kw_b) == 1
        assert def_kw_b[0].style.colour == STYLES["keyword"].colour

    def test_class_keyword_stable_across_files(self):
        p = PythonSemanticProvider()
        file_a = "class Alpha: pass"
        file_b = "class Beta: pass"

        tokens_a = p.get_tokens(file_a)
        tokens_b = p.get_tokens(file_b)

        kw_a = [t for t in tokens_a if t.kind == "keyword"]
        kw_b = [t for t in tokens_b if t.kind == "keyword"]

        assert kw_a[0].style.colour == kw_b[0].style.colour
        assert kw_a[0].style.colour == STYLES["keyword"].colour

    def test_overlay_never_contains_keyword_colour(self):
        p = PythonSemanticProvider()
        files = [
            "def foo(): pass",
            "class Bar: pass",
            "if True:\n    return x",
            "import os\nfrom os import path",
        ]
        for f in files:
            p.invalidate_cache()
            ranges = p.get_semantic_ranges(f)
            colours = [c for _, _, c in ranges]
            assert STYLES["keyword"].colour not in colours


# ------------------------------------------------------------------
# 15. Repaint behaviour (goto-definition, paste, rewrite)
# ------------------------------------------------------------------


class TestRepaintBehaviour:
    """Verify that cache invalidation forces fresh computation and
    that stale results are never returned after mutations."""

    def test_invalidate_cache_forces_fresh_computation(self):
        p = PythonSemanticProvider()
        code = "def foo(): pass"
        p.get_semantic_ranges(code)
        assert p._cache_text == code

        new_code = "def bar(): pass"
        p.invalidate_cache()
        result = p.get_semantic_ranges(new_code)

        func_names = {code[s : s + l] for s, l, _ in result}
        assert "bar" not in func_names

        func_names_new = {new_code[s : s + l] for s, l, _ in result}
        assert "bar" in func_names_new

    def test_file_switch_clears_old_overlay(self):
        p = PythonSemanticProvider()
        file_a = "class OldClass: pass"
        file_b = "class NewClass: pass"

        overlay_a = p.get_semantic_ranges(file_a)
        names_a = {file_a[s : s + l] for s, l, _ in overlay_a}
        assert "OldClass" in names_a

        p.invalidate_cache()
        overlay_b = p.get_semantic_ranges(file_b)
        names_b = {file_b[s : s + l] for s, l, _ in overlay_b}
        assert "NewClass" in names_b
        assert "OldClass" not in names_b

    def test_paste_simulation(self):
        p = PythonSemanticProvider()
        original = "def original(): pass"
        p.get_semantic_ranges(original)
        assert p._cache_text == original

        p.invalidate_cache()
        after_paste = "def original():\n    x = 1\ndef pasted(): pass"
        result = p.get_semantic_ranges(after_paste)
        names = {after_paste[s : s + l] for s, l, _ in result}
        assert "original" in names
        assert "pasted" in names


# ------------------------------------------------------------------
# 16. Decorators
# ------------------------------------------------------------------


class TestDecorators:
    """Decorator syntax must be handled lexically (the @ sign) and
    decorator function names must stay lexical — no overlay colouring."""

    def test_at_sign_is_lexical_decorator(self):
        p = PythonSemanticProvider()
        code = "@my_decorator\ndef foo(): pass"
        tokens = p.get_tokens(code)
        decorator_tokens = [t for t in tokens if t.kind == "decorator"]
        assert len(decorator_tokens) == 1
        at_text = code[decorator_tokens[0].start : decorator_tokens[0].start + decorator_tokens[0].length]
        assert at_text == "@"

    def test_decorator_name_not_in_overlay(self):
        p = PythonSemanticProvider()
        code = "@my_decorator\ndef foo(): pass"
        p.invalidate_cache()
        overlay = p.get_semantic_ranges(code)
        overlay_texts = {code[s : s + l] for s, l, _ in overlay}
        assert "my_decorator" not in overlay_texts

    def test_property_decorator(self):
        p = PythonSemanticProvider()
        code = (
            "class X:\n"
            "    @property\n"
            "    def name(self): pass\n"
        )
        tokens = p.get_tokens(code)
        decorator_tokens = [t for t in tokens if t.kind == "decorator"]
        assert len(decorator_tokens) == 1
        at_text = code[decorator_tokens[0].start : decorator_tokens[0].start + decorator_tokens[0].length]
        assert at_text == "@"

    def test_multiple_decorators(self):
        p = PythonSemanticProvider()
        code = (
            "@decorator_a\n"
            "@decorator_b\n"
            "def foo(): pass\n"
        )
        tokens = p.get_tokens(code)
        decorator_tokens = [t for t in tokens if t.kind == "decorator"]
        assert len(decorator_tokens) == 2


# ------------------------------------------------------------------
# 17. Multiline imports (additional edge cases)
# ------------------------------------------------------------------


class TestMultilineImportsExtended:
    """Additional multiline import edge cases."""

    def test_parenthesized_import_single_alias(self):
        p = PythonSemanticProvider()
        code = "from os import (\n    path,\n)\n"
        mod_names = _named_spans(p, code, "module")
        assert "os" in mod_names
        def_names = _named_spans(p, code, "definition")
        assert "path" in def_names

    def test_dotted_module_in_from_import(self):
        p = PythonSemanticProvider()
        code = "from collections.abc import Mapping, Sequence"
        mod_names = _named_spans(p, code, "module")
        assert "collections.abc" in mod_names
        def_names = _named_spans(p, code, "definition")
        assert "Mapping" in def_names
        assert "Sequence" in def_names

    def test_import_star_not_colored(self):
        p = PythonSemanticProvider()
        code = "from os import *"
        overlay = p.get_semantic_ranges(code)
        overlay_texts = {code[s : s + l] for s, l, _ in overlay}
        assert "*" not in overlay_texts


# ------------------------------------------------------------------
# 18. F-strings
# ------------------------------------------------------------------


class TestFStrings:
    """F-strings must be colored as strings in the lexer path,
    with no overlay false positives."""

    def test_fstring_colored_as_string(self):
        p = PythonSemanticProvider()
        code = 'x = f"hello {name}"'
        tokens = p.get_tokens(code)
        string_tokens = [t for t in tokens if t.kind == "string"]
        assert len(string_tokens) >= 1

    def test_fstring_no_overlay(self):
        p = PythonSemanticProvider()
        code = 'x = f"hello {name}"'
        overlay = p.get_semantic_ranges(code)
        overlay_texts = {code[s : s + l] for s, l, _ in overlay}
        assert "name" not in overlay_texts

    def test_fstring_with_expression(self):
        p = PythonSemanticProvider()
        code = 'x = f"result: {a + b}"'
        tokens = p.get_tokens(code)
        string_tokens = [t for t in tokens if t.kind == "string"]
        assert len(string_tokens) >= 1
