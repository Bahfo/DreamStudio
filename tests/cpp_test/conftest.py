"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Pytest configuration for C++ plugin tests.
"""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test (requires libclang)")
    config.addinivalue_line("markers", "slow: mark test as slow running")