"""
graph/schema.py - Neo4j graph schema initialization for Kizlly.

Creates constraints and indexes required by the contract knowledge graph.
All statements use ``IF NOT EXISTS`` so the function is safe to call on
every application startup (idempotent).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Constraint & index definitions
# ------------------------------------------------------------------ #

_CONSTRAINTS = [
    # Unique constraints
    (
        "constraint_contract_id",
        "CREATE CONSTRAINT constraint_contract_id IF NOT EXISTS "
        "FOR (c:Contract) REQUIRE c.id IS UNIQUE",
    ),
    (
        "constraint_vendor_name",
        "CREATE CONSTRAINT constraint_vendor_name IF NOT EXISTS "
        "FOR (v:Vendor) REQUIRE v.name IS UNIQUE",
    ),
    (
        "constraint_clause_id",
        "CREATE CONSTRAINT constraint_clause_id IF NOT EXISTS "
        "FOR (cl:Clause) REQUIRE cl.id IS UNIQUE",
    ),
    (
        "constraint_risktype_name",
        "CREATE CONSTRAINT constraint_risktype_name IF NOT EXISTS "
        "FOR (rt:RiskType) REQUIRE rt.name IS UNIQUE",
    ),
]

_INDEXES = [
    # Property indexes for fast lookups
    (
        "index_contract_status",
        "CREATE INDEX index_contract_status IF NOT EXISTS "
        "FOR (c:Contract) ON (c.status)",
    ),
    (
        "index_contract_expiration",
        "CREATE INDEX index_contract_expiration IF NOT EXISTS "
        "FOR (c:Contract) ON (c.expirationDate)",
    ),
    (
        "index_date_date",
        "CREATE INDEX index_date_date IF NOT EXISTS "
        "FOR (d:Date) ON (d.date)",
    ),
]


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

def initialize_schema(client: "Neo4jClient") -> None:
    """Create all required constraints and indexes in Neo4j.

    This function is designed to be called once during application startup.
    Every statement uses ``IF NOT EXISTS`` so repeated invocations are
    harmless.

    Args:
        client: An initialised :class:`Neo4jClient` instance.
    """
    if not client.is_connected:
        logger.warning(
            "Neo4j is not connected — skipping schema initialisation."
        )
        return

    logger.info("Initialising Neo4j graph schema …")

    for name, cypher in _CONSTRAINTS:
        try:
            client.run_query(cypher)
            logger.info("  ✓ Constraint  %s", name)
        except Exception as exc:
            logger.error("  ✗ Constraint  %s failed: %s", name, exc)

    for name, cypher in _INDEXES:
        try:
            client.run_query(cypher)
            logger.info("  ✓ Index       %s", name)
        except Exception as exc:
            logger.error("  ✗ Index       %s failed: %s", name, exc)

    logger.info("Neo4j schema initialisation complete.")
