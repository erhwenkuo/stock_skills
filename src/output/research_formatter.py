"""Output formatters for deep research results (KIK-367)."""

from typing import Optional

from src.output._format_helpers import fmt_pct as _fmt_pct
from src.output._format_helpers import fmt_float as _fmt_float


# ---------------------------------------------------------------------------
# API status summary (KIK-431)
# ---------------------------------------------------------------------------

_STATUS_ICON = {
    "ok": "✅",
    "not_configured": "🔑",
    "auth_error": "❌",
    "rate_limited": "⚠️",
    "timeout": "⏱️",
    "other_error": "❌",
}

_STATUS_MSG = {
    "ok": "OK",
    "not_configured": "Not configured — set XAI_API_KEY to enable",
    "auth_error": "Auth error (401) — check your XAI_API_KEY",
    "rate_limited": "Rate limited (429) — retry after a while",
    "timeout": "Timeout — check network connection",
    "other_error": "Error — see stderr for details",
}


def _format_api_status(api_status: Optional[dict]) -> str:
    """Format API status summary section (KIK-431).

    Parameters
    ----------
    api_status : dict | None
        ``{"grok": {"status": ..., "status_code": ..., "message": ...}}``
        from researcher functions.  Returns empty string when None.
    """
    if not api_status:
        return ""
    grok = api_status.get("grok", {})
    if not isinstance(grok, dict):
        return ""
    status = grok.get("status", "ok")
    icon = _STATUS_ICON.get(status, "❓")
    msg = _STATUS_MSG.get(status, status)
    lines = [
        "---",
        "",
        "## API Status",
        "| API | Status |",
        "|:----|:-----|",
        f"| Grok (xAI) | {icon} {msg} |",
        "",
    ]
    return "\n".join(lines)


def _fmt_int(value) -> str:
    """Format a value as a comma-separated integer, or '-' if None."""
    if value is None:
        return "-"
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "-"


def _sentiment_label(score: float) -> str:
    """Convert a sentiment score (-1 to 1) to a label."""
    if score >= 0.3:
        return "Bullish"
    if score >= 0.1:
        return "Slightly bullish"
    if score >= -0.1:
        return "Neutral"
    if score >= -0.3:
        return "Slightly bearish"
    return "Bearish"


def _fmt_market_cap(value: Optional[float]) -> str:
    """Format market cap with appropriate unit."""
    if value is None:
        return "-"
    if value >= 1e12:
        return f"{value / 1e12:.2f}T"
    if value >= 1e9:
        return f"{value / 1e9:.1f}B"
    if value >= 1e6:
        return f"{value / 1e6:.1f}M"
    return _fmt_int(value)


# ---------------------------------------------------------------------------
# format_stock_research
# ---------------------------------------------------------------------------

def format_stock_research(data: dict) -> str:
    """Format stock research as a Markdown report.

    Parameters
    ----------
    data : dict
        Output from researcher.research_stock().

    Returns
    -------
    str
        Markdown-formatted report.
    """
    if not data:
        return "No research data available."

    symbol = data.get("symbol", "-")
    name = data.get("name") or ""
    title = f"{name} ({symbol})" if name else symbol

    lines: list[str] = []
    lines.append(f"# {title} \u2014 Deep Research")
    lines.append("")

    fundamentals = data.get("fundamentals", {})

    # --- Basic info table ---
    lines.append("## Basic Information")
    lines.append("| Item | Value |")
    lines.append("|:-----|:---|")
    lines.append(f"| Sector | {fundamentals.get('sector') or '-'} |")
    lines.append(f"| Industry | {fundamentals.get('industry') or '-'} |")
    lines.append(f"| Price | {_fmt_float(fundamentals.get('price'), 0)} |")
    lines.append(f"| Market Cap | {_fmt_market_cap(fundamentals.get('market_cap'))} |")
    lines.append("")

    # --- Valuation table ---
    lines.append("## Valuation")
    lines.append("| Metric | Value |")
    lines.append("|:-----|---:|")
    lines.append(f"| PER | {_fmt_float(fundamentals.get('per'))} |")
    lines.append(f"| PBR | {_fmt_float(fundamentals.get('pbr'))} |")
    lines.append(f"| Div Yield | {_fmt_pct(fundamentals.get('dividend_yield'))} |")
    lines.append(f"| ROE | {_fmt_pct(fundamentals.get('roe'))} |")

    value_score = data.get("value_score")
    score_str = _fmt_float(value_score) if value_score is not None else "-"
    lines.append(f"| Value Score | {score_str}/100 |")
    lines.append("")

    # --- News ---
    news = data.get("news", [])
    lines.append("## Latest News")
    if news:
        for item in news[:10]:
            title_text = item.get("title", "")
            publisher = item.get("publisher", "")
            pub_date = item.get("providerPublishTime") or item.get("date", "")
            suffix_parts = []
            if publisher:
                suffix_parts.append(publisher)
            if pub_date:
                suffix_parts.append(str(pub_date))
            suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
            if title_text:
                lines.append(f"- {title_text}{suffix}")
    else:
        lines.append("No news available.")
    lines.append("")

    # --- X Sentiment ---
    x_sentiment = data.get("x_sentiment", {})
    _has_sentiment = (
        x_sentiment.get("positive")
        or x_sentiment.get("negative")
        or x_sentiment.get("raw_response")
    )

    lines.append("## X (Twitter) Sentiment")

    if _has_sentiment:
        score = x_sentiment.get("sentiment_score", 0.0)
        label = _sentiment_label(score)
        lines.append(f"**Judgment: {label}** (score: {_fmt_float(score)})")
        lines.append("")

        positive = x_sentiment.get("positive", [])
        if positive:
            lines.append("### Positive Factors")
            for p in positive:
                lines.append(f"- {p}")
            lines.append("")

        negative = x_sentiment.get("negative", [])
        if negative:
            lines.append("### Negative Factors")
            for n in negative:
                lines.append(f"- {n}")
            lines.append("")
    else:
        lines.append(
            "*Grok API (XAI_API_KEY) is not configured \u2014 X sentiment analysis unavailable.*"
        )
        lines.append("")

    # --- Deep research (Grok API) ---
    grok = data.get("grok_research", {})
    _has_grok = (
        grok.get("recent_news")
        or grok.get("catalysts", {}).get("positive")
        or grok.get("catalysts", {}).get("negative")
        or grok.get("analyst_views")
        or grok.get("competitive_notes")
        or grok.get("raw_response")
    )

    if _has_grok:
        lines.append("## Deep Research (Grok API)")
        lines.append("")

        # Recent news
        recent_news = grok.get("recent_news", [])
        if recent_news:
            lines.append("### Recent Key News")
            for item in recent_news:
                lines.append(f"- {item}")
            lines.append("")

        # Catalysts
        catalysts = grok.get("catalysts", {})
        positive_catalysts = catalysts.get("positive", [])
        negative_catalysts = catalysts.get("negative", [])
        if positive_catalysts or negative_catalysts:
            lines.append("### Earnings Catalysts")
            if positive_catalysts:
                lines.append("**Positive:**")
                for c in positive_catalysts:
                    lines.append(f"- {c}")
                lines.append("")
            if negative_catalysts:
                lines.append("**Negative:**")
                for c in negative_catalysts:
                    lines.append(f"- {c}")
                lines.append("")

        # Analyst views
        analyst_views = grok.get("analyst_views", [])
        if analyst_views:
            lines.append("### Analyst & Institutional Views")
            for v in analyst_views:
                lines.append(f"- {v}")
            lines.append("")

        # Competitive notes
        competitive = grok.get("competitive_notes", [])
        if competitive:
            lines.append("### Competitive Highlights")
            for c in competitive:
                lines.append(f"- {c}")
            lines.append("")
    else:
        lines.append("## Deep Research")
        lines.append(
            "*Grok API (XAI_API_KEY) is not configured \u2014 Web/X search research unavailable.*"
        )
        lines.append(
            "*Set the XAI_API_KEY environment variable to enable deep analysis via X posts and web search.*"
        )
        lines.append("")

    # API status summary (KIK-431)
    status_section = _format_api_status(data.get("api_status"))
    if status_section:
        lines.append(status_section)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# format_industry_research
# ---------------------------------------------------------------------------

def format_industry_research(data: dict) -> str:
    """Format industry research as a Markdown report.

    Parameters
    ----------
    data : dict
        Output from researcher.research_industry().

    Returns
    -------
    str
        Markdown-formatted report.
    """
    if not data:
        return "No research data available."

    theme = data.get("theme", "-")

    if data.get("api_unavailable"):
        lines: list[str] = []
        lines.append(f"# {theme} - Industry Research")
        lines.append("")
        lines.append(
            "*Industry research requires the Grok API. "
            "Please set the XAI_API_KEY environment variable.*"
        )
        lines.append("")
        status_section = _format_api_status(data.get("api_status"))
        if status_section:
            lines.append(status_section)
        return "\n".join(lines)

    grok = data.get("grok_research", {})
    lines: list[str] = []
    lines.append(f"# {theme} - Industry Research")
    lines.append("")

    # Trends
    trends = grok.get("trends", [])
    lines.append("## Trends")
    if trends:
        for t in trends:
            lines.append(f"- {t}")
    else:
        lines.append("No information")
    lines.append("")

    # Key players
    key_players = grok.get("key_players", [])
    lines.append("## Key Players")
    if key_players:
        lines.append("| Company | Ticker | Note |")
        lines.append("|:-----|:----------|:---------|")
        for p in key_players:
            if isinstance(p, dict):
                name = p.get("name", "-")
                ticker = p.get("ticker", "-")
                note = p.get("note", "-")
                lines.append(f"| {name} | {ticker} | {note} |")
            else:
                lines.append(f"| {p} | - | - |")
    else:
        lines.append("No information")
    lines.append("")

    # Growth drivers
    drivers = grok.get("growth_drivers", [])
    lines.append("## Growth Drivers")
    if drivers:
        for d in drivers:
            lines.append(f"- {d}")
    else:
        lines.append("No information")
    lines.append("")

    # Risks
    risks = grok.get("risks", [])
    lines.append("## Risk Factors")
    if risks:
        for r in risks:
            lines.append(f"- {r}")
    else:
        lines.append("No information")
    lines.append("")

    # Regulatory
    regulatory = grok.get("regulatory", [])
    lines.append("## Regulatory & Policy Trends")
    if regulatory:
        for r in regulatory:
            lines.append(f"- {r}")
    else:
        lines.append("No information")
    lines.append("")

    # Investor focus
    focus = grok.get("investor_focus", [])
    lines.append("## Investor Focus Points")
    if focus:
        for f in focus:
            lines.append(f"- {f}")
    else:
        lines.append("No information")
    lines.append("")

    # API status summary (KIK-431)
    status_section = _format_api_status(data.get("api_status"))
    if status_section:
        lines.append(status_section)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# format_market_research
# ---------------------------------------------------------------------------

def _fmt_change(value, is_point_diff: bool) -> str:
    """Format a daily/weekly change value for the macro table."""
    if value is None:
        return "-"
    if is_point_diff:
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:.2f}"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.2f}%"


def _vix_label(vix_price: float) -> str:
    """Convert VIX level to a market sentiment label."""
    if vix_price < 15:
        return "Low volatility (optimistic market)"
    if vix_price < 25:
        return "Normal range"
    if vix_price < 35:
        return "Rising anxiety"
    return "Panic level"


def format_market_research(data: dict) -> str:
    """Format market overview research as a Markdown report.

    Parameters
    ----------
    data : dict
        Output from researcher.research_market().

    Returns
    -------
    str
        Markdown-formatted report.
    """
    if not data:
        return "No research data available."

    market = data.get("market", "-")

    lines: list[str] = []
    lines.append(f"# {market} - Market Overview")
    lines.append("")

    # === Layer 1: Macro indicators table (yfinance) ===
    indicators = data.get("macro_indicators", [])
    if indicators:
        lines.append("## Key Indicators")
        lines.append("| Indicator | Current | Daily Change | Weekly Change |")
        lines.append("|:-----|------:|------:|--------:|")
        for ind in indicators:
            name = ind.get("name", "-")
            price = ind.get("price")
            is_point = ind.get("is_point_diff", False)
            price_str = _fmt_float(price, 2) if price is not None else "-"
            daily_str = _fmt_change(ind.get("daily_change"), is_point)
            weekly_str = _fmt_change(ind.get("weekly_change"), is_point)
            lines.append(f"| {name} | {price_str} | {daily_str} | {weekly_str} |")
        lines.append("")

        # Fear & Greed (VIX-based)
        vix = next((i for i in indicators if i.get("name") == "VIX"), None)
        if vix and vix.get("price") is not None:
            vix_price = vix["price"]
            label = _vix_label(vix_price)
            lines.append(f"**Fear & Greed: {label}** (VIX: {_fmt_float(vix_price, 2)})")
            lines.append("")

    # === Layer 2: Grok qualitative ===
    if data.get("api_unavailable"):
        lines.append("*Grok API (XAI_API_KEY) not configured \u2014 qualitative analysis skipped*")
        lines.append("")
        return "\n".join(lines)

    grok = data.get("grok_research", {})

    # Price action
    price_action = grok.get("price_action", "")
    lines.append("## Recent Price Action")
    lines.append(price_action if price_action else "No information")
    lines.append("")

    # Macro factors
    macro = grok.get("macro_factors", [])
    lines.append("## Macro Economic Factors")
    if macro:
        for m in macro:
            lines.append(f"- {m}")
    else:
        lines.append("No information")
    lines.append("")

    # Sentiment
    sentiment = grok.get("sentiment", {})
    score = sentiment.get("score", 0.0) if isinstance(sentiment, dict) else 0.0
    summary = sentiment.get("summary", "") if isinstance(sentiment, dict) else ""
    label = _sentiment_label(score)
    lines.append("## Sentiment")
    lines.append(f"**Judgment: {label}** (score: {_fmt_float(score)})")
    if summary:
        lines.append(summary)
    lines.append("")

    # Upcoming events
    events = grok.get("upcoming_events", [])
    lines.append("## Upcoming Events & Economic Indicators")
    if events:
        for e in events:
            lines.append(f"- {e}")
    else:
        lines.append("No information")
    lines.append("")

    # Sector rotation
    rotation = grok.get("sector_rotation", [])
    lines.append("## Sector Rotation")
    if rotation:
        for r in rotation:
            lines.append(f"- {r}")
    else:
        lines.append("No information")
    lines.append("")

    # API status summary (KIK-431)
    status_section = _format_api_status(data.get("api_status"))
    if status_section:
        lines.append(status_section)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# format_business_research
# ---------------------------------------------------------------------------

def format_business_research(data: dict) -> str:
    """Format business model research as a Markdown report.

    Parameters
    ----------
    data : dict
        Output from researcher.research_business().

    Returns
    -------
    str
        Markdown-formatted report.
    """
    if not data:
        return "No research data available."

    symbol = data.get("symbol", "-")
    name = data.get("name") or ""
    title = f"{name} ({symbol})" if name else symbol

    if data.get("api_unavailable"):
        lines: list[str] = []
        lines.append(f"# {title} - Business Model Analysis")
        lines.append("")
        lines.append(
            "*Business model analysis requires the Grok API. "
            "Please set the XAI_API_KEY environment variable.*"
        )
        lines.append("")
        status_section = _format_api_status(data.get("api_status"))
        if status_section:
            lines.append(status_section)
        return "\n".join(lines)

    grok = data.get("grok_research", {})
    lines: list[str] = []
    lines.append(f"# {title} - Business Model Analysis")
    lines.append("")

    # Overview
    overview = grok.get("overview", "")
    lines.append("## Business Overview")
    lines.append(overview if overview else "No information")
    lines.append("")

    # Segments
    segments = grok.get("segments", [])
    lines.append("## Business Segments")
    if segments:
        lines.append("| Segment | Revenue Share | Description |")
        lines.append("|:-----------|:---------|:-----|")
        for seg in segments:
            if isinstance(seg, dict):
                seg_name = seg.get("name", "-")
                share = seg.get("revenue_share", "-")
                desc = seg.get("description", "-")
                lines.append(f"| {seg_name} | {share} | {desc} |")
            else:
                lines.append(f"| {seg} | - | - |")
    else:
        lines.append("No information")
    lines.append("")

    # Revenue model
    revenue_model = grok.get("revenue_model", "")
    lines.append("## Revenue Model")
    lines.append(revenue_model if revenue_model else "No information")
    lines.append("")

    # Competitive advantages
    advantages = grok.get("competitive_advantages", [])
    lines.append("## Competitive Advantages")
    if advantages:
        for a in advantages:
            lines.append(f"- {a}")
    else:
        lines.append("No information")
    lines.append("")

    # Key metrics
    metrics = grok.get("key_metrics", [])
    lines.append("## Key KPIs")
    if metrics:
        for m in metrics:
            lines.append(f"- {m}")
    else:
        lines.append("No information")
    lines.append("")

    # Growth strategy
    strategy = grok.get("growth_strategy", [])
    lines.append("## Growth Strategy")
    if strategy:
        for s in strategy:
            lines.append(f"- {s}")
    else:
        lines.append("No information")
    lines.append("")

    # Risks
    risks = grok.get("risks", [])
    lines.append("## Business Risks")
    if risks:
        for r in risks:
            lines.append(f"- {r}")
    else:
        lines.append("No information")
    lines.append("")

    # API status summary (KIK-431)
    status_section = _format_api_status(data.get("api_status"))
    if status_section:
        lines.append(status_section)

    return "\n".join(lines)
