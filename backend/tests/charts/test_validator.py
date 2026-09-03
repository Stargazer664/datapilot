import pytest

from analytics_app.charts.validator import ChartValidationError, validate_plotly_spec


def test_accepts_a_safe_bar_chart() -> None:
    spec = {
        "data": [{"type": "bar", "x": ["华东", "华南"], "y": [12, 9]}],
        "layout": {"title": {"text": "区域销售额"}},
    }
    assert validate_plotly_spec(spec)["data"][0]["type"] == "bar"


def test_rejects_remote_or_executable_content() -> None:
    with pytest.raises(ChartValidationError):
        validate_plotly_spec(
            {"data": [{"type": "bar", "x": [1], "y": [2], "customdata": "javascript:alert(1)"}]}
        )
