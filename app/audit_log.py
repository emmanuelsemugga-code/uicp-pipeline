#!/usr/bin/env python3
"""
app/audit_log.py – GAP‑20 Audit Log Abstraction

Provides a swappable audit log backend so that single‑instance (Colab)
and multi‑instance (Docker Compose + PostgreSQL) deployments share the
same enforcement logic.
"""
import json, os, hashlib
from abc import ABC, abstractmethod

class AuditLog(ABC):
    """Abstract audit log interface."""

    @abstractmethod
    def append(self, decision: dict) -> str:
        """Append a decision record. Returns the decision_id."""
        ...

    @abstractmethod
    def get_by_id(self, decision_id: str) -> dict | None:
        """Retrieve a decision by its decision_id."""
        ...

    @abstractmethod
    def list_recent(self, limit: int = 100) -> list[dict]:
        """Return the most recent decisions."""
        ...

    @abstractmethod
    def export_range(self, start_date: str, end_date: str) -> list[dict]:
        """Export decisions in a date range (ISO format)."""
        ...

    @abstractmethod
    def verify_chain(self) -> bool:
        """Verify the cryptographic chain integrity."""
        ...


class LocalFileAuditLog(AuditLog):
    """
    Single‑instance audit log.
    Stores decisions in an in‑memory list and flushes to a JSON file on export.
    This is the exact behaviour of the original Phase4EnforcementGateway.
    """
    def __init__(self):
        self._entries: list[dict] = []

    def append(self, decision: dict) -> str:
        prev_hash = self._entries[-1]["_chain_hash"] if self._entries else "GENESIS"
        chain_input = prev_hash + decision["decision_id"]
        chain_hash = hashlib.sha256(chain_input.encode()).hexdigest()
        entry = {**decision, "_chain_hash": chain_hash}
        self._entries.append(entry)
        return decision["decision_id"]

    def get_by_id(self, decision_id: str) -> dict | None:
        for entry in self._entries:
            if entry.get("decision_id") == decision_id:
                return entry
        return None

    def list_recent(self, limit: int = 100) -> list[dict]:
        return self._entries[-limit:]

    def export_range(self, start_date: str, end_date: str) -> list[dict]:
        return [
            e for e in self._entries
            if start_date <= e.get("timestamp", "") <= end_date
        ]

    def verify_chain(self) -> bool:
        running = "GENESIS"
        for e in self._entries:
            expected = hashlib.sha256(
                (running + e["decision_id"]).encode()
            ).hexdigest()
            if e.get("_chain_hash") != expected:
                return False
            running = e["_chain_hash"]
        return True

    def get_all(self) -> list[dict]:
        return list(self._entries)


class PostgreSQLAuditLog(AuditLog):
    """
    Multi‑instance audit log backed by PostgreSQL.
    Requires psycopg2 and a running Postgres instance.
    """
    def __init__(self, dsn: str):
        import psycopg2
        self._dsn = dsn
        self._init_db()

    def _init_db(self):
        import psycopg2
        conn = psycopg2.connect(self._dsn)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                instance_id TEXT,
                decision_id TEXT UNIQUE,
                decision_data JSONB,
                result TEXT,
                signature TEXT,
                chain_hash TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_decision_id ON audit_log(decision_id);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp DESC);
        """)
        conn.commit()
        conn.close()

    def append(self, decision: dict) -> str:
        import psycopg2
        conn = psycopg2.connect(self._dsn)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO audit_log
                (instance_id, decision_id, decision_data, result, signature, chain_hash)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                decision.get("instance_id", "unknown"),
                decision["decision_id"],
                json.dumps(decision),
                decision.get("status", "UNKNOWN"),
                decision.get("decision_signature", ""),
                decision.get("_chain_hash", ""),
            ))
            conn.commit()
            return decision["decision_id"]
        finally:
            conn.close()

    def get_by_id(self, decision_id: str) -> dict | None:
        import psycopg2
        conn = psycopg2.connect(self._dsn)
        cur = conn.cursor()
        cur.execute("SELECT decision_data FROM audit_log WHERE decision_id=%s", (decision_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def list_recent(self, limit: int = 100) -> list[dict]:
        import psycopg2
        conn = psycopg2.connect(self._dsn)
        cur = conn.cursor()
        cur.execute("SELECT decision_data FROM audit_log ORDER BY timestamp DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def export_range(self, start_date: str, end_date: str) -> list[dict]:
        import psycopg2
        conn = psycopg2.connect(self._dsn)
        cur = conn.cursor()
        cur.execute(
            "SELECT decision_data FROM audit_log WHERE timestamp BETWEEN %s AND %s",
            (start_date, end_date),
        )
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def verify_chain(self) -> bool:
        entries = self.list_recent(10_000)
        running = "GENESIS"
        for e in entries:
            expected = hashlib.sha256(
                (running + e["decision_id"]).encode()
            ).hexdigest()
            if e.get("_chain_hash") != expected:
                return False
            running = e["_chain_hash"]
        return True
