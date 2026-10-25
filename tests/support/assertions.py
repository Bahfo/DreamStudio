"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Custom assertions for DreamStudio tests.
"""

from collections.abc import Sequence
from pathlib import Path

import pytest


def assert_valid_run_id(run_id: str):
    """Assert run_id follows ``YYYYMMDDTHHMMSSZ-gitrev[-dirty][-N]``."""
    import re

    pattern = r"^\d{8}T\d{6}Z-[a-f0-9]{7,}(-dirty)?(-\d+)?$"
    assert re.match(pattern, run_id), f"Invalid run_id format: {run_id}"


def assert_test_result_structure(result: dict):
    """Assert test result has expected structure."""
    required_keys = {"name", "status", "duration", "file", "line"}
    assert all(
        k in result for k in required_keys
    ), f"Missing keys in result: {required_keys - set(result.keys())}"
    assert result["status"] in {"passed", "failed", "skipped", "blocked", "error"}
    assert isinstance(result["duration"], (int, float))
    assert result["duration"] >= 0
    assert isinstance(result["line"], int)


def assert_suite_result_structure(result: dict):
    """Assert suite result has expected structure."""
    required_keys = {"name", "path", "tests", "start_time", "end_time", "exit_code"}
    assert all(
        k in result for k in required_keys
    ), f"Missing keys in suite result: {required_keys - set(result.keys())}"
    assert isinstance(result["tests"], list)
    for test in result["tests"]:
        assert_test_result_structure(test)


def assert_summary_structure(summary: dict):
    """Assert run summary has expected structure."""
    required_keys = {
        "run_id",
        "timestamp",
        "suites",
        "total_tests",
        "passed",
        "failed",
        "skipped",
        "blocked",
        "errors",
        "duration",
        "exit_code",
    }
    assert all(
        k in summary for k in required_keys
    ), f"Missing keys in summary: {required_keys - set(summary.keys())}"
    assert isinstance(summary["suites"], list)
    for suite in summary["suites"]:
        assert_suite_result_structure(suite)


def assert_report_exists(run_dir: Path):
    """Assert run directory contains expected report files."""
    assert (run_dir / "report.md").exists(), "report.md missing"
    assert (run_dir / "summary.json").exists(), "summary.json missing"
    assert (run_dir / "console.log").exists(), "console.log missing"
    assert (run_dir / "environment.txt").exists(), "environment.txt missing"


def assert_history_updated(history_file: Path, run_id: str):
    """Assert HISTORY.md contains entry for run_id."""
    content = history_file.read_text()
    assert run_id in content, f"Run ID {run_id} not found in history"


def assert_suite_readme_updated(readme: Path, run_id: str):
    """Assert suite README contains entry for run_id."""
    content = readme.read_text()
    assert run_id in content, f"Run ID {run_id} not found in suite README"


def assert_no_production_code_changes(changed_files: Sequence[str]):
    """Assert no production code files were modified (only test files)."""
    production_dirs = {
        "editor/",
        "bootstrap/",
        "config/",
        "DreamCLI/",
        "hex-editor/",
        "manifests/",
        "packaging/",
    }
    for f in changed_files:
        for prod_dir in production_dirs:
            assert not f.startswith(prod_dir), f"Production code modified: {f}"


def assert_test_file_not_weakened(original: str, modified: str):
    """Assert test file wasn't weakened (assertions removed, etc.)."""
    # Check for removed assertions
    original_asserts = original.count("assert ")
    modified_asserts = modified.count("assert ")
    assert modified_asserts >= original_asserts * 0.9, "Significant assertion removal detected"

    # Check for removed test functions
    import re

    original_tests = len(re.findall(r"def test_\w+", original))
    modified_tests = len(re.findall(r"def test_\w+", modified))
    assert modified_tests >= original_tests, "Test functions removed"

    # Check for added skip/xfail markers
    original_skips = original.count("@pytest.mark.skip") + original.count("@pytest.mark.xfail")
    modified_skips = modified.count("@pytest.mark.skip") + modified.count("@pytest.mark.xfail")
    assert modified_skips <= original_skips + 1, "Unjustified skip/xfail added"


class AssertionHelper:
    """Helper class for complex assertions."""

    @staticmethod
    def assert_eventually(condition: callable, timeout: float = 5.0, interval: float = 0.05, msg: str = ""):
        """Assert condition becomes true within timeout."""
        import time

        start = time.time()
        while time.time() - start < timeout:
            if condition():
                return
            time.sleep(interval)
        pytest.fail(f"Condition not met within {timeout}s: {msg}")

    @staticmethod
    def assert_signal_sequence(signal_obj, expected_sequence: list, timeout: float = 5.0):
        """Assert signal emits expected sequence of arguments."""
        import time

        received = []
        signal_obj.connect(lambda *args: received.append(args))

        start = time.time()
        while len(received) < len(expected_sequence) and time.time() - start < timeout:
            time.sleep(0.01)

        assert (
            received == expected_sequence
        ), f"Signal sequence mismatch: got {received}, expected {expected_sequence}"

    @staticmethod
    def assert_dict_subset(subset: dict, superset: dict, path: str = ""):
        """Assert all keys in subset exist in superset with same values."""
        for key, value in subset.items():
            current_path = f"{path}.{key}" if path else key
            assert key in superset, f"Missing key {current_path}"
            if isinstance(value, dict) and isinstance(superset[key], dict):
                AssertionHelper.assert_dict_subset(value, superset[key], current_path)
            else:
                assert superset[key] == value, f"Value mismatch at {current_path}: {superset[key]} != {value}"


# Convenience function
assert_eventually = AssertionHelper.assert_eventually
assert_signal_sequence = AssertionHelper.assert_signal_sequence
assert_dict_subset = AssertionHelper.assert_dict_subset
