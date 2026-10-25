"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared test helper functions.
"""

import contextlib
import time
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock


@contextlib.contextmanager
def wait_for_signal(signal_obj, timeout: float = 5.0) -> Generator[None, None, None]:
    """
    Wait for a Qt signal to be emitted.

    Usage:
        with wait_for_signal(editor.dirty_state_changed):
            editor._on_text_changed()
    """
    result = []

    def handler(*args):
        result.append(args)

    signal_obj.connect(handler)
    try:
        yield
        start = time.time()
        while not result and time.time() - start < timeout:
            time.sleep(0.01)
    finally:
        try:
            signal_obj.disconnect(handler)
        except (TypeError, RuntimeError):
            pass


@contextlib.contextmanager
def wait_for_condition(
    condition: Callable[[], bool], timeout: float = 5.0, interval: float = 0.05
) -> Generator[None, None, None]:
    """
    Wait for a condition to become true.

    Usage:
        with wait_for_condition(lambda: editor.is_dirty()):
            editor._on_text_changed()
    """
    yield
    start = time.time()
    while not condition() and time.time() - start < timeout:
        time.sleep(interval)
    assert condition(), f"Condition not met within {timeout}s"


def create_test_file(path: Path, content: str, encoding: str = "utf-8") -> Path:
    """Create a test file with given content."""
    path.write_text(content, encoding=encoding)
    return path


def assert_signal_emitted(signal_obj, expected_args=None, timeout=1.0):
    """Assert a signal was emitted with expected arguments."""
    result = []

    def handler(*args):
        result.append(args)

    signal_obj.connect(handler)
    try:
        start = time.time()
        while not result and time.time() - start < timeout:
            time.sleep(0.01)
    finally:
        try:
            signal_obj.disconnect(handler)
        except (TypeError, RuntimeError):
            pass

    assert result, f"Signal {signal_obj} was not emitted within {timeout}s"

    if expected_args is not None:
        assert result[0] == expected_args, f"Signal args {result[0]} != {expected_args}"

    return result[0]


def get_private_attr(obj: Any, attr: str) -> Any:
    """Get private attribute for testing (use sparingly)."""
    return getattr(obj, f"_{obj.__class__.__name__}__{attr}", getattr(obj, f"_{attr}", None))


def set_private_attr(obj: Any, attr: str, value: Any) -> None:
    """Set private attribute for testing (use sparingly)."""
    private_name = f"_{obj.__class__.__name__}__{attr}"
    if hasattr(obj, private_name):
        setattr(obj, private_name, value)
    else:
        setattr(obj, f"_{attr}", value)


def call_private_method(obj: Any, method: str, *args, **kwargs) -> Any:
    """Call private method for testing (use sparingly)."""
    private_name = f"_{obj.__class__.__name__}__{method}"
    if hasattr(obj, private_name):
        return getattr(obj, private_name)(*args, **kwargs)
    return getattr(obj, f"_{method}")(*args, **kwargs)


class QtEventLoopHelper:
    """Helper for managing Qt event loop in tests."""

    def __init__(self, qapp):
        self.qapp = qapp

    def process_events(self, max_time: float = 0.1):
        """Process pending events for a short time."""
        self.qapp.processEvents()
        time.sleep(max_time)

    def wait_until(self, condition: Callable[[], bool], timeout: float = 5.0):
        """Wait until condition is true, processing events."""
        start = time.time()
        while not condition() and time.time() - start < timeout:
            self.qapp.processEvents()
            time.sleep(0.01)
        assert condition(), f"Condition not met within {timeout}s"


def make_editor_with_provider(provider, language="python"):
    """Create a CodeEditor bound to *provider* for navigation-style tests."""
    from editor.Ironica.code_editor import CodeEditor

    editor = CodeEditor(None, language=language)
    editor.current_provider = provider
    editor.current_lang = language
    return editor


def assert_file_contains(path: Path, expected: str):
    """Assert file contains expected text."""
    content = path.read_text()
    assert expected in content, f"Expected '{expected}' in {path}"


def assert_dir_structure(root: Path, structure: dict):
    """Assert directory structure matches expected dict."""
    for name, expected in structure.items():
        path = root / name
        if isinstance(expected, dict):
            assert path.is_dir(), f"Expected directory {path}"
            assert_dir_structure(path, expected)
        elif expected is True:
            assert path.exists(), f"Expected {path} to exist"
        elif expected is False:
            assert not path.exists(), f"Expected {path} to not exist"
        else:
            assert path.is_file(), f"Expected file {path}"
            if isinstance(expected, str):
                assert path.read_text() == expected
