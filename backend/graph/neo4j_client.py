"""
graph/neo4j_client.py - Neo4j AuraDB client for Kizlly.

Provides a singleton Neo4j driver that executes Cypher queries for
contract graph operations. Degrades gracefully when Neo4j is not
configured — every public method returns an empty/safe default instead
of crashing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Singleton Neo4j driver wrapper.

    Usage::

        client = Neo4jClient()
        client.verify_connection()
        records = client.run_query("MATCH (n) RETURN n LIMIT 5")
        client.close()
    """

    _instance: Optional["Neo4jClient"] = None

    # ------------------------------------------------------------------ #
    # Singleton
    # ------------------------------------------------------------------ #
    def __new__(cls) -> "Neo4jClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    # ------------------------------------------------------------------ #
    # Init
    # ------------------------------------------------------------------ #
    def __init__(self) -> None:
        """Connect to Neo4j AuraDB using neo4j+s:// protocol.

        If any of the required config values (URI, password) are empty the
        client stays in a *disconnected* state and all queries return empty
        results.
        """
        if self._initialized:
            return
        self._initialized = True

        self._driver = None
        self._connected = False

        if not NEO4J_URI or not NEO4J_PASSWORD:
            logger.warning(
                "Neo4j is NOT configured (NEO4J_URI or NEO4J_PASSWORD missing). "
                "Graph features will be disabled."
            )
            return

        try:
            uri = NEO4J_URI
            # Ensure we use the neo4j+s:// protocol for AuraDB
            if uri.startswith("bolt://"):
                uri = uri.replace("bolt://", "neo4j+s://", 1)
            elif not uri.startswith("neo4j+s://") and not uri.startswith("neo4j://"):
                uri = f"neo4j+s://{uri}"

            self._driver = GraphDatabase.driver(
                uri,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
                max_connection_lifetime=300,
                connection_timeout=10,
            )
            self._connected = True
            logger.info("Neo4j driver initialised for %s", uri)
        except Exception as exc:
            logger.error("Failed to create Neo4j driver: %s", exc)
            self._driver = None
            self._connected = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """Cleanly shut down the Neo4j driver."""
        if self._driver is not None:
            try:
                self._driver.close()
                logger.info("Neo4j driver closed.")
            except Exception as exc:
                logger.error("Error closing Neo4j driver: %s", exc)
            finally:
                self._driver = None
                self._connected = False
                Neo4jClient._instance = None
                self._initialized = False

    @property
    def is_connected(self) -> bool:
        """Return ``True`` if the driver is available."""
        return self._connected and self._driver is not None

    # ------------------------------------------------------------------ #
    # Connection verification
    # ------------------------------------------------------------------ #
    def verify_connection(self) -> bool:
        """Test connectivity to the Neo4j instance.

        Returns:
            ``True`` if a simple query succeeds, ``False`` otherwise.
        """
        if not self.is_connected:
            return False
        try:
            with self._driver.session(database=NEO4J_DATABASE) as session:
                session.run("RETURN 1 AS ok").consume()
            logger.info("Neo4j connection verified.")
            return True
        except (ServiceUnavailable, Neo4jError, Exception) as exc:
            logger.error("Neo4j connection verification failed: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    # Generic query execution
    # ------------------------------------------------------------------ #
    def run_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return records as a list of dicts.

        Args:
            query:  A parameterised Cypher statement.
            params: Parameters to bind into the query.

        Returns:
            A list of ``dict`` — one per result record.  Returns ``[]`` if
            Neo4j is unavailable.
        """
        if not self.is_connected:
            logger.debug("Neo4j not connected; skipping query.")
            return []

        params = params or {}
        try:
            with self._driver.session(database=NEO4J_DATABASE) as session:
                result = session.run(query, **params)
                return [record.data() for record in result]
        except (ServiceUnavailable, Neo4jError) as exc:
            logger.error("Cypher query failed: %s | query=%s", exc, query[:120])
            return []
        except Exception as exc:
            logger.error("Unexpected error during query: %s", exc)
            return []

    # ------------------------------------------------------------------ #
    # Contract operations
    # ------------------------------------------------------------------ #
    def create_contract(
        self,
        contract_id: str,
        title: str,
        vendor_name: str,
        effective_date: Optional[str] = None,
        expiration_date: Optional[str] = None,
        value: float = 0.0,
        status: str = "Active",
    ) -> List[Dict[str, Any]]:
        """MERGE a Vendor, CREATE a Contract, and link them.

        Uses ``MERGE`` on the Vendor so it stays unique across contracts.

        Args:
            contract_id:     Unique contract identifier.
            title:           Human-readable contract title.
            vendor_name:     Vendor / counter-party name.
            effective_date:  ISO date string (YYYY-MM-DD) or ``None``.
            expiration_date: ISO date string (YYYY-MM-DD) or ``None``.
            value:           Monetary value of the contract.
            status:          Contract status label.

        Returns:
            Query result records.
        """
        query = """
        MERGE (v:Vendor {name: $vendor_name})
        CREATE (c:Contract {
            id: $contract_id,
            title: $title,
            effectiveDate: $effective_date,
            expirationDate: $expiration_date,
            value: $value,
            status: $status,
            createdAt: datetime()
        })
        CREATE (c)-[:WITH_VENDOR]->(v)
        CREATE (v)-[:APPEARS_IN]->(c)
        RETURN c.id AS contractId, v.name AS vendor
        """
        return self.run_query(query, {
            "contract_id": contract_id,
            "title": title,
            "vendor_name": vendor_name,
            "effective_date": effective_date,
            "expiration_date": expiration_date,
            "value": value,
            "status": status,
        })

    # ------------------------------------------------------------------ #
    # Clause operations
    # ------------------------------------------------------------------ #
    def create_clause(
        self,
        clause_id: str,
        contract_id: str,
        clause_type: str,
        text: str,
        section: Optional[str] = None,
        severity: str = "Medium",
    ) -> List[Dict[str, Any]]:
        """CREATE a Clause node and link it to the parent Contract.

        Args:
            clause_id:    Unique clause identifier.
            contract_id:  Parent contract identifier.
            clause_type:  Type/category of the clause.
            text:         Full clause text.
            section:      Section reference in the document.
            severity:     Risk severity label.

        Returns:
            Query result records.
        """
        query = """
        MATCH (c:Contract {id: $contract_id})
        CREATE (cl:Clause {
            id: $clause_id,
            type: $clause_type,
            text: $text,
            section: $section,
            severity: $severity,
            createdAt: datetime()
        })
        CREATE (c)-[:HAS_CLAUSE]->(cl)
        RETURN cl.id AS clauseId, c.id AS contractId
        """
        return self.run_query(query, {
            "clause_id": clause_id,
            "contract_id": contract_id,
            "clause_type": clause_type,
            "text": text,
            "section": section,
            "severity": severity,
        })

    # ------------------------------------------------------------------ #
    # Risk flagging
    # ------------------------------------------------------------------ #
    def flag_clause_risk(
        self,
        clause_id: str,
        risk_type_name: str,
        category: str = "Other",
        confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """MERGE a RiskType node and CREATE a FLAGGED_AS relationship.

        Args:
            clause_id:      Clause to flag.
            risk_type_name: Name of the risk type (e.g. "Unlimited Liability").
            category:       Risk category label.
            confidence:     AI confidence score 0-1.

        Returns:
            Query result records.
        """
        query = """
        MATCH (cl:Clause {id: $clause_id})
        MERGE (rt:RiskType {name: $risk_type_name})
        ON CREATE SET rt.category = $category
        CREATE (cl)-[:FLAGGED_AS {confidence: $confidence, flaggedAt: datetime()}]->(rt)
        RETURN cl.id AS clauseId, rt.name AS riskType
        """
        return self.run_query(query, {
            "clause_id": clause_id,
            "risk_type_name": risk_type_name,
            "category": category,
            "confidence": confidence,
        })

    # ------------------------------------------------------------------ #
    # Renewal dates
    # ------------------------------------------------------------------ #
    def set_renewal_date(
        self,
        contract_id: str,
        renewal_date: str,
    ) -> List[Dict[str, Any]]:
        """MERGE a Date node and create a RENEWS_ON relationship.

        Args:
            contract_id:  Contract to set the renewal for.
            renewal_date: ISO date string (YYYY-MM-DD).

        Returns:
            Query result records.
        """
        query = """
        MATCH (c:Contract {id: $contract_id})
        MERGE (d:Date {date: $renewal_date})
        MERGE (c)-[:RENEWS_ON]->(d)
        RETURN c.id AS contractId, d.date AS renewalDate
        """
        return self.run_query(query, {
            "contract_id": contract_id,
            "renewal_date": renewal_date,
        })

    # ------------------------------------------------------------------ #
    # Visualisation
    # ------------------------------------------------------------------ #
    def get_graph_data(self) -> Dict[str, list]:
        """Return all nodes and edges for front-end graph visualisation.

        Results are capped at **200 nodes** to keep the payload
        manageable.

        Returns:
            ``{"nodes": [...], "edges": [...]}``
        """
        if not self.is_connected:
            return {"nodes": [], "edges": []}

        node_query = """
        MATCH (n)
        WHERE n:Contract OR n:Vendor OR n:Clause OR n:RiskType OR n:Date
        WITH n LIMIT 200
        RETURN
            elementId(n) AS elementId,
            labels(n)    AS labels,
            properties(n) AS props
        """
        edge_query = """
        MATCH (a)-[r]->(b)
        WHERE (a:Contract OR a:Vendor OR a:Clause OR a:RiskType OR a:Date)
          AND (b:Contract OR b:Vendor OR b:Clause OR b:RiskType OR b:Date)
        WITH r, a, b LIMIT 500
        RETURN
            elementId(a) AS sourceId,
            elementId(b) AS targetId,
            type(r)      AS relType,
            properties(r) AS props
        """

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        try:
            raw_nodes = self.run_query(node_query)
            for rec in raw_nodes:
                node_labels = rec.get("labels", [])
                props = rec.get("props", {})
                node_id = props.get("id") or props.get("name") or rec.get("elementId")
                node_type = node_labels[0] if node_labels else "Unknown"
                label = (
                    props.get("title")
                    or props.get("name")
                    or props.get("id")
                    or props.get("date")
                    or str(node_id)
                )
                nodes.append({
                    "id": str(node_id),
                    "label": str(label),
                    "type": node_type,
                    "properties": props,
                })

            raw_edges = self.run_query(edge_query)
            for rec in raw_edges:
                edges.append({
                    "source": str(rec.get("sourceId")),
                    "target": str(rec.get("targetId")),
                    "type": rec.get("relType", "RELATED"),
                    "properties": rec.get("props", {}),
                })

        except Exception as exc:
            logger.error("Failed to fetch graph data: %s", exc)

        return {"nodes": nodes, "edges": edges}
