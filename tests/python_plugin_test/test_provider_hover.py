"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for hover extraction, HTML/Markdown rendering, and symbol detection.
"""

from __future__ import annotations

import pytest

from editor.Ironica.plugins.python import provider as provider_module
from editor.Ironica.plugins.python.domain_models import (
    HoverDetails,
    ParameterInfo,
)
from editor.Ironica.plugins.python.provider import (
    PythonLanguageProvider,
    _clean_docstring,
    _format_hover_markdown,
    _format_qt_tooltip,
    _is_inside_string,
    _signature_is_redundant,
    _strip_signature_echo,
)
from tests.python_plugin_test.helpers import RecordingAdapter


@pytest.fixture
def hover_details() -> HoverDetails:
    """Return a rich hover payload covering every optional field."""
    return HoverDetails(
        name="greet",
        kind="function",
        signature="def greet(name: str, times: int = 1) -> str",
        parameters=[
            ParameterInfo("name", "str"),
            ParameterInfo("times", "int", "1"),
        ],
        return_type="str",
        docstring="\n    Return a greeting.\n\n    Keeps the formatting.\n    ",
    )


class TestSymbolDetection:
    """Tests for the caret-to-identifier and string guards."""

    @pytest.mark.parametrize(
        ("line", "column", "expected"),
        [
            ("value = 1", 0, "value"),
            ("value = 1", 4, "value"),
            ("value = 1", 5, None),
            ("value = 1", 6, None),
            ("call(argument)", 7, "argument"),
            ("x = 1", -1, None),
            ("x = 1", 99, None),
        ],
    )
    def test_symbol_at_extracts_identifier_under_column(self, line, column, expected):
        """Identifiers are half-open: the column after the name is not a hit."""
        assert PythonLanguageProvider._symbol_at(line, 0, column) == expected

    def test_symbol_at_ignores_text_inside_strings(self):
        """Text inside a string literal is never treated as a symbol."""
        assert PythonLanguageProvider._symbol_at('x = "hello"', 0, 6) is None

    def test_symbol_at_returns_none_for_missing_line(self):
        """A line past the end of the buffer yields no symbol."""
        assert PythonLanguageProvider._symbol_at("one line", 4, 0) is None

    def test_symbol_at_finds_symbol_on_last_line_without_newline(self):
        """The final line is addressable even without a trailing newline."""
        text = "first = 1\nsecond = 2"

        assert PythonLanguageProvider._symbol_at(text, 1, 0) == "second"

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            (0, "first = 1"),
            (1, ""),
            (2, "third = 3"),
            (3, "fourth = 4"),
        ],
    )
    def test_line_text_at_extracts_exact_line(self, line, expected):
        """Line extraction preserves empty lines and avoids whole-buffer splits."""
        text = "first = 1\n\nthird = 3\nfourth = 4"

        assert PythonLanguageProvider._line_text_at(text, line) == expected

    def test_line_text_at_negative_line_returns_none(self):
        """Negative line numbers are invalid."""
        assert PythonLanguageProvider._line_text_at("text", -1) is None

    def test_line_text_at_beyond_buffer_returns_none(self):
        """A line past the last newline does not fabricate content."""
        assert PythonLanguageProvider._line_text_at("one\ntwo", 2) is None


class TestStringDetection:
    """Tests for the single-line string-literal guard used by hover."""

    @pytest.mark.parametrize(
        ("line", "column", "expected"),
        [
            ("x = 'abc'", 0, False),
            ("x = 'abc'", 4, True),
            ("x = 'abc'", 5, True),
            ("x = 'abc'", 8, True),
            ("x = 'abc'", 9, False),
            ('x = "abc"', 4, True),
            ("x = 'abc' # trailing", 12, False),
            ("# 'quoted'", 4, False),
            ('x = """doc"""', 4, True),
            ('x = """doc"""', 10, True),
            ('x = """doc"""', 11, False),
            ("x = '''doc'''", 4, True),
            ("x = 'unterminated", 6, True),
            ('x = f"value"', 6, True),
            ("x = 1", 0, False),
            ("", 0, False),
        ],
    )
    def test_is_inside_string_matches_literal_boundaries(self, line, column, expected):
        """Quotes, triple quotes, comments, and unclosed literals are handled."""
        assert _is_inside_string(line, column) is expected


class TestDocstringCleaning:
    """Tests for common-indentation removal."""

    def test_strips_common_margin_and_surrounding_blank_lines(self):
        """A conventional docstring keeps its paragraph break."""
        docstring = "\n    Summary line.\n\n    Detail line.\n    "

        assert _clean_docstring(docstring) == "Summary line.\n\nDetail line."

    def test_expands_tabs_before_measuring_indentation(self):
        """Tabs are expanded to four spaces before the margin is computed."""
        docstring = "\n\tSummary.\n\tDetail.\n"

        assert _clean_docstring(docstring) == "Summary.\nDetail."

    def test_single_line_docstring_is_stripped(self):
        """A one-line docstring loses its outer whitespace."""
        assert _clean_docstring("  Summary.  ") == "Summary."

    def test_blank_docstring_returns_empty(self):
        """Whitespace-only documentation collapses to an empty string."""
        assert _clean_docstring("   \n\t\n") == ""
        assert _clean_docstring("") == ""


class TestQtTooltip:
    """Tests for the HTML4-safe tooltip formatter."""

    def test_renders_signature_parameters_and_return_type(self, hover_details):
        """Structured details become a rich tooltip body."""
        tooltip = _format_qt_tooltip(hover_details)

        assert '<b style="color:#569CD6;">greet</b>' in tooltip
        assert "(FUNCTION)" in tooltip
        assert "def greet(name: str, times: int = 1) -&gt; str" in tooltip
        assert "Parameters:" in tooltip
        assert "&#8226;&nbsp;<b>name</b>" in tooltip
        assert 'color="#4EC9B0;">str</font>' in tooltip
        assert 'color="#4EC9B0;">int</font>' in tooltip
        assert 'color="#B5CEA8">1</font>' in tooltip
        assert "Returns:" in tooltip
        assert "Return a greeting." in tooltip

    def test_escapes_html_in_every_untrusted_field(self):
        """Names, signatures, defaults, and documentation are HTML-escaped."""
        details = HoverDetails(
            name="f<g",
            kind="function",
            signature='def f(x="<tag>")',
            parameters=[ParameterInfo("<arg>", "<int>", "<default>")],
            return_type="<str>",
            docstring="<script>alert(1)</script> & more",
        )

        tooltip = _format_qt_tooltip(details)

        assert "<script>" not in tooltip
        assert "&lt;script&gt;" in tooltip
        assert "f&lt;g" in tooltip
        assert "&lt;tag&gt;" in tooltip
        assert "&lt;arg&gt;" in tooltip
        assert "&lt;int&gt;" in tooltip
        assert "&lt;default&gt;" in tooltip
        assert "&lt;str&gt;" in tooltip
        assert "&amp; more" in tooltip

    def test_newlines_and_double_spaces_become_html_breaks(self):
        """Signatures keep visual line breaks and indentation in Qt tooltips."""
        details = HoverDetails(
            name="f",
            kind="function",
            signature="def f(\n  a,\n  b,\n)",
        )

        tooltip = _format_qt_tooltip(details)

        assert "<br/>" in tooltip
        assert "&nbsp;&nbsp;" in tooltip

    def test_missing_kind_uses_symbol_label(self):
        """An empty kind falls back to the generic SYMBOL label."""
        tooltip = _format_qt_tooltip(HoverDetails("value", "", "value = 1"))

        assert "(SYMBOL)" in tooltip


class TestSignatureHelpers:
    """Tests for signature redundancy and docstring echo removal."""

    @pytest.mark.parametrize(
        ("signature", "name", "kind", "expected"),
        [
            ("greet()", "greet", "function", True),
            ("greet", "greet", "function", True),
            ("function greet", "greet", "function", True),
            ("function greet()", "greet", "function", True),
            ("def greet()", "greet", "function", False),
            ("greet(name)", "greet", "function", False),
            ("", "greet", "function", False),
            ("greet()", "", "function", False),
        ],
    )
    def test_signature_is_redundant(self, signature, name, kind, expected):
        """Only a bare name/kind echo is considered redundant."""
        assert _signature_is_redundant(signature, name, kind) is expected

    @pytest.mark.parametrize(
        "docstring",
        [
            "greet(name)\n\nDoes the greeting.",
            "greet\n\nDoes the greeting.",
            "def greet(name)\n\nDoes the greeting.",
            "function greet\n\nDoes the greeting.",
        ],
    )
    def test_strip_signature_echo_removes_leading_echo(self, docstring):
        """Signatures, names, and kind-name labels are stripped from the top."""
        stripped = _strip_signature_echo(
            docstring, "greet", "function", "def greet(name)"
        )

        assert stripped == "Does the greeting."

    def test_strip_signature_echo_keeps_real_text(self):
        """A sentence that merely starts with the name is preserved."""
        docstring = "greeting helpers are documented here.\n\nDetails."

        stripped = _strip_signature_echo(docstring, "greet", "function", "")

        assert stripped.startswith("greeting helpers")
        assert stripped.endswith("Details.")

    def test_strip_signature_echo_handles_empty_docstring(self):
        """Empty documentation stays empty."""
        assert _strip_signature_echo("", "greet", "function", "") == ""


class TestHoverMarkdown:
    """Tests for the Markdown flyout formatter."""

    def test_renders_rich_markdown_document(self, hover_details):
        """Signature, parameters, return type, and docs appear in order."""
        markdown = _format_hover_markdown(hover_details)

        assert markdown.startswith("```python\ndef greet(")
        assert "```" in markdown
        assert "### Parameters (2)" in markdown
        assert "- **name** `str`" in markdown
        assert "- **times** `int` = `1`" in markdown
        assert "**Returns:** `str`" in markdown
        assert "---" in markdown
        assert "Return a greeting.\n\nKeeps the formatting." in markdown

    def test_redundant_signature_is_omitted(self):
        """A signature that only repeats the symbol name is suppressed."""
        details = HoverDetails(
            name="greet",
            kind="function",
            signature="greet()",
            docstring="Does the greeting.",
        )

        markdown = _format_hover_markdown(details)

        assert "```python" not in markdown
        assert markdown == "Does the greeting."

    def test_empty_details_produce_a_placeholder(self):
        """A symbol without documentation still yields a readable body."""
        markdown = _format_hover_markdown(HoverDetails("value", "variable", ""))

        assert markdown == "*variable — no documentation available.*"

    def test_missing_kind_uses_generic_placeholder_label(self):
        """The fallback label is lower-case and generic when kind is blank."""
        markdown = _format_hover_markdown(HoverDetails("value", "", ""))

        assert markdown == "*symbol — no documentation available.*"

    def test_parameter_without_type_uses_any(self):
        """Untyped parameters are labelled ``any``."""
        details = HoverDetails(
            name="f",
            kind="function",
            signature="def f(value)",
            parameters=[ParameterInfo("value")],
        )

        assert "- **value** `any`" in _format_hover_markdown(details)


class TestProviderHoverFlow:
    """Tests for the provider-level hover orchestration."""

    @staticmethod
    def _provider(
        details: HoverDetails | None,
    ) -> tuple[PythonLanguageProvider, RecordingAdapter]:
        adapter = RecordingAdapter(hover=details)
        return PythonLanguageProvider(adapter=adapter), adapter

    def test_hover_details_are_returned_from_the_adapter(self, hover_details):
        """A valid identifier is forwarded to the adapter and returned as-is."""
        provider, adapter = self._provider(hover_details)

        result = provider.get_hover_details("value = call(value)", 0, 14)

        assert result is hover_details
        assert adapter.calls[0][0] == "hover"

    def test_hover_context_uses_one_based_line_and_raw_column(self, hover_details):
        """The editor's 0-based row is converted to Jedi's 1-based line."""
        provider, adapter = self._provider(hover_details)
        provider.file_path = "/tmp/module.py"
        provider.project_root = "/tmp/project"

        provider.get_hover_details("first\nsecond", 1, 3)

        context = adapter.calls[0][1]
        assert context.source_code == "first\nsecond"
        assert context.line == 2
        assert context.column == 3
        assert context.file_path == "/tmp/module.py"
        assert context.project_root == "/tmp/project"

    def test_explicit_paths_override_provider_defaults(self, hover_details):
        """Per-request paths take precedence over configured defaults."""
        provider, adapter = self._provider(hover_details)
        provider.file_path = "/tmp/default.py"
        provider.project_root = "/tmp/default"

        provider.get_hover_details(
            "value",
            0,
            0,
            file_path="/tmp/explicit.py",
            project_root="/tmp/explicit",
        )

        context = adapter.calls[0][1]
        assert context.file_path == "/tmp/explicit.py"
        assert context.project_root == "/tmp/explicit"

    def test_empty_text_short_circuits_without_adapter_call(self):
        """An empty buffer never reaches Jedi."""
        provider, adapter = self._provider(None)

        assert provider.get_hover_details("", 0, 0) is None
        assert adapter.calls == []

    @pytest.mark.parametrize("source", ["def f(): pass", "for item in values: pass"])
    def test_keyword_hover_is_rejected(self, source):
        """Python keywords have no useful Jedi hover in this contract."""
        provider, adapter = self._provider(HoverDetails("def", "keyword", "def"))

        assert provider.get_hover_details(source, 0, 1) is None
        assert adapter.calls == []

    def test_string_literal_hover_is_rejected(self):
        """A caret inside a string literal does not invoke Jedi."""
        provider, adapter = self._provider(None)

        assert provider.get_hover_details('value = "text"', 0, 10) is None
        assert adapter.calls == []

    def test_adapter_none_is_preserved(self):
        """Jedi's ``None`` result is returned without manufacturing details."""
        provider, _adapter = self._provider(None)

        assert provider.get_hover_details("value = 1", 0, 0) is None

    def test_hover_hint_renders_adapter_details(self, hover_details):
        """The legacy HTML hint is produced from the domain details."""
        provider, _adapter = self._provider(hover_details)

        hint = provider.get_hover_hint("greet(name)", 0, 1)

        assert hint is not None
        assert "greet" in hint
        assert "Parameters:" in hint

    def test_hover_hint_returns_none_when_adapter_has_no_details(self):
        """No details means no tooltip."""
        provider, _adapter = self._provider(None)

        assert provider.get_hover_hint("value = 1", 0, 0) is None

    def test_hover_hint_on_empty_text_returns_none(self):
        """The empty-buffer shortcut applies to the HTML hint too."""
        provider, adapter = self._provider(HoverDetails("x", "variable", "x = 1"))

        assert provider.get_hover_hint("", 0, 0) is None
        assert adapter.calls == []

    def test_hover_display_returns_title_and_markdown_body(self, hover_details):
        """The flyout receives a human-readable title and Markdown body."""
        provider, _adapter = self._provider(hover_details)

        display = provider.get_hover_display("greet(name)", 0, 1)

        assert display is not None
        title, body = display
        assert title == "## greet (Function)"
        assert "### Parameters (2)" in body

    def test_hover_display_without_kind_omits_parentheses(self):
        """A missing kind produces a plain title."""
        provider, _adapter = self._provider(HoverDetails("value", "", "value = 1"))

        display = provider.get_hover_display("value = 1", 0, 0)

        assert display is not None
        assert display[0] == "## value"

    def test_hover_display_returns_none_without_details(self):
        """No domain details means no flyout payload."""
        provider, _adapter = self._provider(None)

        assert provider.get_hover_display("value = 1", 0, 0) is None


class TestHoverModuleSurface:
    """Tests for module-level helpers exported by the provider module."""

    def test_module_exposes_documented_helpers(self):
        """The private helpers are part of the module's tested surface."""
        assert provider_module._is_inside_string is _is_inside_string
        assert provider_module._format_qt_tooltip is _format_qt_tooltip
        assert provider_module._format_hover_markdown is _format_hover_markdown
