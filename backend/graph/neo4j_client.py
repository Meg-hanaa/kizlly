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
            session_kwargs = {}
            if NEO4J_DATABASE and NEO4J_DATABASE != "neo4j":
                session_kwargs["database"] = NEO4J_DATABASE
            with self._driver.session(**session_kwargs) as session:
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
            session_kwargs = {}
            if NEO4J_DATABASE and NEO4J_DATABASE != "neo4j":
                session_kwargs["database"] = NEO4J_DATABASE
            with self._driver.session(**session_kwargs) as session:
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
        renewal_date: Optional[str] = None,
        notice_deadline: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """MERGE a Vendor, CREATE a Contract, and link them."""
        query = """
        MERGE (v:Vendor {name: $vendor_name})
        CREATE (c:Contract {
            id: $contract_id,
            title: $title,
            effectiveDate: $effective_date,
            expirationDate: $expiration_date,
            value: $value,
            status: $status,
            renewal_date: $renewal_date,
            notice_deadline: $notice_deadline,
            owner: $owner,
            createdAt: datetime()
        })
        CREATE (c)-[:WITH_VENDOR]->(v)
        CREATE (v)-[:APPEARS_IN]->(c)
        RETURN c.id AS contractId, v.name AS vendor
        """
        clean_renewal = renewal_date.split("T")[0] if (renewal_date and "T" in renewal_date) else renewal_date
        if clean_renewal:
            clean_renewal = clean_renewal[:10]
            
        clean_notice = notice_deadline.split("T")[0] if (notice_deadline and "T" in notice_deadline) else notice_deadline
        if clean_notice:
            clean_notice = clean_notice[:10]

        return self.run_query(query, {
            "contract_id": contract_id,
            "title": title,
            "vendor_name": vendor_name,
            "effective_date": effective_date,
            "expiration_date": expiration_date,
            "value": value,
            "status": status,
            "renewal_date": clean_renewal,
            "notice_deadline": clean_notice,
            "owner": owner,
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
        """MERGE a Date node and create a RENEWS_ON relationship."""
        # Truncate 'YYYY-MM-DDTHH:MM' or similar to 'YYYY-MM-DD' for date() compatibility
        short_date = renewal_date.split("T")[0] if "T" in renewal_date else renewal_date
        short_date = short_date[:10]
        
        query = """
        MATCH (c:Contract {id: $contract_id})
        MERGE (d:Date {date: $short_date})
        MERGE (c)-[:RENEWS_ON]->(d)
        RETURN c.id AS contractId, d.date AS renewalDate
        """
        return self.run_query(query, {
            "contract_id": contract_id,
            "short_date": short_date,
        })

    def create_alert(
        self,
        alert_id: str,
        contract_id: str,
        alert_type: str,
        fired_at: str,
        status: str = "unseen",
    ) -> List[Dict[str, Any]]:
        """CREATE an Alert node and link it to the Contract node."""
        query = """
        MATCH (c:Contract {id: $contract_id})
        CREATE (a:Alert {
            id: $alert_id,
            type: $alert_type,
            fired_at: $fired_at,
            status: $status
        })
        CREATE (c)-[:HAS_ALERT]->(a)
        RETURN a.id AS alertId
        """
        return self.run_query(query, {
            "alert_id": alert_id,
            "contract_id": contract_id,
            "alert_type": alert_type,
            "fired_at": fired_at,
            "status": status,
        })

    def mark_alert_seen_neo4j(self, alert_id: str) -> List[Dict[str, Any]]:
        """Update an Alert node status to 'seen'."""
        query = """
        MATCH (a:Alert {id: $alert_id})
        SET a.status = "seen"
        RETURN a.id AS alertId
        """
        return self.run_query(query, {"alert_id": alert_id})

    def log_audit_event(
        self,
        contract_id: str,
        action: str,
        details: str,
        reviewer_id: Optional[str] = None,
        reviewer_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """CREATE an AuditEvent node linked to the Contract node."""
        query = """
        MATCH (c:Contract {id: $contract_id})
        CREATE (ae:AuditEvent {
            action: $action,
            details: $details,
            reviewerId: $reviewer_id,
            reviewerName: $reviewer_name,
            timestamp: datetime()
        })
        CREATE (c)-[:HAS_AUDIT_EVENT]->(ae)
        RETURN ae.action AS action
        """
        return self.run_query(query, {
            "contract_id": contract_id,
            "action": action,
            "details": details,
            "reviewer_id": reviewer_id,
            "reviewer_name": reviewer_name,
        })
    # ------------------------------------------------------------------ #
    # Visualisation
    # ------------------------------------------------------------------ #
    def get_graph_data(self, owner: Optional[str] = None) -> Dict[str, list]:
        """Return all nodes and edges for front-end graph visualisation."""
        if not self.is_connected:
            return {"nodes": [], "edges": []}

        # Match only contract nodes owned by the user, and trace their immediate dependencies
        params = {}
        if owner:
            node_query = """
            MATCH (c:Contract {owner: $owner})
            OPTIONAL MATCH (c)-[r1:WITH_VENDOR]->(v:Vendor)
            OPTIONAL MATCH (c)-[r2:HAS_CLAUSE]->(cl:Clause)
            OPTIONAL MATCH (cl)-[r3:FLAGGED_AS]->(rt:RiskType)
            OPTIONAL MATCH (c)-[r4:RENEWS_ON]->(d:Date)
            WITH collect(c) + collect(v) + collect(cl) + collect(rt) + collect(d) AS allNodes
            UNWIND allNodes AS n
            WITH DISTINCT n
            WHERE n IS NOT NULL
            RETURN
                elementId(n) AS elementId,
                labels(n)    AS labels,
                properties(n) AS props
            LIMIT 200
            """
            edge_query = """
            MATCH (a)-[r]->(b)
            WHERE (a:Contract OR a:Vendor OR a:Clause OR a:RiskType OR a:Date)
              AND (b:Contract OR b:Vendor OR b:Clause OR b:RiskType OR b:Date)
              AND (
                (a:Contract AND a.owner = $owner) OR
                (b:Contract AND b.owner = $owner) OR
                EXISTS {
                    MATCH (c:Contract {owner: $owner})
                    WHERE (c)-[*..2]->(a) OR (c)-[*..2]->(b)
                }
              )
            WITH r, a, b LIMIT 500
            RETURN
                elementId(a) AS sourceId,
                elementId(b) AS targetId,
                type(r)      AS relType,
                properties(r) AS props
            """
            params["owner"] = owner
        else:
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

        def serialize_prop(v):
            if hasattr(v, "isoformat"):
                return v.isoformat()
            elif isinstance(v, (str, int, float, bool)) or v is None:
                return v
            else:
                return str(v)
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        try:
            raw_nodes = self.run_query(node_query, params)
            for rec in raw_nodes:
                node_labels = rec.get("labels", [])
                props = rec.get("props", {})
                node_id = rec.get("elementId")
                node_type = node_labels[0] if node_labels else "Unknown"
                label = (
                    props.get("title")
                    or props.get("name")
                    or props.get("id")
                    or props.get("date")
                    or str(node_id)
                )
                serialized_props = {k: serialize_prop(val) for k, val in props.items()}
                nodes.append({
                    "id": str(node_id),
                    "label": str(label),
                    "type": node_type,
                    "properties": serialized_props,
                })

            raw_edges = self.run_query(edge_query, params)
            for rec in raw_edges:
                edge_props = rec.get("props", {})
                serialized_edge_props = {k: serialize_prop(val) for k, val in edge_props.items()}
                edges.append({
                    "source": str(rec.get("sourceId")),
                    "target": str(rec.get("targetId")),
                    "type": rec.get("relType", "RELATED"),
                    "properties": serialized_edge_props,
                })

        except Exception as exc:
            logger.error("Failed to fetch graph data: %s", exc)

        return {"nodes": nodes, "edges": edges}
