"""
Bootstrap kernel for DreamStudio IDE.

Provides a layered startup architecture with clearly separated responsibilities:
- ServiceRegistry: central service container
- ConfigurationService: JSON-based configuration management
- ResourceManager: theme, icon, and asset loading with fallbacks
- SplashController: startup progress display
- RecoveryWindow: critical failure diagnostics
- BootstrapManager: startup orchestration and phase execution
"""

from bootstrap.registry import ServiceRegistry
from bootstrap.config import ConfigurationService
from bootstrap.resources import ResourceManager
from bootstrap.splash import SplashController
from bootstrap.recovery import RecoveryWindow
from bootstrap.manager import BootstrapManager

__all__ = [
    "ServiceRegistry",
    "ConfigurationService",
    "ResourceManager",
    "SplashController",
    "RecoveryWindow",
    "BootstrapManager",
]
