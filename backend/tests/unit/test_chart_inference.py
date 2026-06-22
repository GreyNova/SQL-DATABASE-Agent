"""Tests for chart-type inference."""
from __future__ import annotations

from app.services.chart_inference import infer_chart


def test_kpi_for_single_cell():
    chart = infer_chart([{"total": 12345.0}], "total revenue")
    assert chart.type == "kpi"
    assert chart.value_field == "total"


def test_line_for_temporal_series():
    rows = [
        {"month": "2025-01", "revenue": 1000.0},
        {"month": "2025-02", "revenue": 1500.0},
    ]
    chart = infer_chart(rows, "revenue by month")
    assert chart.type == "line"
    assert chart.x_field == "month"
    assert chart.y_field == "revenue"


def test_bar_for_category_measure():
    rows = [
        {"city": "Mumbai", "total": 1000.0},
        {"city": "Delhi", "total": 800.0},
    ]
    chart = infer_chart(rows, "revenue by city")
    assert chart.type == "bar"


def test_pie_for_few_categories_share_question():
    rows = [{"category": "A", "total": 1.0}, {"category": "B", "total": 2.0}]
    chart = infer_chart(rows, "revenue distribution by category")
    assert chart.type == "pie"


def test_table_for_empty():
    chart = infer_chart([], "anything")
    assert chart.type == "table"
