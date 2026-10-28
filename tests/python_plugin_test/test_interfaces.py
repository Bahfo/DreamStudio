"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the ``IJediAdapter`` bridge contract.
"""

from __future__ import annotations

import pytest

from editor.Ironica.plugins.python.domain_models import (
    CompletionDetails,
    DefinitionLocation,
    HoverDetails,
    PythonContext,
)
from editor.Ironica.plugins.python.interfaces import IJediAdapter
from editor.Ironica.plugins.python.jedi_adapter import JediAdapter


class _CompleteAdapter(IJediAdapter):
    """Minimal implementation satisfying the entire bridge contract."""

    def get_hover(self, context: PythonContext):
        return HoverDetails("name", "variable", "name = 1")

    def get_definition(self, context: PythonContext):
        return DefinitionLocation("/tmp/a.py", 1, 0)

    def get_completions(self, context: PythonContext):
        return [CompletionDetails("item")]


class TestIJediAdapterContract:
    """Tests for abstract-method enforcement and substitution."""

    def test_interface_cannot_be_instantiated(self):
        """The bridge is abstract and rejects direct construction."""
        with pytest.raises(TypeError):
            IJediAdapter()

    def test_interface_declares_exactly_three_operations(self):
        """The bridge exposes hover, definition, and completion operations."""
        assert IJediAdapter.__abstractmethods__ == frozenset(
            {"get_hover", "get_definition", "get_completions"}
        )

    @pytest.mark.parametrize(
        "missing",
        ["get_hover", "get_definition", "get_completions"],
    )
    def test_each_abstract_method_is_mandatory(self, missing):
        """Omitting any single operation leaves the adapter abstract."""
        attributes = {
            "get_hover": lambda self, context: None,
            "get_definition": lambda self, context: None,
            "get_completions": lambda self, context: [],
        }
        attributes.pop(missing)
        partial = type(f"Partial_{missing}", (IJediAdapter,), attributes)

        with pytest.raises(TypeError):
            partial()

    def test_complete_subclass_is_instantiable(self):
        """A subclass implementing all three methods can be created."""
        adapter = _CompleteAdapter()

        assert isinstance(adapter, IJediAdapter)

    def test_domain_models_round_trip_through_interface(self):
        """The interface accepts and returns the documented domain models."""
        adapter = _CompleteAdapter()
        context = PythonContext("name = 1", 1, 0)

        hover = adapter.get_hover(context)
        definition = adapter.get_definition(context)
        completions = adapter.get_completions(context)

        assert isinstance(hover, HoverDetails)
        assert isinstance(definition, DefinitionLocation)
        assert isinstance(completions[0], CompletionDetails)

    def test_jedi_adapter_implements_the_interface(self):
        """The production Jedi adapter is a valid bridge implementation."""
        adapter = JediAdapter()

        assert isinstance(adapter, IJediAdapter)
        assert JediAdapter.__abstractmethods__ == frozenset()
