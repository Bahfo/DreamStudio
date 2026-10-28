"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for ServiceRegistry key-value storage.
"""

import pytest


class TestServiceRegistry:
    """Tests for ServiceRegistry key-value storage."""

    def test_register_and_get(self):
        """Register and retrieve a service by string key."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()
        registry.register("test_key", "test_value")

        assert registry.get("test_key") == "test_value"
        assert registry.has("test_key") is True
        assert registry.has("missing_key") is False

    def test_register_factory_is_lazy(self):
        """Factory services are instantiated only on first access."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        registry.register_factory("lazy_service", factory)
        assert call_count == 0
        assert registry.has("lazy_service") is True

        assert registry.get("lazy_service") == "instance_1"
        assert registry.get("lazy_service") == "instance_1"
        assert call_count == 1
        assert registry.is_initialized("lazy_service") is True

    def test_get_missing_raises(self):
        """Getting a missing key raises KeyError with the key name."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()

        with pytest.raises(KeyError, match="nonexistent"):
            registry.get("nonexistent")

    def test_registered_and_initialized_names(self):
        """Registered/initialized name listings reflect registry state."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()
        registry.register("eager", object())
        registry.register_factory("lazy", lambda: object())

        assert registry.registered_names() == ["eager", "lazy"]
        assert registry.initialized_names() == ["eager"]

        registry.get("lazy")
        assert registry.initialized_names() == ["eager", "lazy"]

    def test_clear(self):
        """clear removes services, factories, and initialization state."""
        from config.registry import ServiceRegistry

        registry = ServiceRegistry()
        registry.register("eager", object())
        registry.register_factory("lazy", lambda: object())
        registry.get("lazy")

        registry.clear()

        assert registry.registered_names() == []
        assert registry.initialized_names() == []
        assert registry.has("eager") is False
        assert registry.has("lazy") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])