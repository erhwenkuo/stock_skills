"""Stock, Screen, Report node operations (KIK-507).

Handles merge_stock, merge_screen, merge_report, merge_report_full,
tag_theme, merge_watchlist, and get_stock_history.
"""

from src.data.graph_store import _common


# ---------------------------------------------------------------------------
# Stock node
# ---------------------------------------------------------------------------

def merge_stock(symbol: str, name: str = "", sector: str = "", country: str = "") -> bool:
    """Create or update a Stock node."""
    if _common._get_mode() == "off":
        return False
    driver = _common._get_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            session.run(
                "MERGE (s:Stock {symbol: $symbol}) "
                "SET s.name = $name, s.sector = $sector, s.country = $country",
                symbol=symbol, name=name, sector=sector, country=country,
            )
            if sector:
                session.run(
                    "MERGE (sec:Sector {name: $sector}) "
                    "WITH sec "
                    "MATCH (s:Stock {symbol: $symbol}) "
                    "MERGE (s)-[:IN_SECTOR]->(sec)",
                    sector=sector, symbol=symbol,
                )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Screen node
# ---------------------------------------------------------------------------

def merge_screen(
    screen_date: str, preset: str, region: str, count: int,
    symbols: list[str],
    semantic_summary: str = "", embedding: list[float] | None = None,
) -> bool:
    """Create a Screen node and SURFACED relationships to stocks."""
    if _common._get_mode() == "off":
        return False
    driver = _common._get_driver()
    if driver is None:
        return False
    if not symbols:
        return False
    screen_id = f"screen_{screen_date}_{region}_{preset}"
    try:
        with driver.session() as session:
            session.run(
                "MERGE (sc:Screen {id: $id}) "
                "SET sc.date = $date, sc.preset = $preset, "
                "sc.region = $region, sc.count = $count",
                id=screen_id, date=screen_date, preset=preset,
                region=region, count=count,
            )
            _common._set_embedding(session, "Screen", screen_id, semantic_summary, embedding)
            for sym in symbols:
                session.run(
                    "MATCH (sc:Screen {id: $screen_id}) "
                    "MERGE (s:Stock {symbol: $symbol}) "
                    "MERGE (sc)-[:SURFACED]->(s)",
                    screen_id=screen_id, symbol=sym,
                )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Report node
# ---------------------------------------------------------------------------

def merge_report(
    report_date: str, symbol: str, score: float, verdict: str,
    semantic_summary: str = "", embedding: list[float] | None = None,
) -> bool:
    """Create a Report node and ANALYZED relationship."""
    if _common._get_mode() == "off":
        return False
    driver = _common._get_driver()
    if driver is None:
        return False
    report_id = f"report_{report_date}_{symbol}"
    try:
        with driver.session() as session:
            session.run(
                "MERGE (r:Report {id: $id}) "
                "SET r.date = $date, r.symbol = $symbol, "
                "r.score = $score, r.verdict = $verdict",
                id=report_id, date=report_date, symbol=symbol,
                score=score, verdict=verdict,
            )
            session.run(
                "MATCH (r:Report {id: $report_id}) "
                "MERGE (s:Stock {symbol: $symbol}) "
                "MERGE (r)-[:ANALYZED]->(s)",
                report_id=report_id, symbol=symbol,
            )
            _common._set_embedding(session, "Report", report_id, semantic_summary, embedding)
        return True
    except Exception:
        return False


def merge_report_full(
    report_date: str, symbol: str, score: float, verdict: str,
    price: float = 0, per: float = 0, pbr: float = 0,
    dividend_yield: float = 0, roe: float = 0, market_cap: float = 0,
    semantic_summary: str = "", embedding: list[float] | None = None,
) -> bool:
    """Extend an existing Report node with full valuation properties (KIK-413).

    Calls merge_report() first, then SETs additional numeric fields.
    Only runs in 'full' mode.
    """
    if _common._get_mode() != "full":
        return merge_report(report_date, symbol, score, verdict,
                            semantic_summary=semantic_summary, embedding=embedding)
    # Ensure base Report node exists
    merge_report(report_date, symbol, score, verdict,
                 semantic_summary=semantic_summary, embedding=embedding)
    driver = _common._get_driver()
    if driver is None:
        return False
    report_id = f"report_{report_date}_{symbol}"
    try:
        with driver.session() as session:
            session.run(
                "MATCH (r:Report {id: $id}) "
                "SET r.price = $price, r.per = $per, r.pbr = $pbr, "
                "r.dividend_yield = $div, r.roe = $roe, r.market_cap = $mcap",
                id=report_id, price=float(price or 0),
                per=float(per or 0), pbr=float(pbr or 0),
                div=float(dividend_yield or 0), roe=float(roe or 0),
                mcap=float(market_cap or 0),
            )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Theme tagging
# ---------------------------------------------------------------------------

def tag_theme(symbol: str, theme: str) -> bool:
    """Tag a stock with a theme."""
    if _common._get_mode() == "off":
        return False
    driver = _common._get_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            session.run(
                "MERGE (t:Theme {name: $theme}) "
                "WITH t "
                "MERGE (s:Stock {symbol: $symbol}) "
                "MERGE (s)-[:HAS_THEME]->(t)",
                theme=theme, symbol=symbol,
            )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Watchlist node (KIK-398)
# ---------------------------------------------------------------------------

def merge_watchlist(name: str, symbols: list[str],
                    semantic_summary: str = "",
                    embedding: list[float] | None = None) -> bool:
    """Create a Watchlist node and BOOKMARKED relationships to stocks."""
    if _common._get_mode() == "off":
        return False
    driver = _common._get_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            session.run(
                "MERGE (w:Watchlist {name: $name})",
                name=name,
            )
            # Watchlist uses 'name' as key, not 'id'; set embedding directly
            if semantic_summary or embedding is not None:
                _sets = []
                _params: dict = {"name": name}
                if semantic_summary:
                    _sets.append("w.semantic_summary = $summary")
                    _params["summary"] = semantic_summary
                if embedding is not None:
                    _sets.append("w.embedding = $embedding")
                    _params["embedding"] = embedding
                if _sets:
                    session.run(
                        f"MATCH (w:Watchlist {{name: $name}}) SET {', '.join(_sets)}",
                        **_params,
                    )
            for sym in symbols:
                session.run(
                    "MATCH (w:Watchlist {name: $name}) "
                    "MERGE (s:Stock {symbol: $symbol}) "
                    "MERGE (w)-[:BOOKMARKED]->(s)",
                    name=name, symbol=sym,
                )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_stock_history(symbol: str) -> dict:
    """Get all graph relationships for a stock (KIK-573: single query).

    Returns dict with keys: screens, reports, trades, health_checks,
    notes, themes, researches.
    """
    _empty = {"screens": [], "reports": [], "trades": [],
              "health_checks": [], "notes": [], "themes": [],
              "researches": []}
    driver = _common._get_driver()
    if driver is None:
        return dict(_empty)
    try:
        with driver.session() as session:
            record = session.run(
                "MATCH (s:Stock {symbol: $symbol}) "
                "OPTIONAL MATCH (sc:Screen)-[:SURFACED]->(s) "
                "OPTIONAL MATCH (rp:Report)-[:ANALYZED]->(s) "
                "OPTIONAL MATCH (t:Trade)-[:BOUGHT|SOLD]->(s) "
                "OPTIONAL MATCH (h:HealthCheck)-[:CHECKED]->(s) "
                "OPTIONAL MATCH (n:Note)-[:ABOUT]->(s) "
                "OPTIONAL MATCH (s)-[:HAS_THEME]->(th:Theme) "
                "OPTIONAL MATCH (rs:Research)-[:RESEARCHED]->(s) "
                "RETURN "
                "collect(DISTINCT {date: sc.date, preset: sc.preset, region: sc.region}) AS screens, "
                "collect(DISTINCT {date: rp.date, score: rp.score, verdict: rp.verdict}) AS reports, "
                "collect(DISTINCT {date: t.date, type: t.type, shares: t.shares, price: t.price}) AS trades, "
                "collect(DISTINCT {date: h.date}) AS health_checks, "
                "collect(DISTINCT {id: n.id, date: n.date, type: n.type, content: n.content}) AS notes, "
                "collect(DISTINCT th.name) AS themes, "
                "collect(DISTINCT {date: rs.date, research_type: rs.research_type, summary: rs.summary}) AS researches",
                symbol=symbol,
            ).single()

            if record is None:
                return dict(_empty)

            # Filter out null entries from OPTIONAL MATCH
            def _clean(items):
                return [d for d in items if d and any(v is not None for v in d.values())]

            return {
                "screens": sorted(_clean(record["screens"]), key=lambda x: x.get("date", ""), reverse=True),
                "reports": sorted(_clean(record["reports"]), key=lambda x: x.get("date", ""), reverse=True),
                "trades": sorted(_clean(record["trades"]), key=lambda x: x.get("date", ""), reverse=True),
                "health_checks": sorted(_clean(record["health_checks"]), key=lambda x: x.get("date", ""), reverse=True),
                "notes": sorted(_clean(record["notes"]), key=lambda x: x.get("date", ""), reverse=True),
                "themes": [t for t in record["themes"] if t is not None],
                "researches": sorted(_clean(record["researches"]), key=lambda x: x.get("date", ""), reverse=True),
            }
    except Exception:
        return dict(_empty)
