"""
Unit tests testing Provider mapping and Caching mechanisms.
Mocking techniques isolate test execution from Jedi and Qt.
Run with: pytest test_provider.py
"""

from unittest.mock import Mock
import pytest

from editor.Ironica.plugins.python.provider import PythonLanguageProvider
from editor.Ironica.plugins.python.domain_models import CompletionItem
from editor.Ironica.plugins.python.interfaces import IJediAdapter
from editor.Ironica.plugins.python.cache import LanguageCache


def test_cache_hits_do_not_retrigger_adapter() -> None:
    """Verifies duplicate requests hit the cache and never invoke the adapter twice."""
    mock_adapter = Mock(spec=IJediAdapter)
    mock_adapter.get_completions.return_value = [
        CompletionItem(label="my_method", insert_text="my_method", kind="function")
    ]

    cache = LanguageCache()
    provider = PythonLanguageProvider(adapter=mock_adapter, cache=cache)

    code = "obj.my"
    line, col = 1, 6

    first_call = provider.get_auto_completions(code, line, col)
    assert first_call == ["my_method"]
    assert mock_adapter.get_completions.call_count == 1

    second_call = provider.get_auto_completions(code, line, col)
    assert second_call == ["my_method"]
    assert mock_adapter.get_completions.call_count == 1  # Should still be 1


def test_cache_invalidation_on_coordinate_change() -> None:
    """Verifies that changing code coordinates bypasses the cached entries."""
    mock_adapter = Mock(spec=IJediAdapter)
    mock_adapter.get_completions.return_value = []

    provider = PythonLanguageProvider(adapter=mock_adapter)

    # Context 1
    provider.get_auto_completions("x = 10", 1, 2)
    # Context 2 (different coordinate, must trigger lookup)
    provider.get_auto_completions("x = 10", 1, 5)

    assert mock_adapter.get_completions.call_count == 2
