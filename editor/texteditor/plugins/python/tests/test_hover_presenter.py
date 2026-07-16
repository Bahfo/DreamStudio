"""
Unit tests for checking HoverPresenter performance under various structural conditions.
Runs headlessly without any Qt initialization.
Run with: pytest test_hover_presenter.py
"""

import pytest
from editor.texteditor.plugins.python.domain_models import HoverDetails, ParameterInfo
from editor.texteditor.plugins.python.hover_presenter import HoverPresenter


@pytest.fixture
def sample_hover_details() -> HoverDetails:
    """Fixture containing a complex simulated HoverDetails model."""
    return HoverDetails(
        name="fetch_records",
        kind="function",
        signature="def fetch_records(limit: int = 50, active_only: bool = True) -> list:",
        parameters=[
            ParameterInfo(name="limit", type_hint="int", default_value="50"),
            ParameterInfo(name="active_only", type_hint="bool", default_value="True"),
        ],
        return_type="list",
        docstring="    Retrieves active user entries.\n\n    Filters results in SQL.\n    ",
    )


def test_markdown_presentation_structure(sample_hover_details: HoverDetails) -> None:
    """Verifies markdown conversion contains all expected metadata components."""
    markdown = HoverPresenter.to_markdown(sample_hover_details)

    assert "### fetch_records (FUNCTION)" in markdown
    assert "```python" in markdown
    assert "`limit`" in markdown
    assert "*int*" in markdown
    assert "= `50`" in markdown
    assert "**Returns:** *list*" in markdown
    assert "Retrieves active user entries." in markdown


def test_html_presentation_styling(sample_hover_details: HoverDetails) -> None:
    """Verifies that the HTML presenter applies proper CSS color-coding tags."""
    html = HoverPresenter.to_html(sample_hover_details)

    # Check for VSCode standard CSS variables / styling tags
    assert "color: #569CD6;" in html  # Function highlight color
    assert "color: #4EC9B0;" in html  # Type hints highlights
    assert "color: #9CDCFE;" in html  # Parameter names
    assert "Retrieves active user entries." in html


def test_presenter_resilience_to_missing_values() -> None:
    """Ensures that the presenter gracefully handles sparse or empty hover metrics."""
    sparse_details = HoverDetails(
        name="plain_variable",
        kind="variable",
        signature="x: float",
    )

    markdown = HoverPresenter.to_markdown(sparse_details)
    html = HoverPresenter.to_html(sparse_details)

    # Plain text conversions must still construct base visual blocks gracefully
    assert "plain_variable" in markdown
    assert "plain_variable" in html
    assert "Parameters:" not in markdown
    assert "Parameters:" not in html
