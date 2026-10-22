"""Bootstrap kernel for DreamStudio IDE."""

from config.registry import ServiceRegistry
from config.config import ConfigurationService
from config.resources import ResourceManager
from config.splash import SplashController
from config.recovery import RecoveryWindow
from config.manager import BootstrapManager

__all__ = [
    "ServiceRegistry",
    "ConfigurationService",
    "ResourceManager",
    "SplashController",
    "RecoveryWindow",
    "BootstrapManager",
]
