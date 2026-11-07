"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared fixtures for terminal subsystem tests.
"""

import os
import sys

import pytest


@pytest.fixture
def temp_cwd(tmp_path):
    d = tmp_path / "cwd"
    d.mkdir()
    return str(d)
