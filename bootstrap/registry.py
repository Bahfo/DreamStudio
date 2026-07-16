"""
ServiceRegistry: central service container for DreamStudio.

Owns all core and startup-critical services. Future services
(Python intelligence, diagnostics, workspace, extensions, terminals,
debugger, language providers) will register here without modifying
BootstrapManager.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Generic service container with lazy and eager registration."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Any] = {}
        self._initialized: set[str] = set()
        logger.info("ServiceRegistry created")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, service: Any) -> None:
        """Register an already-instantiated service."""
        if name in self._services:
            logger.warning("Overwriting existing service: %s", name)
        self._services[name] = service
        self._initialized.add(name)
        logger.info("Service registered: %s", name)

    def register_factory(self, name: str, factory: Any) -> None:
        """Register a callable that will create the service on first access."""
        if name not in self._services:
            self._factories[name] = factory
            logger.info("Service factory registered: %s", name)

    def _instantiate(self, name: str) -> Any:
        factory = self._factories.get(name)
        if factory is None:
            raise KeyError(f"No service or factory registered under '{name}'")
        service = factory()
        self._services[name] = service
        self._initialized.add(name)
        del self._factories[name]
        logger.info("Service instantiated from factory: %s", name)
        return service

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, name: str) -> Any:
        """Retrieve a service by name, instantiating from factory if needed."""
        if name in self._services:
            return self._services[name]
        if name in self._factories:
            return self._instantiate(name)
        raise KeyError(f"No service registered under '{name}'")

    def has(self, name: str) -> bool:
        return name in self._services or name in self._factories

    def is_initialized(self, name: str) -> bool:
        return name in self._initialized

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def registered_names(self) -> list[str]:
        """Return all registered service names (both live and deferred)."""
        return sorted(set(self._services) | set(self._factories))

    def initialized_names(self) -> list[str]:
        return sorted(self._initialized)

    def clear(self) -> None:
        """Remove all services. Primarily for testing."""
        self._services.clear()
        self._factories.clear()
        self._initialized.clear()
        logger.info("ServiceRegistry cleared")
