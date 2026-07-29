"""
Tests for provider coordinate translation.
"""

from unittest.mock import Mock

from editor.Ironica.plugins.python.domain_models import (
    PythonContext,
)
from editor.Ironica.plugins.python.provider import PythonLanguageProvider
from editor.Ironica.plugins.python.cache import LanguageCache
from editor.Ironica.plugins.python.interfaces import IJediAdapter


class TestProviderCoordinateConversion:
    """Tests that the provider correctly translates 0-indexed to 1-indexed."""

    def test_provider_context_method_line_conversion(self):
        adapter = Mock(spec=IJediAdapter)
        adapter.get_hover.return_value = None
        cache = LanguageCache()
        provider = PythonLanguageProvider(adapter=adapter, cache=cache)

        provider.get_hover_hint("hello\nworld", line=1, col=3)

        call_args = adapter.get_hover.call_args
        ctx = call_args[0][0]
        assert ctx.line == 2
        assert ctx.column == 3
