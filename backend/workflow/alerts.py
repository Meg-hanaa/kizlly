"""
workflow/alerts.py - Local alerts storage for Kizlly.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import AUDIT_DB_PATH

logger = logging.getLogger(__name__)

_CREATE_ALERTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    fired_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unseen'
);
"""

class AlertManager:
    """Manages the persistence of contract renewal alerts in a local SQLite database."""

    def __init__(self) -> None:
        self.db_path = str(AUDIT_DB_PATH)
        try:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute(_CREATE_ALERTS_TABLE_SQL)
            self._conn.commit()
            logger.info("Alert database initialised.")
        except sqlite3.Error as exc:
            logger.error("Failed to initialise alerts table in SQLite: %s", exc)
            raise

    def has_alert_fired(self, contract_id: str, alert_type: str) -> bool:
        """Check if an alert of a specific type has already been fired for a contract."""
        try:
            cursor = self._conn.execute(
                "SELECT 1 FROM alerts WHERE contract_id = ? AND alert_type = ?",
                (contract_id, alert_type)
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as exc:
            logger.error("Error checking alert fire status: %s", exc)
            return False

    def create_alert(
        self,
        alert_id: str,
        contract_id: str,
        alert_type: str,
        fired_at: str,
        status: str = "unseen",
    ) -> None:
        """Insert a new alert record into the database."""
        try:
            self._conn.execute(
                "INSERT INTO alerts (id, contract_id, alert_type, fired_at, status) VALUES (?, ?, ?, ?, ?)",
                (alert_id, contract_id, alert_type, fired_at, status)
            )
            self._conn.commit()
            logger.info("Alert %s created in SQLite for contract %s", alert_id, contract_id)
        except sqlite3.Error as exc:
            logger.error("Failed to insert alert in SQLite: %s", exc)

    def get_unseen_alerts(self) -> List[Dict[str, Any]]:
        """Retrieve all alerts with 'unseen' status."""
        try:
            cursor = self._conn.execute(
                "SELECT * FROM alerts WHERE status = 'unseen' ORDER BY fired_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            logger.error("Failed to query unseen alerts: %s", exc)
            return []

    def mark_alert_seen(self, alert_id: str) -> bool:
        """Update an alert's status to 'seen'."""
        try:
            cursor = self._conn.execute(
                "UPDATE alerts SET status = 'seen' WHERE id = ?",
                (alert_id,)
            )
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as exc:
            logger.error("Failed to mark alert as seen: %s", exc)
            return False

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Fetch details of a single alert by ID."""
        try:
            cursor = self._conn.execute(
                "SELECT * FROM alerts WHERE id = ?",
                (alert_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as exc:
            logger.error("Failed to get alert: %s", exc)
            return None


# Global singleton instance
alert_manager = AlertManager()
