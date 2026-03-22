"""Community query functions (KIK-578 split from community.py).

Query functions for retrieving community data, stock membership,
similar stocks, and community-based lessons.
"""

from typing import Optional

from src.data.graph_query import _common


# ---------------------------------------------------------------------------
# Public API — Queries
# ---------------------------------------------------------------------------


def get_communities(level: int = 0) -> list[dict]:
    """Retrieve existing Community nodes from Neo4j.

    Returns list of dicts: {id, name, size, level, created_at, members}
    """
    driver = _common._get_driver()
    if driver is None:
        return []
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (c:Community) "
                "WHERE c.level = $level "
                "OPTIONAL MATCH (s:Stock)-[:BELONGS_TO]->(c) "
                "RETURN c.id AS id, c.name AS name, c.size AS size, "
                "c.level AS level, c.created_at AS created_at, "
                "collect(s.symbol) AS members "
                "ORDER BY c.size DESC",
                level=level,
            )
            return [dict(r) for r in result]
    except Exception:
        return []


def get_stock_community(symbol: str) -> Optional[dict]:
    """Get the community a stock belongs to.

    Returns {community_id, name, size, level, peers} or None.
    """
    driver = _common._get_driver()
    if driver is None:
        return None
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (s:Stock {symbol: $symbol})-[:BELONGS_TO]->(c:Community) "
                "OPTIONAL MATCH (peer:Stock)-[:BELONGS_TO]->(c) "
                "WHERE peer.symbol <> $symbol "
                "RETURN c.id AS community_id, c.name AS name, "
                "c.size AS size, c.level AS level, "
                "collect(peer.symbol) AS peers",
                symbol=symbol,
            )
            record = result.single()
            if record is None:
                return None
            return dict(record)
    except Exception:
        return None


def get_similar_stocks(
    symbol: str,
    top_k: int = 5,
    similarity_cutoff: float = 0.3,
) -> list[dict]:
    """Get stocks most similar to the given symbol.

    Lightweight version: computes similarity without full community detection.
    Returns list of dicts: {symbol, similarity, shared_screens, shared_themes,
    shared_sectors, shared_news}
    """
    from src.data.graph_query.community_detect import (
        _fetch_cooccurrence_vectors,
        _jaccard_single,
    )

    driver = _common._get_driver()
    if driver is None:
        return []
    try:
        vectors = _fetch_cooccurrence_vectors(driver)
        if symbol not in vectors:
            return []
        target = vectors[symbol]
        results = []
        for other_sym, other_vec in vectors.items():
            if other_sym == symbol:
                continue
            sim = _jaccard_single(target, other_vec)
            if sim >= similarity_cutoff:
                results.append(
                    {
                        "symbol": other_sym,
                        "similarity": round(sim, 4),
                        "shared_screens": len(
                            target["screens"] & other_vec["screens"]
                        ),
                        "shared_themes": len(target["themes"] & other_vec["themes"]),
                        "shared_sectors": len(
                            target["sectors"] & other_vec["sectors"]
                        ),
                        "shared_news": len(target["news"] & other_vec["news"]),
                    }
                )
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    except Exception:
        return []


def update_stock_community(
    symbol: str,
    similarity_cutoff: float = 0.3,
) -> Optional[dict]:
    """Assign a stock to the best-matching existing community.

    Computes similarity against all existing community members and
    assigns the stock to the community with highest average similarity.
    Does NOT trigger full re-detection.

    Returns the assigned community dict or None.
    """
    from src.data.graph_query.community_detect import (
        _fetch_cooccurrence_vectors,
        _jaccard_single,
    )

    driver = _common._get_driver()
    if driver is None:
        return None
    try:
        from src.data.graph_store import _common as gs_common

        if gs_common._get_mode() == "off":
            return None

        vectors = _fetch_cooccurrence_vectors(driver)
        if symbol not in vectors:
            return None

        # Get existing communities
        communities = get_communities(level=0)
        if not communities:
            return None

        target = vectors[symbol]
        best_community = None
        best_avg_sim = 0.0

        for comm in communities:
            members = comm.get("members", [])
            if not members:
                continue
            sims = []
            for member in members:
                if member in vectors:
                    sim = _jaccard_single(target, vectors[member])
                    sims.append(sim)
            if sims:
                avg_sim = sum(sims) / len(sims)
                if avg_sim > best_avg_sim and avg_sim >= similarity_cutoff:
                    best_avg_sim = avg_sim
                    best_community = comm

        if best_community is None:
            return None

        # Write BELONGS_TO relationship
        comm_id = best_community["id"]
        with driver.session() as session:
            session.run(
                "MATCH (s:Stock {symbol: $symbol}) "
                "MATCH (c:Community {id: $cid}) "
                "MERGE (s)-[:BELONGS_TO]->(c)",
                symbol=symbol,
                cid=comm_id,
            )

        return {
            "community_id": comm_id,
            "name": best_community.get("name", ""),
            "size": best_community.get("size", 0),
        }
    except Exception:
        return None


def get_community_lessons(symbol: str, limit: int = 3) -> list[dict]:
    """Get lessons from peer stocks in the same community (KIK-569).

    Traverses: Stock->BELONGS_TO->Community<-BELONGS_TO<-Stock<-ABOUT<-Note(lesson)

    Returns list of lesson dicts with added '_source_symbol' field
    to indicate the peer stock the lesson came from.
    """
    driver = _common._get_driver()
    if driver is None:
        return []
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (s:Stock {symbol: $symbol})-[:BELONGS_TO]->(c:Community) "
                "MATCH (peer:Stock)-[:BELONGS_TO]->(c) "
                "WHERE peer.symbol <> $symbol "
                "MATCH (n:Note {type: 'lesson'})-[:ABOUT]->(peer) "
                "RETURN n.content AS content, n.trigger AS trigger, "
                "n.expected_action AS expected_action, n.date AS date, "
                "n.id AS id, peer.symbol AS source_symbol, "
                "c.name AS community_name "
                "ORDER BY n.date DESC LIMIT $limit",
                symbol=symbol,
                limit=limit,
            )
            lessons = []
            for r in result:
                les = {
                    "id": r["id"] or "",
                    "content": r["content"] or "",
                    "trigger": r["trigger"] or "",
                    "expected_action": r["expected_action"] or "",
                    "date": r["date"] or "",
                    "symbol": f"{r['source_symbol']}->{r['community_name']}",
                    "_source_symbol": r["source_symbol"],
                    "_community": r["community_name"],
                }
                lessons.append(les)
            return lessons
    except Exception:
        return []
