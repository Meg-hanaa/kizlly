"""
graph/queries.py - Portfolio dashboard Cypher queries for Kizlly.

Each function accepts a :class:`Neo4jClient` and returns structured data
ready for the API layer. All queries are read-only.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Vendor exposure
# ------------------------------------------------------------------ #

def get_vendor_exposure(client: "Neo4jClient", owner: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return top-20 vendors by total active-contract exposure for an owner."""
    active_where = "c.status = 'Active' OR c.status = 'completed'"
    params = {}
    if owner:
        active_where = f"({active_where}) AND c.owner = $owner"
        params["owner"] = owner

    query = f"""
    MATCH (c:Contract)-[:WITH_VENDOR]->(v:Vendor)
    WHERE {active_where}
    RETURN
         v.name        AS vendor,
         count(c)      AS contractCount,
         sum(c.value)  AS totalExposure
    ORDER BY totalExposure DESC
    LIMIT 20
    """
    return client.run_query(query, params)


# ------------------------------------------------------------------ #
# Renewal risk
# ------------------------------------------------------------------ #

def get_renewal_risk(
    client: "Neo4jClient",
    days: int = 90,
    owner: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find contracts renewing within *days* for an owner and categorise urgency."""
    where_clauses = ["daysUntil >= 0", "daysUntil <= $days"]
    params = {"days": days}
    if owner:
        where_clauses.append("c.owner = $owner")
        params["owner"] = owner

    query = f"""
    MATCH (c:Contract)-[:RENEWS_ON]->(d:Date)
    MATCH (c)-[:WITH_VENDOR]->(v:Vendor)
    WITH c, v, d,
         duration.inDays(date(), date(d.date)).days AS daysUntil
    WHERE {' AND '.join(where_clauses)}
    RETURN
         c.id        AS contractId,
         c.title     AS title,
         v.name      AS vendor,
         d.date      AS renewalDate,
         c.value     AS value,
         daysUntil,
         CASE
             WHEN daysUntil <= 30 THEN 'URGENT'
             WHEN daysUntil <= 60 THEN 'SOON'
             ELSE 'UPCOMING'
         END AS urgency
    ORDER BY daysUntil ASC
    """
    return client.run_query(query, params)


# ------------------------------------------------------------------ #
# Clause / risk patterns
# ------------------------------------------------------------------ #

def get_clause_patterns(client: "Neo4jClient") -> List[Dict[str, Any]]:
    """Find risk types that appear across multiple vendors.

    Helps surface systemic risks in the portfolio — for example, if the
    same "unlimited liability" clause appears in contracts with five
    different vendors.

    Returns:
        A list of dicts with keys ``risk_type``, ``category``,
        ``vendor_count``, ``contract_count``, ``clause_count``,
        ``affected_vendors``.
    """
    query = """
    MATCH (cl:Clause)-[:FLAGGED_AS]->(rt:RiskType)
    MATCH (c:Contract)-[:HAS_CLAUSE]->(cl)
    MATCH (c)-[:WITH_VENDOR]->(v:Vendor)
    WITH rt,
         collect(DISTINCT v.name) AS vendors,
         count(DISTINCT c)        AS contractCount,
         count(DISTINCT cl)       AS clauseCount
    WHERE size(vendors) > 0
    RETURN
        rt.name       AS risk_type,
        rt.category   AS category,
        size(vendors)  AS vendor_count,
        contractCount  AS contract_count,
        clauseCount    AS clause_count,
        vendors        AS affected_vendors
    ORDER BY vendor_count DESC
    """
    return client.run_query(query)


# ------------------------------------------------------------------ #
# Portfolio statistics
# ------------------------------------------------------------------ #

def get_portfolio_stats(client: "Neo4jClient", owner: Optional[str] = None) -> Dict[str, Any]:
    """Return high-level portfolio statistics for a specific owner."""
    stats: Dict[str, Any] = {
        "total_contracts": 0,
        "active_vendors": 0,
        "flagged_clauses": 0,
        "risk_distribution": {},
    }

    # Match contract filter parameters
    match_clause = "MATCH (c:Contract)"
    where_clauses = []
    params = {}
    if owner:
        where_clauses.append("c.owner = $owner")
        params["owner"] = owner

    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    # Total contracts
    rows = client.run_query(f"{match_clause} {where_str} RETURN count(c) AS cnt", params)
    if rows:
        stats["total_contracts"] = rows[0].get("cnt", 0)

    # Active vendors
    active_where = "c.status = 'Active' OR c.status = 'completed'"
    if owner:
        active_where = f"({active_where}) AND c.owner = $owner"
    
    rows = client.run_query(
        "MATCH (c:Contract)-[:WITH_VENDOR]->(v:Vendor) "
        f"WHERE {active_where} "
        "RETURN count(DISTINCT v) AS cnt",
        params
    )
    if rows:
        stats["active_vendors"] = rows[0].get("cnt", 0)

    # Flagged clauses
    clause_where = ""
    if owner:
        clause_where = "WHERE c.owner = $owner"
    
    rows = client.run_query(
        "MATCH (c:Contract)-[:HAS_CLAUSE]->(cl:Clause)-[:FLAGGED_AS]->(:RiskType) "
        f"{clause_where} "
        "RETURN count(DISTINCT cl) AS cnt",
        params
    )
    if rows:
        stats["flagged_clauses"] = rows[0].get("cnt", 0)

    # Risk distribution
    rows = client.run_query(
        "MATCH (c:Contract)-[:HAS_CLAUSE]->(cl:Clause)-[:FLAGGED_AS]->(rt:RiskType) "
        f"{clause_where} "
        "RETURN rt.name AS risk_type, count(cl) AS cnt "
        "ORDER BY cnt DESC",
        params
    )
    stats["risk_distribution"] = {
        row["risk_type"]: row["cnt"] for row in rows
    }

    return stats


# ------------------------------------------------------------------ #
# Vendor blast radius
# ------------------------------------------------------------------ #

def get_vendor_blast_radius(
    client: "Neo4jClient",
    vendor_name: str,
) -> Dict[str, Any]:
    """Assess the full impact of a single vendor across the portfolio.

    Returns:
        A dict with ``vendor``, ``contracts`` (list of contract dicts),
        ``risk_flags`` (list), ``total_value``, and ``contract_count``.
    """
    result: Dict[str, Any] = {
        "vendor": vendor_name,
        "contracts": [],
        "risk_flags": [],
        "total_value": 0.0,
        "contract_count": 0,
    }

    # Contracts
    contracts = client.run_query(
        """
        MATCH (v:Vendor {name: $vendor_name})-[:APPEARS_IN]->(c:Contract)
        RETURN
            c.id             AS contractId,
            c.title          AS title,
            c.status         AS status,
            c.value          AS value,
            c.expirationDate AS expirationDate
        ORDER BY c.value DESC
        """,
        {"vendor_name": vendor_name},
    )
    result["contracts"] = contracts
    result["contract_count"] = len(contracts)
    result["total_value"] = sum(
        c.get("value", 0) or 0 for c in contracts
    )

    # Risk flags linked to that vendor's contracts
    risks = client.run_query(
        """
        MATCH (v:Vendor {name: $vendor_name})-[:APPEARS_IN]->(c:Contract)
              -[:HAS_CLAUSE]->(cl:Clause)-[:FLAGGED_AS]->(rt:RiskType)
        RETURN
            c.id        AS contractId,
            cl.id       AS clauseId,
            rt.name     AS riskType,
            rt.category AS category,
            cl.severity AS severity
        """,
        {"vendor_name": vendor_name},
    )
    result["risk_flags"] = risks

    return result


# ------------------------------------------------------------------ #
# Shared vendor exposure (hidden cross-vendor risk)
# ------------------------------------------------------------------ #

def get_shared_vendor_exposure(client: "Neo4jClient") -> List[Dict[str, Any]]:
    """Find contracts that share a common vendor — hidden concentration risk.

    Returns:
        A list of dicts with ``vendor``, ``contractIds``, ``titles``,
        ``totalValue``, ``contractCount``.
    """
    query = """
    MATCH (v:Vendor)-[:APPEARS_IN]->(c:Contract)
    WITH v,
         collect(c.id)    AS contractIds,
         collect(c.title) AS titles,
         sum(c.value)     AS totalValue,
         count(c)         AS contractCount
    WHERE contractCount > 1
    RETURN
        v.name        AS vendor,
        contractIds,
        titles,
        totalValue,
        contractCount
    ORDER BY totalValue DESC
    """
    return client.run_query(query)
