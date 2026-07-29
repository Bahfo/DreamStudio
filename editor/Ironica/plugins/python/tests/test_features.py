"""
Pure headless unit tests validating the refactoring & complexity engines.
Run with: pytest test_features.py
"""

import pytest
from editor.Ironica.plugins.python.utils.complexity import ComplexityAnalysisService


def test_complexity_calculations() -> None:
    """Verifies branch-logic increases cyclomatic complexity counts accurately."""
    code = (
        "def evaluate_val(x):\n"
        "    if x > 10:\n"  # CC +1
        "        if x < 20:\n"  # CC +1
        "            return 'mid'\n"
        "        return 'high'\n"
        "    return 'low'\n"
    )
    service = ComplexityAnalysisService()
    report = service.analyze_source(code)

    assert report.total_loc == 6
    assert report.function_count == 1
    assert len(report.functions) == 1

    func = report.functions[0]
    assert func.name == "evaluate_val"
    assert func.cyclomatic_complexity == 3  # Entry path + 2 conditional branches
    assert func.nesting_depth == 2  # Nested 'if' block


def test_empty_source_complexity_resilience() -> None:
    """Verifies complexity calculation returns safe default structures for blank source files."""
    service = ComplexityAnalysisService()
    report = service.analyze_source("   \n\n  ")

    assert report.total_loc == 0
    assert report.function_count == 0
    assert report.max_cyclomatic_complexity == 1
