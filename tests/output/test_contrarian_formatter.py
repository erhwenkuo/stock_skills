"""Tests for format_contrarian_markdown in src/output/formatter.py (KIK-504)."""

import pytest

from src.output.formatter import format_contrarian_markdown


def _make_contrarian_result(
    symbol="7203.T",
    name="Toyota Motor",
    price=2850.0,
    per=8.0,
    pbr=0.7,
    rsi=25.0,
    sma200_deviation=-0.15,
    tech_score=25.0,
    val_score=20.0,
    fund_score=18.0,
    contrarian_score=63.0,
    contrarian_grade="B",
):
    return {
        "symbol": symbol,
        "name": name,
        "price": price,
        "per": per,
        "pbr": pbr,
        "rsi": rsi,
        "sma200_deviation": sma200_deviation,
        "tech_score": tech_score,
        "val_score": val_score,
        "fund_score": fund_score,
        "contrarian_score": contrarian_score,
        "contrarian_grade": contrarian_grade,
    }


class TestFormatContrarianMarkdown:
    def test_empty_results(self):
        result = format_contrarian_markdown([])
        assert "見つかりませんでした" in result

    def test_single_result(self):
        results = [_make_contrarian_result()]
        output = format_contrarian_markdown(results)
        assert "7203.T" in output
        assert "Toyota Motor" in output
        assert "テク" in output
        assert "バリュ" in output
        assert "ファンダ" in output

    def test_grade_display(self):
        results = [
            _make_contrarian_result(symbol="A.T", contrarian_grade="A", contrarian_score=75),
            _make_contrarian_result(symbol="B.T", contrarian_grade="B", contrarian_score=55),
            _make_contrarian_result(symbol="C.T", contrarian_grade="C", contrarian_score=35),
        ]
        output = format_contrarian_markdown(results)
        assert "A" in output
        assert "B" in output
        assert "C" in output

    def test_table_has_header_and_separator(self):
        results = [_make_contrarian_result()]
        output = format_contrarian_markdown(results)
        lines = output.split("\n")
        assert "| 順位 |" in lines[0]
        assert "|---:" in lines[1]

    def test_legend_present(self):
        results = [_make_contrarian_result()]
        output = format_contrarian_markdown(results)
        assert "凡例" in output
        assert "判定" in output

    def test_multiple_results_ranking(self):
        results = [
            _make_contrarian_result(symbol="1001.T", contrarian_score=80, contrarian_grade="A"),
            _make_contrarian_result(symbol="1002.T", contrarian_score=55, contrarian_grade="B"),
        ]
        output = format_contrarian_markdown(results)
        assert "| 1 |" in output
        assert "| 2 |" in output

    def test_none_values_handled(self):
        result = _make_contrarian_result()
        result["rsi"] = None
        result["sma200_deviation"] = None
        output = format_contrarian_markdown([result])
        assert "-" in output  # None values render as "-"
