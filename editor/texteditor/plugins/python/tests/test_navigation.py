"""
Unit and integration tests for navigation services.
Requires pytest. Run with: pytest test_navigation.py
"""

from unittest.mock import Mock
import pytest

from editor.texteditor.plugins.python.navigation import NavigationService, ReferenceFinderService
from editor.texteditor.plugins.python.domain_models import PythonContext, DefinitionLocation
from editor.texteditor.plugins.python.jedi_adapter import JediAdapter
from editor.texteditor.plugins.python.interfaces import IJediAdapter


def test_navigation_service_delegation() -> None:
    """Verifies NavigationService correctly calls the injected adapter."""
    mock_adapter = Mock(spec=IJediAdapter)
    expected_location = DefinitionLocation(
        file_path="main.py", line=10, column=4, context_line="def test():"
    )
    mock_adapter.get_definition.return_value = expected_location

    service = NavigationService(adapter=mock_adapter)
    context = PythonContext(source_code="test()", line=1, column=2)

    result = service.navigate_to_definition(context)

    assert result == expected_location
    mock_adapter.get_definition.assert_called_once_with(context)


def test_reference_finder_real_jedi() -> None:
    """Integration test verifying reference finder with the real JediAdapter."""
    code = (
        "def process_data(x):\n"
        "    return x + 1\n"
        "\n"
        "process_data(10)\n"
        "process_data(20)\n"
    )
    # Cursor is placed on the initial declaration of process_data
    context = PythonContext(source_code=code, line=1, column=5)

    adapter = JediAdapter()
    service = ReferenceFinderService(adapter=adapter)

    references = service.find_all_references(context)

    # We expect 3 total references: 1 declaration and 2 call usages
    assert len(references) == 3

    lines_found = [ref.line for ref in references]
    assert 1 in lines_found
    assert 4 in lines_found
    assert 5 in lines_found

    # Confirm context lines are extracted cleanly
    assert any("def process_data" in ref.context_line for ref in references)
