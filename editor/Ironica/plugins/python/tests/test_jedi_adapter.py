"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Unit tests validating JediAdapter functionality.
These run completely headless and independent of Qt or any UI environment.
Run with: pytest test_jedi_adapter.py
"""

import pytest
from editor.Ironica.plugins.python.domain_models import PythonContext
from editor.Ironica.plugins.python.jedi_adapter import JediAdapter


def test_get_hover_signature() -> None:
    """Verifies that hover details can resolve detailed python signatures."""
    code = "def calc_sum(a: int, b: int = 10) -> int:\n    return a + b\n\ncalc_sum"
    context = PythonContext(source_code=code, line=4, column=4)

    adapter = JediAdapter()
    hover = adapter.get_hover(context)

    assert hover is not None
    assert hover.name == "calc_sum"
    assert hover.kind == "function"
    assert "calc_sum" in hover.signature
    assert len(hover.parameters) == 2
    assert hover.parameters[0].name == "a"
    assert hover.parameters[1].name == "b"
    assert hover.parameters[1].default_value == "10"


def test_get_definition_navigation() -> None:
    """Verifies that we can correctly trace a variable back to its definition point."""
    code = "my_var = 42\nprint(my_var)"
    context = PythonContext(source_code=code, line=2, column=8)

    adapter = JediAdapter()
    location = adapter.get_definition(context)

    assert location is not None
    assert location.line == 1
    assert location.column == 0
    assert "my_var" in (location.context_line or "")


def test_error_resiliency() -> None:
    """Verifies that the adapter gracefully recovers from bad positions or syntaxes."""
    context = PythonContext(source_code="import os", line=999, column=999)

    adapter = JediAdapter()
    hover = adapter.get_hover(context)
    definition = adapter.get_definition(context)

    assert hover is None
    assert definition is None
