"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the Python plugin's immutable-by-convention domain models.
"""

from __future__ import annotations

import dataclasses

import pytest

from editor.Ironica.plugins.python.domain_models import (
    CompletionDetails,
    DefinitionLocation,
    HoverDetails,
    ParameterInfo,
    PythonContext,
    ReferenceLocation,
)


class TestPythonContext:
    """Tests for the editor snapshot handed to the Jedi adapter."""

    def test_required_fields_are_preserved(self):
        """The snapshot keeps source, line, and column verbatim."""
        context = PythonContext(source_code="x = 1\n", line=4, column=11)

        assert context.source_code == "x = 1\n"
        assert context.line == 4
        assert context.column == 11

    def test_optional_fields_default_to_none(self):
        """Unsaved buffers have no file path or project root by default."""
        context = PythonContext(source_code="", line=1, column=0)

        assert context.file_path is None
        assert context.project_root is None

    def test_context_equality_is_value_based(self):
        """Two snapshots with identical values compare equal."""
        first = PythonContext("text", 2, 3, "/tmp/a.py", "/tmp")
        second = PythonContext("text", 2, 3, "/tmp/a.py", "/tmp")

        assert first == second
        assert first != PythonContext("text", 2, 4, "/tmp/a.py", "/tmp")

    def test_documented_immutability_is_convention_not_enforcement(self):
        """The dataclass is documented as immutable but is not frozen.

        This test records the current contract honestly: mutating a context
        silently succeeds. Callers must treat the object as read-only.
        """
        context = PythonContext("text", 2, 3)

        context.line = 99

        assert context.line == 99
        assert PythonContext.__dataclass_params__.frozen is False


class TestFrozenModels:
    """Tests for models that reject mutation at runtime."""

    def test_parameter_info_is_frozen(self):
        """ParameterInfo raises FrozenInstanceError on assignment."""
        parameter = ParameterInfo("value", "int", "1")

        with pytest.raises(dataclasses.FrozenInstanceError):
            parameter.name = "other"

    def test_hover_details_is_frozen(self):
        """HoverDetails raises FrozenInstanceError on assignment."""
        details = HoverDetails("func", "function", "def func()")

        with pytest.raises(dataclasses.FrozenInstanceError):
            details.signature = "def other()"

    def test_definition_location_is_frozen(self):
        """DefinitionLocation raises FrozenInstanceError on assignment."""
        location = DefinitionLocation("/tmp/a.py", 3, 4)

        with pytest.raises(dataclasses.FrozenInstanceError):
            location.line = 99

    def test_reference_location_is_frozen(self):
        """ReferenceLocation raises FrozenInstanceError on assignment."""
        reference = ReferenceLocation("/tmp/a.py", 3, 4, "value = 1", 5)

        with pytest.raises(dataclasses.FrozenInstanceError):
            reference.column = 0

    def test_completion_details_is_frozen(self):
        """CompletionDetails raises FrozenInstanceError on assignment."""
        completion = CompletionDetails("path")

        with pytest.raises(dataclasses.FrozenInstanceError):
            completion.text = "other"


class TestModelDefaults:
    """Tests for optional-field defaults and factory isolation."""

    def test_parameter_info_defaults(self):
        """Type hints and defaults are optional."""
        parameter = ParameterInfo("name")

        assert parameter.type_hint is None
        assert parameter.default_value is None

    def test_hover_details_parameter_lists_are_independent(self):
        """Each HoverDetails instance owns a distinct parameter list."""
        first = HoverDetails("a", "function", "def a()")
        second = HoverDetails("b", "function", "def b()")

        first.parameters.append(ParameterInfo("value"))

        assert second.parameters == []
        assert len(first.parameters) == 1

    def test_hover_details_optional_fields(self):
        """Return type and docstring default to None."""
        details = HoverDetails("a", "function", "def a()")

        assert details.return_type is None
        assert details.docstring is None

    def test_definition_location_context_line_defaults_to_none(self):
        """A definition may be reported without surrounding source."""
        location = DefinitionLocation("/tmp/a.py", 1, 0)

        assert location.context_line is None

    def test_completion_details_insert_text_defaults_to_empty(self):
        """Insert text is optional and defaults to the empty string."""
        completion = CompletionDetails("item")

        assert completion.insert_text == ""
        assert completion.kind == ""
        assert completion.signature == ""

    def test_completion_details_keeps_full_payload(self):
        """Every completion field is retained exactly as supplied."""
        completion = CompletionDetails(
            text="path",
            insert_text="path",
            kind="module",
            signature="def path(...)",
        )

        assert completion == CompletionDetails(
            "path", "path", "module", "def path(...)"
        )

    def test_reference_location_has_no_default_symbol_length(self):
        """ReferenceLocation requires an explicit symbol width for highlighting."""
        reference = ReferenceLocation("/tmp/a.py", 2, 4, "call(value)", 4)

        assert reference.file_path == "/tmp/a.py"
        assert reference.line == 2
        assert reference.column == 4
        assert reference.context_line == "call(value)"
        assert reference.symbol_length == 4
