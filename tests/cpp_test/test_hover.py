"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Tests for C++ hover extraction, Markdown rendering, and symbol detection.
"""

from __future__ import annotations

import pytest

from editor.Ironica.plugins.cpp.models import CppHoverDetails
from editor.Ironica.plugins.cpp.provider import CppProvider


class TestCppHoverModels:
    """Tests for the CppHoverDetails domain model."""

    def test_hover_details_creation_with_all_fields(self):
        """CppHoverDetails can be created with all optional fields."""
        details = CppHoverDetails(
            name="foo",
            kind="function",
            signature="int foo(int a, double b) const",
            parameters=["a: int", "b: double"],
            return_type="int",
            docstring="Computes foo.",
        )
        assert details.name == "foo"
        assert details.kind == "function"
        assert details.signature == "int foo(int a, double b) const"
        assert details.parameters == ["a: int", "b: double"]
        assert details.return_type == "int"
        assert details.docstring == "Computes foo."

    def test_hover_details_creation_minimal(self):
        """CppHoverDetails works with only required fields."""
        details = CppHoverDetails(name="bar", kind="variable", signature="int bar")
        assert details.name == "bar"
        assert details.kind == "variable"
        assert details.signature == "int bar"
        assert details.parameters == []
        assert details.return_type is None
        assert details.docstring is None


class TestCppProviderHoverFormatting:
    """Tests for the provider's Markdown formatting."""

    @pytest.fixture
    def provider(self) -> CppProvider:
        """Return a CppProvider instance."""
        return CppProvider()

    def test_format_hover_markdown_with_full_details(self, provider: CppProvider):
        """Full hover details render a complete Markdown document."""
        details = CppHoverDetails(
            name="calculate",
            kind="function",
            signature="double calculate(double x, int y) noexcept",
            parameters=["x: double", "y: int"],
            return_type="double",
            docstring="Performs calculation.\n\nReturns the result.",
        )
        title, body = provider._format_hover_markdown(details)

        assert title == "## calculate (Function)"
        assert "```cpp" in body
        assert "double calculate(double x, int y) noexcept" in body
        assert "### Parameters (2)" in body
        assert "- `x: double`" in body
        assert "- `y: int`" in body
        assert "**Returns:** `double`" in body
        assert "---" in body
        assert "Performs calculation." in body
        assert "Returns the result." in body

    def test_format_hover_markdown_without_parameters(self, provider: CppProvider):
        """Hover without parameters still renders signature and docstring."""
        details = CppHoverDetails(
            name="PI",
            kind="variable",
            signature="constexpr double PI = 3.14159",
            docstring="Mathematical constant pi.",
        )
        title, body = provider._format_hover_markdown(details)

        assert title == "## PI (Variable)"
        assert "```cpp" in body
        assert "constexpr double PI = 3.14159" in body
        assert "### Parameters" not in body
        assert "**Returns:**" not in body
        assert "Mathematical constant pi." in body

    def test_format_hover_markdown_without_signature(self, provider: CppProvider):
        """Missing signature falls back to docstring or placeholder."""
        details = CppHoverDetails(
            name="unknown_symbol",
            kind="function",
            signature="",
            docstring="No signature available.",
        )
        title, body = provider._format_hover_markdown(details)

        assert title == "## unknown_symbol (Function)"
        assert "```cpp" not in body
        assert body == "No signature available."

    def test_format_hover_markdown_minimal_placeholder(self, provider: CppProvider):
        """A symbol with no info produces a readable placeholder."""
        details = CppHoverDetails(name="mystery", kind="class", signature="")
        title, body = provider._format_hover_markdown(details)

        assert title == "## mystery (Class)"
        assert body == "*class — no documentation available.*"

    def test_format_hover_markdown_handles_backticks_in_signature(
        self, provider: CppProvider
    ):
        """Backticks in signature are preserved in code block (uses different delimiter)."""
        details = CppHoverDetails(
            name="templated",
            kind="function",
            signature="void templated<`int`>()",
        )
        title, body = provider._format_hover_markdown(details)

        # Code blocks preserve content; we use ```cpp so backticks are fine
        assert "```cpp" in body
        assert "void templated<`int`>()" in body

    def test_format_hover_markdown_empty_kind(self, provider: CppProvider):
        """Empty kind produces plain title without parentheses."""
        details = CppHoverDetails(name="value", kind="", signature="int value")
        title, body = provider._format_hover_markdown(details)

        assert title == "## value"
        assert "### Parameters" not in body


class TestCppCommentCleaning:
    """Tests for C/C++ comment marker stripping."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("/// Adds two integers.", "Adds two integers."),
            ("//! Brief comment.", "Brief comment."),
            ("// Plain comment.", "Plain comment."),
            ("/** Block comment. */", "Block comment."),
            (
                "/**\n * Multi-line block.\n * Second line.\n */",
                "Multi-line block.\nSecond line.",
            ),
            (
                "/// First line.\n/// Second line.",
                "First line.\nSecond line.",
            ),
            ("///\n/// Body after blank.\n", "Body after blank."),
            ("", None),
            ("///", None),
        ],
    )
    def test_clean_comment_strips_markers(self, raw, expected):
        """Every supported comment style is reduced to readable prose."""
        from editor.Ironica.plugins.cpp.navigation.engine import NavigationEngine

        assert NavigationEngine._clean_comment(raw) == expected


class _FakeType:
    def __init__(self, spelling: str) -> None:
        self.spelling = spelling


class _FakeArgument:
    def __init__(self, name: str, type_spelling: str) -> None:
        self.spelling = name
        self.type = _FakeType(type_spelling)


class _FakeKind:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeCursor:
    def __init__(
        self,
        *,
        arguments=None,
        result_type="",
        const_method=False,
        type_spelling="",
    ) -> None:
        self._arguments = arguments or []
        self.result_type = _FakeType(result_type)
        self._const_method = const_method
        self.type = _FakeType(type_spelling)

    def get_arguments(self):
        return list(self._arguments)

    def is_const_method(self):
        return self._const_method


class TestCppSignatureConstruction:
    """Tests for cursor-to-signature mapping."""

    @staticmethod
    def _construct(cursor, name, kind):
        from editor.Ironica.plugins.cpp.navigation.engine import NavigationEngine

        return NavigationEngine._cursor_signature(cursor, name, kind)

    def test_function_signature_includes_name_return_and_parameters(self):
        """Functions render a complete C-like prototype."""
        cursor = _FakeCursor(
            arguments=[_FakeArgument("a", "int"), _FakeArgument("b", "double")],
            result_type="int",
        )

        signature, return_type, parameters = self._construct(cursor, "add", "function")

        assert signature == "int add(int a, double b)"
        assert return_type == "int"
        assert parameters == ["int a", "double b"]

    def test_const_method_signature_appends_const(self):
        """Const methods preserve their qualifier."""
        cursor = _FakeCursor(result_type="const std::string &", const_method=True)

        signature, return_type, parameters = self._construct(cursor, "label", "method")

        assert signature == "const std::string & label() const"
        assert return_type == "const std::string &"
        assert parameters == []

    def test_constructor_omits_return_type(self):
        """Constructors have no return type."""
        cursor = _FakeCursor(
            arguments=[_FakeArgument("value", "int")],
            result_type="void",
        )

        signature, return_type, parameters = self._construct(
            cursor, "Widget", "constructor"
        )

        assert signature == "Widget(int value)"
        assert return_type == "void"
        assert parameters == ["int value"]

    @pytest.mark.parametrize(
        ("kind", "name", "expected"),
        [
            ("class", "Widget", "class Widget"),
            ("struct", "Widget", "struct Widget"),
            ("enum", "Color", "enum Color"),
            ("namespace", "detail", "namespace detail"),
        ],
    )
    def test_type_declarations_use_keyword_prefix(self, kind, name, expected):
        """Class/struct/enum/namespace declarations are self-describing."""
        signature, return_type, parameters = self._construct(_FakeCursor(), name, kind)

        assert signature == expected
        assert return_type is None
        assert parameters == []

    def test_variable_signature_prefixes_type(self):
        """Variables render as ``type name``."""
        cursor = _FakeCursor(type_spelling="int")

        signature, return_type, parameters = self._construct(
            cursor, "value", "variable"
        )

        assert signature == "int value"
        assert return_type == "int"
        assert parameters == []


class TestCppProviderHoverIntegration:
    """Integration-style tests for the provider hover flow."""

    @pytest.fixture
    def provider(self) -> CppProvider:
        return CppProvider()

    def test_get_hover_display_returns_none_for_empty_text(self, provider: CppProvider):
        """Empty buffer returns no hover."""
        result = provider.get_hover_display("", 0, 0)
        assert result is None

    def test_get_hover_display_returns_none_for_whitespace_only(
        self, provider: CppProvider
    ):
        """Whitespace-only buffer returns no hover."""
        result = provider.get_hover_display("   \n\t  ", 0, 0)
        assert result is None


# NOTE: Full integration tests with libclang require a compile_commands.json
# and are slow. They are covered in separate integration test modules.
# These unit tests verify the formatting logic and model structure.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
