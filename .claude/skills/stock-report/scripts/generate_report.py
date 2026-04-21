#!/usr/bin/env python3
"""Entry point for the stock-report skill."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from scripts.common import try_import, HAS_HISTORY_STORE, HAS_GRAPH_QUERY as _HAS_GQ, HAS_GRAPH_STORE as _HAS_GS, print_context, print_suggestions
from src.data.yahoo_client import get_stock_info, get_stock_detail
from src.core.screening.indicators import calculate_value_score
from src.core.common import is_etf

HAS_SHAREHOLDER_RETURN, _sr = try_import("src.core.screening.indicators", "calculate_shareholder_return")
if HAS_SHAREHOLDER_RETURN: calculate_shareholder_return = _sr["calculate_shareholder_return"]

HAS_SHAREHOLDER_HISTORY, _sh = try_import("src.core.screening.indicators", "calculate_shareholder_return_history")
if HAS_SHAREHOLDER_HISTORY: calculate_shareholder_return_history = _sh["calculate_shareholder_return_history"]

HAS_RETURN_STABILITY, _rs = try_import("src.core.screening.indicators", "assess_return_stability")
if HAS_RETURN_STABILITY: assess_return_stability = _rs["assess_return_stability"]

# Module availability from common.py (KIK-448)
HAS_HISTORY = HAS_HISTORY_STORE
if HAS_HISTORY:
    from src.data.history import save_report as history_save_report

HAS_VALUE_TRAP, _vt = try_import("src.core.health_check", "_detect_value_trap")
if HAS_VALUE_TRAP: _detect_value_trap = _vt["_detect_value_trap"]

HAS_CONTRARIAN, _ct = try_import("src.core.screening.contrarian", "compute_contrarian_score")
if HAS_CONTRARIAN: compute_contrarian_score = _ct["compute_contrarian_score"]

HAS_GRAPH_QUERY = _HAS_GQ
if HAS_GRAPH_QUERY:
    from src.data.graph_query import get_prior_report

HAS_INDUSTRY_CONTEXT = _HAS_GQ
if HAS_INDUSTRY_CONTEXT:
    from src.data.graph_query import get_industry_research_for_sector

# KIK-487: Theme auto-tagging from industry
HAS_GRAPH_STORE = _HAS_GS
if HAS_GRAPH_STORE:
    from src.data.graph_store import tag_theme

HAS_THEME_LOOKUP, _tl = try_import("src.core.screening.query_builder", "infer_themes")
if HAS_THEME_LOOKUP:
    _infer_themes = _tl["infer_themes"]
else:
    def _infer_themes(industry: str) -> list[str]:
        return []


def _print_etf_report(symbol: str, data: dict):
    """Print an ETF-specific report (KIK-469)."""
    def fmt(val, pct=False):
        if val is None:
            return "-"
        return f"{val * 100:.2f}%" if pct else f"{val:.4f}"

    def fmt_int(val):
        if val is None:
            return "-"
        return f"{val:,.0f}"

    print(f"# {data.get('name', symbol)} ({symbol}) [ETF]")
    print()

    # Fund overview
    print("## Fund Overview")
    print("| Item | Value |")
    print("|---:|:---|")
    print(f"| Category | {data.get('fund_category') or '-'} |")
    print(f"| Fund Family | {data.get('fund_family') or '-'} |")
    print(f"| Total Assets (AUM) | {fmt_int(data.get('total_assets_fund'))} |")
    print(f"| Expense Ratio | {fmt(data.get('expense_ratio'), pct=True)} |")
    print()

    # Expense ratio assessment
    er = data.get("expense_ratio")
    if er is not None:
        if er <= 0.001:
            er_verdict = "Ultra-low cost (excellent)"
        elif er <= 0.005:
            er_verdict = "Low cost (good)"
        elif er <= 0.01:
            er_verdict = "Somewhat high"
        else:
            er_verdict = "High cost (review recommended)"
        print(f"- **Expense Ratio Rating**: {er_verdict}")
        print()

    # Performance
    print("## Performance")
    print("| Metric | Value |")
    print("|---:|:---|")
    print(f"| Current Price | {fmt_int(data.get('price'))} |")
    print(f"| Dividend Yield | {fmt(data.get('dividend_yield_trailing'), pct=True)} |")
    print(f"| Beta | {fmt(data.get('beta'))} |")
    print(f"| 52-Week High | {fmt_int(data.get('fifty_two_week_high'))} |")
    print(f"| 52-Week Low | {fmt_int(data.get('fifty_two_week_low'))} |")
    print()

    # AUM assessment
    aum = data.get("total_assets_fund")
    if aum is not None:
        if aum >= 10_000_000_000:
            aum_verdict = "Large (sufficient liquidity)"
        elif aum >= 1_000_000_000:
            aum_verdict = "Mid-size (good liquidity)"
        elif aum >= 100_000_000:
            aum_verdict = "Small (caution on liquidity)"
        else:
            aum_verdict = "Very small (redemption risk)"
        print(f"- **Fund Size**: {aum_verdict}")

    # Save history
    if HAS_HISTORY:
        try:
            history_save_report(symbol, data, 0, "ETF")
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_report.py <ticker>")
        print("Example: generate_report.py 7203.T")
        sys.exit(1)

    symbol = sys.argv[1]

    # Context retrieval (KIK-465)
    print_context(f"report {symbol}")

    data = get_stock_detail(symbol)
    if data is None:
        data = get_stock_info(symbol)

    if data is None:
        print(f"Error: Could not fetch data for {symbol}.")
        sys.exit(1)

    # KIK-469: ETF auto-detection
    if is_etf(data):
        _print_etf_report(symbol, data)
        print_suggestions(symbol=symbol, context_summary=f"ETF report generated: {symbol}")
        return

    thresholds = {"per_max": 15, "pbr_max": 1.0, "dividend_yield_min": 0.03, "roe_min": 0.08}
    score = calculate_value_score(data, thresholds)

    if score >= 70:
        verdict = "Undervalued (consider buying)"
    elif score >= 50:
        verdict = "Slightly undervalued"
    elif score >= 30:
        verdict = "Fair value"
    else:
        verdict = "Overvalued tendency"

    def fmt(val, pct=False):
        if val is None:
            return "-"
        return f"{val * 100:.2f}%" if pct else f"{val:.2f}"

    def fmt_int(val):
        if val is None:
            return "-"
        return f"{val:,.0f}"

    print(f"# {data.get('name', symbol)} ({symbol})")
    print()
    print(f"- **Sector**: {data.get('sector') or '-'}")
    print(f"- **Industry**: {data.get('industry') or '-'}")
    print()
    print("## Price Information")
    print(f"- **Current Price**: {fmt_int(data.get('price'))}")
    print(f"- **Market Cap**: {fmt_int(data.get('market_cap'))}")
    print()
    print("## Valuation")
    print(f"| Metric | Value |")
    print(f"|---:|:---|")
    print(f"| P/E | {fmt(data.get('per'))} |")
    print(f"| P/B | {fmt(data.get('pbr'))} |")
    print(f"| Dividend Yield (Trailing) | {fmt(data.get('dividend_yield_trailing'), pct=True)} |")
    print(f"| Dividend Yield (Forward) | {fmt(data.get('dividend_yield'), pct=True)} |")
    print(f"| ROE | {fmt(data.get('roe'), pct=True)} |")
    print(f"| ROA | {fmt(data.get('roa'), pct=True)} |")
    print(f"| Revenue Growth | {fmt(data.get('revenue_growth'), pct=True)} |")
    print()
    print("## Undervaluation Assessment")
    print(f"- **Score**: {score:.1f} / 100")
    print(f"- **Verdict**: {verdict}")

    # KIK-381: Value trap warning
    if HAS_VALUE_TRAP:
        vt = _detect_value_trap(data)
        if vt["is_trap"]:
            print()
            print("## ⚠️ Value Trap Warning")
            for reason in vt["reasons"]:
                print(f"- {reason}")

    # KIK-504: Contrarian signal section
    if HAS_CONTRARIAN:
        try:
            from src.data import yahoo_client as _yc
            _hist = _yc.get_price_history(symbol, period="1y")
        except Exception:
            _hist = None
        ct_result = compute_contrarian_score(_hist, data)
        if ct_result["contrarian_score"] > 0:
            print()
            print("## Contrarian Signal")
            _ct_grade = ct_result["grade"]
            print(f"- **Contrarian Score**: {ct_result['contrarian_score']:.0f} / 100 (Grade {_ct_grade})")
            _tech = ct_result["technical"]
            _val = ct_result["valuation"]
            _fund = ct_result["fundamental"]
            _rsi_str = f"RSI={fmt(_tech.get('rsi'))}" if _tech.get("rsi") is not None else "RSI=-"
            _sma_dev = _tech.get("sma200_deviation")
            _sma_str = f"SMA200 deviation={fmt(_sma_dev, pct=True)}" if _sma_dev is not None else "SMA200 deviation=-"
            print(f"- Technical: {_tech['score']:.0f}/40 ({_rsi_str}, {_sma_str})")
            print(f"- Valuation: {_val['score']:.0f}/30")
            print(f"- Fundamental Deviation: {_fund['score']:.0f}/30")
            if _ct_grade == "A":
                print("- **Verdict**: Strong contrarian signal (consider entry)")
            elif _ct_grade == "B":
                print("- **Verdict**: Contrarian signal detected (verify)")
            elif _ct_grade == "C":
                print("- **Verdict**: Weak contrarian signal (wait and see)")

    # KIK-375: Shareholder return section
    if HAS_SHAREHOLDER_RETURN:
        sr = calculate_shareholder_return(data)
        total_rate = sr.get("total_return_rate")
        if total_rate is not None or sr.get("dividend_yield") is not None:
            print()
            print("## Shareholder Returns")
            print("| Metric | Value |")
            print("|---:|:---|")
            print(f"| Dividend Yield | {fmt(sr.get('dividend_yield'), pct=True)} |")
            print(f"| Buyback Yield | {fmt(sr.get('buyback_yield'), pct=True)} |")
            print(f"| **Total Return Rate** | **{fmt(total_rate, pct=True)}** |")
            dp = sr.get("dividend_paid")
            br = sr.get("stock_repurchase")
            ta = sr.get("total_return_amount")
            if dp is not None or br is not None:
                print()
                print(f"- Total Dividends: {fmt_int(dp)}")
                print(f"- Buyback Amount: {fmt_int(br)}")
                print(f"- Total Shareholder Returns: {fmt_int(ta)}")

    # KIK-380: Shareholder return 3-year history
    if HAS_SHAREHOLDER_HISTORY:
        sr_hist = calculate_shareholder_return_history(data)
        if len(sr_hist) >= 2:
            print()
            print("## Shareholder Return History")
            header_cols = []
            for entry in sr_hist:
                fy = entry.get("fiscal_year")
                header_cols.append(str(fy) if fy else "-")
            print("| Metric | " + " | ".join(header_cols) + " |")
            print("|---:" + " | :---" * len(sr_hist) + " |")
            print("| Total Dividends | " + " | ".join(
                fmt_int(e.get("dividend_paid")) for e in sr_hist
            ) + " |")
            print("| Buyback Amount | " + " | ".join(
                fmt_int(e.get("stock_repurchase")) for e in sr_hist
            ) + " |")
            print("| Total Returns | " + " | ".join(
                fmt_int(e.get("total_return_amount")) for e in sr_hist
            ) + " |")
            print("| Total Return Rate | " + " | ".join(
                fmt(e.get("total_return_rate"), pct=True) for e in sr_hist
            ) + " |")
            # Trend judgment
            rates = [e.get("total_return_rate") for e in sr_hist
                     if e.get("total_return_rate") is not None]
            if len(rates) >= 2:
                if all(rates[i] >= rates[i + 1] for i in range(len(rates) - 1)):
                    trend = "📈 Increasing trend (active shareholder returns)"
                elif all(rates[i] <= rates[i + 1] for i in range(len(rates) - 1)):
                    trend = "📉 Decreasing trend (caution)"
                else:
                    trend = "➡️ Flat"
                print()
                print(f"- **Trend**: {trend}")

                # KIK-383: Return stability assessment
                if HAS_RETURN_STABILITY:
                    stability = assess_return_stability(sr_hist)
                    stab_label = stability.get("label", "")
                    avg_rate = stability.get("avg_rate")
                    if avg_rate is not None:
                        print(f"- **Stability**: {stab_label} (3-year avg: {avg_rate*100:.2f}%)")
                    else:
                        print(f"- **Stability**: {stab_label}")
        elif len(sr_hist) == 1 and HAS_RETURN_STABILITY:
            stability = assess_return_stability(sr_hist)
            stab_label = stability.get("label", "")
            if stab_label and stab_label != "-":
                print()
                print("## Shareholder Return Stability")
                entry = sr_hist[0]
                rate = entry.get("total_return_rate")
                if rate is not None:
                    fy = entry.get("fiscal_year")
                    fy_str = f"{fy}: " if fy else ""
                    print(f"- {fy_str}Total return rate {rate*100:.2f}%")
                print(f"- **Stability**: {stab_label}")

    # KIK-433: Industry context from Neo4j (same-sector research)
    _sector = data.get("sector") or ""
    if HAS_INDUSTRY_CONTEXT and _sector:
        try:
            industry_ctx = get_industry_research_for_sector(_sector, days=30)
        except Exception:
            industry_ctx = []
        if industry_ctx:
            print()
            print("## Industry Context (Same-Sector Recent Research)")
            for ctx in industry_ctx[:3]:
                target = ctx.get("target", "")
                date_str = ctx.get("date", "")
                summary = ctx.get("summary", "")
                cats = ctx.get("catalysts", [])
                growth = [c["text"] for c in cats if c.get("type") == "growth_driver"]
                risks  = [c["text"] for c in cats if c.get("type") == "risk"]
                print(f"\n### {target} ({date_str})")
                if summary:
                    print(summary[:200])
                if growth:
                    print("**Tailwinds:** " + ", ".join(growth[:3]))
                if risks:
                    print("**Risks:** " + ", ".join(risks[:3]))

    # KIK-406: Prior report comparison
    if HAS_GRAPH_QUERY:
        try:
            prior = get_prior_report(symbol)
            if prior and prior.get("score") is not None:
                diff = score - prior["score"]
                print()
                print("## Comparison with Previous Report")
                print(f"- Previous: {prior['date']} / Score {prior['score']:.1f} / {prior.get('verdict', '-')}")
                print(f"- Current: Score {score:.1f} / {verdict}")
                print(f"- Change: {diff:+.1f}pt")
        except Exception:
            pass

    if HAS_HISTORY:
        try:
            history_save_report(symbol, data, score, verdict)
        except Exception as e:
            print(f"Warning: Failed to save history: {e}", file=sys.stderr)

    # KIK-487: Auto-tag themes based on industry
    if HAS_GRAPH_STORE:
        _industry = data.get("industry") or ""
        for _theme_key in _infer_themes(_industry):
            try:
                tag_theme(symbol, _theme_key)
            except Exception:
                pass

    # Proactive suggestions (KIK-465)
    print_suggestions(symbol=symbol, context_summary=f"Report generated: {symbol}")


if __name__ == "__main__":
    main()
