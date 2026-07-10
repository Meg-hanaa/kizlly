"""
workflow/audit_log.py - Immutable audit trail for Kizlly.

Backs every workflow action with an append-only SQLite database.
By design, **no UPDATE or DELETE operations exist** — the log is a
tamper-evident record of every step, review decision, and external
data transfer.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import AUDIT_DB_PATH

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# SQL constants
# ------------------------------------------------------------------ #

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id          TEXT    NOT NULL,
    step                 TEXT    NOT NULL,
    action               TEXT    NOT NULL,
    details              TEXT    DEFAULT '',
    reviewer_id          TEXT,
    reviewer_name        TEXT,
    timestamp            TEXT    NOT NULL,
    data_sent_externally TEXT
);
"""

_INSERT_SQL = """
INSERT INTO audit_log
    (workflow_id, step, action, details, reviewer_id, reviewer_name,
     timestamp, data_sent_externally)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?);
"""

_SELECT_ALL_SQL = "SELECT * FROM audit_log ORDER BY id ASC"
_SELECT_BY_WF_SQL = (
    "SELECT * FROM audit_log WHERE workflow_id = ? ORDER BY id ASC"
)
_SELECT_PRIVACY_ALL_SQL = (
    "SELECT * FROM audit_log WHERE data_sent_externally IS NOT NULL "
    "ORDER BY id ASC"
)
_SELECT_PRIVACY_BY_WF_SQL = (
    "SELECT * FROM audit_log WHERE data_sent_externally IS NOT NULL "
    "AND workflow_id = ? ORDER BY id ASC"
)


class AuditLog:
    """Append-only audit trail backed by SQLite.

    Usage::

        audit = AuditLog()
        audit.log_event("wf-123", "ingest", "started")
        trail = audit.get_trail("wf-123")
    """

    def __init__(self) -> None:
        """Open (or create) the SQLite database at ``config.AUDIT_DB_PATH``.

        The audit table is created automatically if it does not exist.
        """
        db_path = str(AUDIT_DB_PATH)
        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute(_CREATE_TABLE_SQL)
            self._conn.commit()
            logger.info("Audit log opened at %s", db_path)
        except sqlite3.Error as exc:
            logger.error("Failed to initialise audit DB: %s", exc)
            raise

    # ------------------------------------------------------------------ #
    # Write (append only)
    # ------------------------------------------------------------------ #

    def log_event(
        self,
        workflow_id: str,
        step: str,
        action: str,
        details: str = "",
        reviewer_id: Optional[str] = None,
        reviewer_name: Optional[str] = None,
        data_sent_externally: Optional[str] = None,
    ) -> None:
        """Append a single event to the audit log.

        This is the **only** write operation — no UPDATE or DELETE methods
        exist by design.

        Args:
            workflow_id:          Identifier of the parent workflow.
            step:                 Name of the workflow step.
            action:               Short verb describing what happened.
            details:              Free-text details (optional).
            reviewer_id:          ID of the human reviewer (if applicable).
            reviewer_name:        Display name of the reviewer.
            data_sent_externally: Description of data sent to external APIs
                                  (for the privacy log).
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            self._conn.execute(
                _INSERT_SQL,
                (
                    workflow_id,
                    step,
                    action,
                    details,
                    reviewer_id,
                    reviewer_name,
                    timestamp,
                    data_sent_externally,
                ),
            )
            self._conn.commit()
            logger.debug(
                "Audit | wf=%s step=%s action=%s", workflow_id, step, action
            )
        except sqlite3.Error as exc:
            logger.error("Audit log write failed: %s", exc)

    # ------------------------------------------------------------------ #
    # Read helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _rows_to_dicts(rows: list) -> List[Dict[str, Any]]:
        """Convert ``sqlite3.Row`` objects to plain dicts."""
        return [dict(row) for row in rows]

    def get_trail(
        self,
        workflow_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return audit entries, optionally filtered by workflow.

        Args:
            workflow_id: If supplied, only entries for this workflow are
                         returned. Pass ``None`` for the complete log.

        Returns:
            A list of dicts matching the audit_log table schema.
        """
        try:
            if workflow_id:
                cursor = self._conn.execute(_SELECT_BY_WF_SQL, (workflow_id,))
            else:
                cursor = self._conn.execute(_SELECT_ALL_SQL)
            return self._rows_to_dicts(cursor.fetchall())
        except sqlite3.Error as exc:
            logger.error("Audit log read failed: %s", exc)
            return []

    def get_privacy_log(
        self,
        workflow_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return only entries where ``data_sent_externally`` is not null.

        This provides a quick view of all data that left the system —
        useful for privacy audits and GDPR compliance.

        Args:
            workflow_id: Optional filter.

        Returns:
            A list of dicts for entries with external data transfers.
        """
        try:
            if workflow_id:
                cursor = self._conn.execute(
                    _SELECT_PRIVACY_BY_WF_SQL, (workflow_id,)
                )
            else:
                cursor = self._conn.execute(_SELECT_PRIVACY_ALL_SQL)
            return self._rows_to_dicts(cursor.fetchall())
        except sqlite3.Error as exc:
            logger.error("Privacy log read failed: %s", exc)
            return []
