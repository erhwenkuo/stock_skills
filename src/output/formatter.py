"""Output formatters for screening results (KIK-575: unified renderer)."""

from src.output._format_helpers import (
    fmt_pct as _fmt_pct,
    fmt_float as _fmt_float,
    fmt_currency_value as _fmt_currency_value,
    build_label as _build_label,
    render_screening_table,
)
from src.core.ticker_utils import lot_cost as _lot_cost, infer_currency as _infer_currency


# ---------------------------------------------------------------------------
# Common cell helpers
# ---------------------------------------------------------------------------

def _price_cell(rank, row):
    return _fmt_float(row.get("price"), decimals=0) if row.get("price") is not None else "-"


def _lot_cost_cell(rank, row):
    """Format minimum investment amount (lot cost) with currency symbol."""
    price = row.get("price")
    symbol = row.get("symbol", "")
    if price is None or not symbol:
        return "-"
    cost = _lot_cost(symbol, price)
    currency = _infer_currency(symbol)
    return _fmt_currency_value(cost, currency)


# ---------------------------------------------------------------------------
# 1. Default (legacy)
# ---------------------------------------------------------------------------

def format_markdown(results: list[dict]) -> str:
    """Format screening results as a Markdown table."""
    return render_screening_table(results, columns=[
        ("Rank", "---:", lambda r, row: str(r)),
        ("Symbol", ":-----", lambda r, row: _build_label(row)),
        ("Price", "-----:", _price_cell),
        ("PER", "----:", lambda r, row: _fmt_float(row.get("per"))),
        ("PBR", "----:", lambda r, row: _fmt_float(row.get("pbr"))),
        ("Div Yield", "---------:", lambda r, row: _fmt_pct(row.get("dividend_yield"))),
        ("ROE", "----:", lambda r, row: _fmt_pct(row.get("roe"))),
        ("Score", "------:", lambda r, row: _fmt_float(row.get("value_score"))),
    ], empty_msg="No matching stocks found.")


# ---------------------------------------------------------------------------
# 2. Query (value, high-dividend, etc.)
# ---------------------------------------------------------------------------

def format_query_markdown(results: list[dict]) -> str:
    """Format EquityQuery screening results with sector column."""
    return render_screening_table(results, columns=[
        ("Rank", "---:", lambda r, row: str(r)),
        ("Symbol", ":-----", lambda r, row: _build_label(row)),
        ("Sector", ":---------", lambda r, row: row.get("sector") or "-"),
        ("Price", "-----:", _price_cell),
        ("Min Investment", "---------:", _lot_cost_cell),
        ("PER", "----:", lambda r, row: _fmt_float(row.get("per"))),
        ("PBR", "----:", lambda r, row: _fmt_float(row.get("pbr"))),
        ("Div Yield", "---------:", lambda r, row: _fmt_pct(row.get("dividend_yield"))),
        ("ROE", "----:", lambda r, row: _fmt_pct(row.get("roe"))),
        ("Score", "------:", lambda r, row: _fmt_float(row.get("value_score"))),
    ], empty_msg="No matching stocks found.")


# ---------------------------------------------------------------------------
# 3. Pullback
# ---------------------------------------------------------------------------

def format_pullback_markdown(results: list[dict]) -> str:
    """Format pullback screening results."""
    def _bounce(r, row):
        bs = row.get("bounce_score")
        return f"{bs:.0f}pt" if bs is not None else "-"

    def _match(r, row):
        return "★Full match" if row.get("match_type", "full") == "full" else "△Partial match"

    return render_screening_table(results, columns=[
        ("Rank", "---:", lambda r, row: str(r)),
        ("Symbol", ":-----", lambda r, row: _build_label(row)),
        ("Price", "-----:", _price_cell),
        ("PER", "----:", lambda r, row: _fmt_float(row.get("per"))),
        ("Pullback%", "------:", lambda r, row: _fmt_pct(row.get("pullback_pct"))),
        ("RSI", "----:", lambda r, row: _fmt_float(row.get("rsi"), decimals=1)),
        ("Vol Ratio", "-------:", lambda r, row: _fmt_float(row.get("volume_ratio"))),
        ("SMA50", "------:", lambda r, row: _fmt_float(row.get("sma50"), decimals=0) if row.get("sma50") is not None else "-"),
        ("SMA200", "-------:", lambda r, row: _fmt_float(row.get("sma200"), decimals=0) if row.get("sma200") is not None else "-"),
        ("Score", "------:", _bounce),
        ("Match", ":------:", _match),
        ("Total Score", "------:", lambda r, row: _fmt_float(row.get("final_score") or row.get("value_score"))),
    ], empty_msg="No stocks met the pullback criteria. (No pullback stocks in uptrend)")


# ---------------------------------------------------------------------------
# 4. Growth
# ---------------------------------------------------------------------------

def format_growth_markdown(results: list[dict]) -> str:
    """Format growth screening results."""
    return render_screening_table(results, columns=[
        ("Rank", "---:", lambda r, row: str(r)),
        ("Symbol", ":-----", lambda r, row: _build_label(row)),
        ("Sector", ":---------", lambda r, row: row.get("sector") or "-"),
        ("Price", "-----:", _price_cell),
        ("PER", "----:", lambda r, row: _fmt_float(row.get("per"))),
        ("PBR", "----:", lambda r, row: _fmt_float(row.get("pbr"))),
        ("EPS Growth", "-------:", lambda r, row: _fmt_pct(row.get("eps_growth"))),
        ("Rev Growth", "--------:", lambda r, row: _fmt_pct(row.get("revenue_growth"))),
        ("ROE", "----:", lambda r, row: _fmt_pct(row.get("roe"))),
    ], empty_msg="No stocks met the growth criteria.")


# ---------------------------------------------------------------------------
# 5. Alpha
# ---------------------------------------------------------------------------

def _alpha_indicator(score):
    """Map change sub-score to indicator: ◎/○/△/×."""
    if score is None:
        return "-"
    if score >= 20:
        return "◎"
    if score >= 15:
        return "○"
    if score >= 10:
        return "△"
    return "×"


def format_alpha_markdown(results: list[dict]) -> str:
    """Format alpha signal screening results (2-axis scoring)."""
    def _pullback(r, row):
        pb = row.get("pullback_match", "none")
        return "★" if pb == "full" else "△" if pb == "partial" else "-"

    return render_screening_table(results, columns=[
        ("Rank", "---:", lambda r, row: str(r)),
        ("Symbol", ":-----", lambda r, row: _build_label(row)),
        ("Price", "-----:", _price_cell),
        ("PER", "----:", lambda r, row: _fmt_float(row.get("per"))),
        ("PBR", "----:", lambda r, row: _fmt_float(row.get("pbr"))),
        ("Value", "----:", lambda r, row: _fmt_float(row.get("value_score"))),
        ("Change", "----:", lambda r, row: _fmt_float(row.get("change_score"))),
        ("Total", "----:", lambda r, row: _fmt_float(row.get("total_score"))),
        ("Pullbk", ":------:", _pullback),
        ("Acc", ":--:", lambda r, row: _alpha_indicator(row.get("accruals_score"))),
        ("Accel", ":---:", lambda r, row: _alpha_indicator(row.get("rev_accel_score"))),
        ("FCF", ":---:", lambda r, row: _alpha_indicator(row.get("fcf_yield_score"))),
        ("ROE Trend", ":------:", lambda r, row: _alpha_indicator(row.get("roe_trend_score"))),
    ], empty_msg="No stocks met the alpha signal criteria.", legends=[
        "**Legend**: Value=Undervaluation score(100pt) / Change=Change score(100pt) / Total=Value+Change(+pullback bonus)",
        "**Change indicators**: Acc=Accruals(earnings quality) / Accel=Revenue growth acceleration / FCF=FCF yield / ROE Trend=ROE improvement trend",
        "**Rating**: ◎=Excellent(20+) ○=Good(15+) △=Average(10+) ×=Insufficient(<10)",
    ])


# ---------------------------------------------------------------------------
# 6. Shareholder Return
# ---------------------------------------------------------------------------

def format_shareholder_return_markdown(results: list[dict]) -> str:
    """Format shareholder-return screening results."""
    def _sr_label(r, row):
        name = row.get("name", row.get("symbol", "?"))
        symbol = row.get("symbol", "")
        markers = row.get("_note_markers", "")
        suffix = f" {markers}" if markers else ""
        return f"{name} ({symbol}){suffix}"

    def _pct_manual(val):
        return f"{val*100:.2f}%" if val else "-"

    def _stability(r, row):
        label = row.get("return_stability_label", "-")
        reason = row.get("return_stability_reason")
        return f"{label} ({reason})" if reason else label

    return render_screening_table(results, columns=[
        ("#", "--:", lambda r, row: str(r)),
        ("Symbol", ":-----", _sr_label),
        ("Sector", ":--------", lambda r, row: row.get("sector", "-")),
        ("PER", "----:", lambda r, row: f"{(row.get('per') or row.get('trailingPE') or 0):.1f}" if (row.get('per') or row.get('trailingPE')) else "-"),
        ("ROE", "----:", lambda r, row: f"{(row.get('roe') or row.get('returnOnEquity') or 0)*100:.1f}%" if (row.get('roe') or row.get('returnOnEquity')) else "-"),
        ("Div Yield", "----------:", lambda r, row: _pct_manual(row.get("dividend_yield_trailing") or row.get("dividend_yield"))),
        ("Buyback", "---------:", lambda r, row: _pct_manual(row.get("buyback_yield"))),
        ("Total Return", "--------:", lambda r, row: f"**{row.get('total_shareholder_return',0)*100:.2f}%**" if row.get("total_shareholder_return") else "-"),
        ("Stability", ":------", _stability),
    ], empty_msg="_No matching stocks_")


# ---------------------------------------------------------------------------
# 7. Trending
# ---------------------------------------------------------------------------

def format_trending_markdown(results: list[dict], market_context: str = "") -> str:
    """Format trending stock screening results."""
    def _cls(r, row):
        c = row.get("classification", "")
        if "Insufficient" in c:
            return "⚪Insufficient"
        if "Undervalued" in c:
            return "🟢Undervalued"
        if "Fair" in c:
            return "🟡Fair"
        return "🔴Overvalued"

    def _reason(r, row):
        reason = row.get("trending_reason") or "-"
        return reason[:37] + "..." if len(reason) > 40 else reason

    prefix = ""
    if market_context:
        prefix = f"> **X Market Sentiment**: {market_context}\n\n"

    table = render_screening_table(results, columns=[
        ("Rank", "---:", lambda r, row: str(r)),
        ("Symbol", ":-----", lambda r, row: _build_label(row)),
        ("Trending Reason", ":---------", _reason),
        ("Price", "-----:", _price_cell),
        ("PER", "----:", lambda r, row: _fmt_float(row.get("per"))),
        ("PBR", "----:", lambda r, row: _fmt_float(row.get("pbr"))),
        ("Div Yield", "---------:", lambda r, row: _fmt_pct(row.get("dividend_yield"))),
        ("ROE", "----:", lambda r, row: _fmt_pct(row.get("roe"))),
        ("Score", "------:", lambda r, row: _fmt_float(row.get("value_score"))),
        ("Judgment", ":----:", _cls),
    ], empty_msg="No stocks trending on X were found.", legends=[
        "**Judgment criteria**: 🟢Undervalued(score 60+) / 🟡Fair(score 30-59) / 🔴Overvalued(score <30) / ⚪Insufficient(data unavailable)",
        "**Data source**: X (Twitter) trends → Yahoo Finance fundamentals",
    ])
    return prefix + table if prefix else table


# ---------------------------------------------------------------------------
# 8. Contrarian
# ---------------------------------------------------------------------------

_GRADE_ICON = {"A": "\U0001f7e2", "B": "\U0001f7e1", "C": "\u26aa", "D": "\U0001f534"}


def format_contrarian_markdown(results: list[dict]) -> str:
    """Format contrarian screening results (3-axis scoring)."""
    def _grade(r, row):
        g = row.get("contrarian_grade", "-")
        return f"{_GRADE_ICON.get(g, '')}{g}"

    return render_screening_table(results, columns=[
        ("Rank", "---:", lambda r, row: str(r)),
        ("Symbol", ":-----", lambda r, row: _build_label(row)),
        ("Price", "-----:", _price_cell),
        ("PER", "----:", lambda r, row: _fmt_float(row.get("per"))),
        ("PBR", "----:", lambda r, row: _fmt_float(row.get("pbr"))),
        ("RSI", "----:", lambda r, row: _fmt_float(row.get("rsi"), decimals=1)),
        ("SMA200 Dev", "---------:", lambda r, row: _fmt_pct(row.get("sma200_deviation"))),
        ("Tech", "----:", lambda r, row: _fmt_float(row.get("tech_score"), decimals=0)),
        ("Value", "-----:", lambda r, row: _fmt_float(row.get("val_score"), decimals=0)),
        ("Fund", "------:", lambda r, row: _fmt_float(row.get("fund_score"), decimals=0)),
        ("Total", "----:", lambda r, row: _fmt_float(row.get("contrarian_score"), decimals=0)),
        ("Grade", ":----:", _grade),
    ], empty_msg="No stocks met the contrarian criteria.", legends=[
        "**Legend**: Tech=Technical contrarian(40pt) / Value=Valuation contrarian(30pt) / Fund=Fundamental divergence(30pt)",
        "**Grade**: \U0001f7e2A(70+)=Strong contrarian / \U0001f7e1B(50+)=Contrarian signal / \u26aaC(30+)=Weak / \U0001f534D(<30)=None",
    ])


# ---------------------------------------------------------------------------
# 9. Momentum
# ---------------------------------------------------------------------------

_SURGE_ICONS = {"accelerating": "\U0001f7e2", "surging": "\U0001f7e1", "overheated": "\U0001f534", "none": "\u26aa"}
_SURGE_LABELS = {"accelerating": "Accel", "surging": "Surging", "overheated": "Overheated", "none": "-"}


def format_momentum_markdown(results: list[dict]) -> str:
    """Format momentum/surge screening results."""
    def _level(r, row):
        lv = row.get("surge_level", "none")
        return f"{_SURGE_ICONS.get(lv, '')}{_SURGE_LABELS.get(lv, '-')}"

    return render_screening_table(results, columns=[
        ("Rank", "---:", lambda r, row: str(r)),
        ("Symbol", ":-----", lambda r, row: _build_label(row)),
        ("Price", "-----:", _price_cell),
        ("50MA Dev", "-------:", lambda r, row: _fmt_pct(row.get("ma50_deviation"))),
        ("Vol Ratio", "-------:", lambda r, row: _fmt_float(row.get("volume_ratio"), decimals=2)),
        ("RSI", "----:", lambda r, row: _fmt_float(row.get("rsi"), decimals=1)),
        ("52w High%", "--------:", lambda r, row: _fmt_pct(row.get("high_change_pct"))),
        ("Score", "------:", lambda r, row: _fmt_float(row.get("surge_score"), decimals=0)),
        ("Level", ":------:", _level),
    ], empty_msg="No stocks met the momentum criteria.", legends=[
        "**Level**: \U0001f7e2Accel(+10~15%)=Good entry / \U0001f7e1Surging(+15~30%)=Momentum continues / \U0001f534Overheated(+30%+)=\u26a0\ufe0f Watch for profit-taking",
    ])


# ---------------------------------------------------------------------------
# Auto-theme header (not a table formatter)
# ---------------------------------------------------------------------------

def format_auto_theme_header(themes: list[dict], skipped: list[dict] | None = None) -> str:
    """Format Grok trending themes header (KIK-440)."""
    from datetime import date
    lines = [f"\U0001f525 Grok-detected Trending Themes ({date.today().isoformat()})\n"]
    for i, t in enumerate(themes, 1):
        conf_pct = int(t.get("confidence", 0) * 100)
        lines.append(f"{i}. **{t['theme']}** (confidence: {conf_pct}%)")
        if t.get("reason"):
            lines.append(f"   {t['reason']}")
        lines.append("")
    if skipped:
        lines.append(f"\u203b Unsupported themes (skipped): {', '.join(t['theme'] for t in skipped)}\n")
    lines.append("---\n")
    return "\n".join(lines)
