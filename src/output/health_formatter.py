"""Health check output formatter (KIK-447, split from portfolio_formatter.py)."""

from src.output._format_helpers import fmt_pct_sign as _fmt_pct_sign
from src.output._format_helpers import fmt_float as _fmt_float


def _render_stock_table(lines: list[str], positions: list[dict]) -> None:
    """Render the stock health check table (individual stocks)."""
    lines.append(
        "| Symbol | P&L | Trend "
        "| Change Quality | Alert "
        "| LT Suitability | Return Stability | Contrarian |"
    )
    lines.append("|:-----|-----:|:-------|:--------|:------------|:--------|:--------|:-------|")

    for pos in positions:
        symbol = pos.get("symbol", "-")
        if pos.get("is_small_cap"):
            symbol += " [small]"
        pnl_pct = pos.get("pnl_pct", 0)
        pnl_str = _fmt_pct_sign(pnl_pct) if pnl_pct is not None else "-"

        trend = pos.get("trend_health", {}).get("trend", "Unknown")
        quality = pos.get("change_quality", {}).get("quality_label", "-")
        alert = pos.get("alert", {})
        alert_emoji = alert.get("emoji", "")
        alert_label = alert.get("label", "None")

        if alert_emoji:
            alert_str = f"{alert_emoji} {alert_label}"
        else:
            alert_str = "None"

        # Value trap indicator (KIK-381)
        vt = pos.get("value_trap", {})
        if vt.get("is_trap"):
            alert_str += " \U0001fa64"

        # Long-term suitability (KIK-371)
        lt = pos.get("long_term", {})
        lt_label = lt.get("label", "-")

        # Return stability (KIK-403)
        rs = pos.get("return_stability", {})
        rs_label = rs.get("label", "-") if rs else "-"

        # Contrarian indicator (KIK-504)
        ct = pos.get("contrarian")
        if ct and ct.get("contrarian_score", 0) > 0:
            ct_grade = ct.get("grade", "-")
            ct_score = ct["contrarian_score"]
            ct_str = f"{ct_grade}{ct_score:.0f}"
        else:
            ct_str = "-"

        lines.append(
            f"| {symbol} | {pnl_str} | {trend} | {quality} "
            f"| {alert_str} | {lt_label} | {rs_label} | {ct_str} |"
        )

    lines.append("")


def _render_etf_table(lines: list[str], positions: list[dict]) -> None:
    """Render the ETF health check table (KIK-469 Phase 2)."""
    lines.append(
        "| Symbol | P&L | Trend "
        "| Expense Ratio | AUM | ETF Score | Alert |"
    )
    lines.append("|:-----|-----:|:-------|:--------|:------|----------:|:--------|")

    for pos in positions:
        symbol = pos.get("symbol", "-")
        pnl_pct = pos.get("pnl_pct", 0)
        pnl_str = _fmt_pct_sign(pnl_pct) if pnl_pct is not None else "-"
        trend = pos.get("trend_health", {}).get("trend", "Unknown")

        change_q = pos.get("change_quality", {})
        etf_health = change_q.get("etf_health") or pos.get("long_term", {}).get("etf_health")
        if etf_health:
            expense = etf_health.get("expense_label", "-")
            aum = etf_health.get("aum_label", "-")
            score = etf_health.get("score", "-")
            score_str = f"{score}/100" if isinstance(score, (int, float)) else "-"
        else:
            expense = "-"
            aum = "-"
            score_str = "-"

        alert = pos.get("alert", {})
        alert_emoji = alert.get("emoji", "")
        alert_label = alert.get("label", "None")
        alert_str = f"{alert_emoji} {alert_label}" if alert_emoji else "None"

        lines.append(
            f"| {symbol} | {pnl_str} | {trend} | {expense} "
            f"| {aum} | {score_str} | {alert_str} |"
        )

    lines.append("")


def format_health_check(health_data: dict) -> str:
    """Format portfolio health check results as a Markdown report.

    Parameters
    ----------
    health_data : dict
        Output from health_check.run_health_check().

    Returns
    -------
    str
        Markdown-formatted health check report.
    """
    lines: list[str] = []

    positions = health_data.get("positions", [])
    alerts = health_data.get("alerts", [])
    summary = health_data.get("summary", {})

    if not positions:
        lines.append("## Portfolio Health Check")
        lines.append("")
        lines.append("No holdings found.")
        return "\n".join(lines)

    # --- Compact summary (KIK-442) ---
    total = len(positions)
    exit_syms = [p["symbol"] for p in positions if p.get("alert", {}).get("level") == "exit"]
    caution_syms = [p["symbol"] for p in positions if p.get("alert", {}).get("level") == "caution"]
    early_syms = [p["symbol"] for p in positions if p.get("alert", {}).get("level") == "early_warning"]
    healthy_count = sum(1 for p in positions if p.get("alert", {}).get("level", "none") == "none")

    def _syms_str(syms: list, max_shown: int = 5) -> str:
        if not syms:
            return ""
        shown = syms[:max_shown]
        suffix = " ..." if len(syms) > max_shown else ""
        return "  → " + ", ".join(shown) + suffix

    lines.append("## 📊 Health Check Summary (" + str(total) + " stocks)")
    lines.append("")
    lines.append(f"🔴 Exit candidates: {len(exit_syms)}{_syms_str(exit_syms)}")
    lines.append(f"⚠️  Caution:         {len(caution_syms)}{_syms_str(caution_syms)}")
    lines.append(f"⏰ Early warning:   {len(early_syms)}{_syms_str(early_syms)}")
    lines.append(f"✅ Healthy:         {healthy_count}")
    lines.append("")
    lines.append("─── Details ────────────────────────────────")
    lines.append("")

    # KIK-469 Phase 2: Split tables by stock/ETF
    stock_positions = health_data.get("stock_positions")
    etf_positions = health_data.get("etf_positions")

    if stock_positions is None:
        # Backward compat: old format without partition keys
        lines.append("## Portfolio Health Check")
        lines.append("")
        _render_stock_table(lines, positions)
    else:
        has_both = bool(stock_positions) and bool(etf_positions)
        if stock_positions:
            if has_both:
                lines.append("## Individual Stock Health Check")
                lines.append("")
            else:
                lines.append("## Portfolio Health Check")
                lines.append("")
            _render_stock_table(lines, stock_positions)
        if etf_positions:
            if has_both:
                lines.append("## ETF Health Check")
                lines.append("")
            else:
                lines.append("## Portfolio Health Check")
                lines.append("")
            _render_etf_table(lines, etf_positions)

    # Summary counts
    total = summary.get("total", 0)
    healthy = summary.get("healthy", 0)
    early = summary.get("early_warning", 0)
    caution = summary.get("caution", 0)
    exit_count = summary.get("exit", 0)
    lines.append(
        f"**{total} stocks**: "
        f"Healthy {healthy} / "
        f"⚡Early warning {early} / "
        f"⚠Caution {caution} / "
        f"🚨Exit {exit_count}"
    )
    lines.append("")

    # Small-cap allocation (KIK-438)
    small_cap_alloc = health_data.get("small_cap_allocation")
    if small_cap_alloc:
        level = small_cap_alloc["level"]
        emoji = {"ok": "✅", "warning": "⚠️", "critical": "🔴"}[level]
        lines.append(f"{emoji} {small_cap_alloc['message']}")
        lines.append("")

    # Community concentration (KIK-549)
    community_conc = health_data.get("community_concentration")
    if community_conc and community_conc.get("warnings"):
        for w in community_conc["warnings"]:
            pct = int(w["weight"] * 100)
            members_str = ", ".join(w["members"])
            lines.append(
                f"⚠️ Community concentration: {w['community']} has"
                f" {w['count']} stocks ({pct}%) — {w['message']}"
            )
            lines.append(f"  Members: {members_str}")
        lines.append("")

    # Theme exposure analysis (KIK-604)
    theme_exposure = health_data.get("theme_exposure")
    if theme_exposure:
        pf_themes = theme_exposure.get("pf_themes", {})
        gap = theme_exposure.get("gap", [])

        if pf_themes or gap:
            lines.append("## 📊 Theme Composition Analysis")
            lines.append("")

        if pf_themes:
            lines.append("### Portfolio Theme Composition")
            lines.append("| Theme | Count | Weight | Symbols |")
            lines.append("|:---|:---|:---|:---|")
            for theme_name, data in pf_themes.items():
                count = len(data["symbols"])
                weight_pct = f"{data['weight'] * 100:.1f}%"
                syms = ", ".join(data["symbols"])
                lines.append(f"| {theme_name} | {count} | {weight_pct} | {syms} |")
            lines.append("")

        if gap:
            lines.append("### Theme Gaps (Trending Themes \u00d7 Not in Portfolio)")
            for g in gap:
                theme = g["theme"]
                stock_count = g.get("stock_count", 0)
                lines.append(
                    f"- {theme}: {stock_count} related stocks -- not in portfolio"
                )
            lines.append("")

    # Exit-rule threshold alerts (KIK-566)
    all_positions = health_data.get("positions", [])
    exit_rule_alerts = [p for p in all_positions if p.get("exit_rule_hit")]
    if exit_rule_alerts:
        for p in exit_rule_alerts:
            sym = p.get("symbol", "?")
            hit = p["exit_rule_hit"]
            if hit["type"] == "stop_loss":
                emoji = "\U0001f534"  # red circle
                label = "Stop-loss reached"
            else:
                emoji = "\U0001f7e2"  # green circle
                label = "Take-profit reached"
            pnl = p.get("pnl_pct", 0)
            lines.append(
                f"{emoji} {sym}: {label} ({hit['threshold']}, current {pnl:+.1f}%)"
            )
            if hit.get("reason"):
                lines.append(f"  Reason: {hit['reason']}")
        lines.append("")

    # Alert details
    if alerts:
        lines.append("## Alert Details")
        lines.append("")

        for pos in alerts:
            symbol = pos.get("symbol", "-")
            alert = pos.get("alert", {})
            emoji = alert.get("emoji", "")
            label = alert.get("label", "")
            reasons = alert.get("reasons", [])
            trend_h = pos.get("trend_health", {})
            change_q = pos.get("change_quality", {})
            change_score = change_q.get("change_score", 0)

            lines.append(f"### {emoji} {symbol} ({label})")
            lines.append("")

            for reason in reasons:
                lines.append(f"- {reason}")

            # Additional context
            trend = trend_h.get("trend", "Unknown")
            rsi = trend_h.get("rsi", float("nan"))
            sma50 = trend_h.get("sma50", float("nan"))
            sma200 = trend_h.get("sma200", float("nan"))
            quality_label = change_q.get("quality_label", "-")

            lines.append(
                f"- Trend: {trend}"
                f" (SMA50={_fmt_float(sma50)}, "
                f"SMA200={_fmt_float(sma200)}, "
                f"RSI={_fmt_float(rsi)})"
            )

            # ETF-specific context (KIK-469)
            etf_h = change_q.get("etf_health")
            if change_q.get("is_etf") and etf_h:
                lines.append(f"- ETF: {etf_h.get('fund_category', '-')} / {etf_h.get('fund_family', '-')}")
                lines.append(f"- Expense ratio: {etf_h.get('expense_label', '-')} / AUM: {etf_h.get('aum_label', '-')}")
                for etf_alert in etf_h.get("alerts", []):
                    lines.append(f"- {etf_alert}")
            else:
                lines.append(
                    f"- Change quality: {quality_label}"
                    f" (change score {change_score:.0f}/100)"
                )

            # Long-term suitability context (KIK-371)
            lt = pos.get("long_term", {})
            lt_label = lt.get("label", "-")
            lt_summary = lt.get("summary", "")
            if lt_label not in ("N/A", "-"):
                lines.append(
                    f"- Long-term suitability: {lt_label}"
                    f" ({lt_summary})"
                )

            # Value trap warning (KIK-381)
            vt = pos.get("value_trap")
            if vt and vt.get("is_trap"):
                lines.append(
                    f"- \U0001fa64 **Value trap signs**: "
                    f"{', '.join(vt['reasons'])}"
                )

            # Shareholder return stability context (KIK-403)
            rs = pos.get("return_stability")
            if rs:
                stability = rs.get("stability")
                latest_pct = (rs.get("latest_rate") or 0) * 100
                avg_pct = (rs.get("avg_rate") or 0) * 100
                if stability == "temporary":
                    lines.append(
                        f"- ⚠️ **Temporarily high returns**: "
                        f"{rs.get('reason', '')}"
                        f" (latest {latest_pct:.1f}%, "
                        f"avg {avg_pct:.1f}%)"
                    )
                elif stability == "decreasing":
                    lines.append(
                        f"- 📉 **Shareholder return declining**: "
                        f"{rs.get('reason', '')}"
                    )
                elif stability in ("stable", "increasing"):
                    lines.append(
                        f"- {rs.get('label', '')} "
                        f"(latest {latest_pct:.1f}%)"
                    )
                elif stability and stability.startswith("single_"):
                    lines.append(
                        f"- {rs.get('label', '')} "
                        f"({rs.get('reason', '')})"
                    )

            # Contrarian signal for alerted stocks (KIK-504, KIK-533)
            ct = pos.get("contrarian")
            if ct and ct.get("contrarian_score", 0) > 0:
                ct_score = ct["contrarian_score"]
                ct_grade = ct.get("grade", "-")
                ct_tech = ct.get("technical", {}).get("score", 0)
                ct_val = ct.get("valuation", {}).get("score", 0)
                ct_fund = ct.get("fundamental", {}).get("score", 0)
                lines.append(
                    f"- Contrarian score: {ct_score:.0f}/100 (grade {ct_grade}) "
                    f"[Tech {ct_tech:.0f} Value {ct_val:.0f} Fund {ct_fund:.0f}]"
                )
                if ct_grade in ("A", "B"):
                    lines.append(
                        "  → **Contrarian buy candidate**: "
                        "Potentially undervalued and technically oversold"
                    )
                elif ct_grade == "C":
                    lines.append(
                        "  → Weak contrarian signal: "
                        "Some conditions are met"
                    )

            # Action suggestion based on alert level
            level = alert.get("level", "none")
            if level == "early_warning":
                lines.append(
                    "→ Possible temporary pullback. Increase monitoring"
                )
            elif level == "caution":
                lines.append(
                    "→ Consider reducing position"
                )
            elif level == "exit":
                lines.append(
                    "→ Investment thesis has collapsed. Consider exiting"
                )

            lines.append("")

    return "\n".join(lines)
