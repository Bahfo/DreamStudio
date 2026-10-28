"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for outline parser registration and building.
"""

import pytest


class TestOutlinePanel:
    """Tests for outline parser registration and building."""

    def test_build_outline_uses_registered_parser(self):
        """build_outline delegates to the parser and fills the root name."""
        from editor.utils.file_properties.outline import (
            OutlineNode,
            OutlineResult,
            SymbolKind,
            build_outline,
            register_parser,
            unregister_parser,
        )

        def parser(source):
            return OutlineResult(
                root=OutlineNode(
                    name="",
                    kind=SymbolKind.FILE,
                    children=[OutlineNode(name="function", kind=SymbolKind.FUNCTION)],
                ),
                language="testoutline",
            )

        register_parser("testoutline", parser)
        try:
            result = build_outline("def function(): pass", "testoutline", "test.py")

            assert result is not None
            assert result.root.name == "test.py"
            assert result.root.children[0].kind is SymbolKind.FUNCTION
        finally:
            unregister_parser("testoutline")

    def test_build_outline_without_parser_returns_none(self):
        """Unknown languages produce no outline."""
        from editor.utils.file_properties.outline import build_outline

        assert build_outline("text", "unknown-language-xyz") is None

    def test_unregister_parser(self):
        """unregister_parser removes a previously registered parser."""
        from editor.utils.file_properties.outline import (
            get_parser,
            register_parser,
            unregister_parser,
        )

        def parser(source):
            return None

        register_parser("testoutline2", parser)
        assert get_parser("testoutline2") is parser

        assert unregister_parser("testoutline2") is True
        assert get_parser("testoutline2") is None

    def test_symbol_kind_enum_values(self):
        """SymbolKind exposes the documented symbol categories."""
        from editor.utils.file_properties.outline import SymbolKind

        assert SymbolKind.FUNCTION.value == "function"
        assert SymbolKind.CLASS.value == "class"
        assert SymbolKind.METHOD.value == "method"
        assert SymbolKind.VARIABLE.value == "variable"
        assert SymbolKind.MODULE.value == "module"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])