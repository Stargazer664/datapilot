from __future__ import annotations

import json
from typing import Any


class ChartValidationError(ValueError):
    """Raised when a chart specification includes unsupported content."""


_ALLOWED_TRACE_TYPES = {"bar", "line", "scatter", "pie", "indicator"}
_ALLOWED_TRACE_KEYS = {
    "type",
    "mode",
    "name",
    "x",
    "y",
    "labels",
    "values",
    "text",
    "hovertemplate",
    "marker",
    "line",
    "value",
    "title",
}
_ALLOWED_LAYOUT_KEYS = {
    "title",
    "xaxis",
    "yaxis",
    "legend",
    "margin",
    "height",
    "showlegend",
    "paper_bgcolor",
    "plot_bgcolor",
    "font",
}


def _contains_unsafe_value(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False).lower()
    return "javascript:" in text or "<script" in text or "http://" in text or "https://" in text


def validate_plotly_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if _contains_unsafe_value(spec):
        raise ChartValidationError("图表包含远程或可执行内容")
    data = spec.get("data")
    if not isinstance(data, list) or not data:
        raise ChartValidationError("图表必须包含数据序列")
    for trace in data:
        if not isinstance(trace, dict) or trace.get("type") not in _ALLOWED_TRACE_TYPES:
            raise ChartValidationError("图表类型不受支持")
        unknown = set(trace) - _ALLOWED_TRACE_KEYS
        if unknown:
            raise ChartValidationError(f"图表字段不受支持：{', '.join(sorted(unknown))}")
    layout = spec.get("layout", {})
    if not isinstance(layout, dict) or set(layout) - _ALLOWED_LAYOUT_KEYS:
        raise ChartValidationError("图表布局字段不受支持")
    return {"data": data, "layout": layout}
