#!/usr/bin/env python3
"""
app/constraint_store.py – GAP‑19 Constraint Store Abstraction

Hybrid constraint storage:
- LocalFileConstraintStore for single‑instance (Colab) — mtime polling, 5s cache
- PostgreSQLConstraintStore for multi‑instance — database polling, 5s cache

Both return (content_dict, version_int) for the active constraints.
"""
import json, os, time, hashlib
from abc import ABC, abstractmethod

class ConstraintStore(ABC):
    """Abstract constraint store — returns (content, version)."""
    @abstractmethod
    def get_constraints(self, tenant_id: str) -> tuple:
        """Return (content_dict, version_int) for the active constraints."""
        ...


class LocalFileConstraintStore(ConstraintStore):
    """
    Single‑instance constraint store.
    Reads constraints from a JSON file.  Detects changes via file mtime.
    Caches the active version for `cache_ttl` seconds (default 5).
    """
    def __init__(self, base_path: str, cache_ttl: float = 5.0):
        self._base_path = base_path
        self._cache_ttl = cache_ttl
        self._cache: dict = {}

    def get_constraints(self, tenant_id: str) -> tuple:
        path = self._base_path.format(tenant_id=tenant_id) if "{tenant_id}" in self._base_path else self._base_path
        now = time.time()

        if tenant_id in self._cache:
            ver, content, cached_at, cached_mtime = self._cache[tenant_id]
            if now - cached_at < self._cache_ttl:
                return content, ver

        if not os.path.exists(path):
            raise FileNotFoundError(f"Constraint file not found: {path}")

        current_mtime = os.path.getmtime(path)

        if tenant_id in self._cache:
            _, _, _, cached_mtime = self._cache[tenant_id]
            if current_mtime == cached_mtime:
                ver, content, _, _ = self._cache[tenant_id]
                self._cache[tenant_id] = (ver, content, now, current_mtime)
                return content, ver

        with open(path, "r") as f:
            content = json.load(f)

        content_hash = hashlib.sha256(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()
        version = int(content_hash[:8], 16)

        self._cache[tenant_id] = (version, content, now, current_mtime)
        return content, version


class PostgreSQLConstraintStore(ConstraintStore):
    """
    Multi‑instance constraint store.
    Polls the `constraints` table for the active version.
    Caches the active version for `cache_ttl` seconds (default 5).
    """
    def __init__(self, dsn: str, cache_ttl: float = 5.0):
        import psycopg2
        self._dsn = dsn
        self._cache_ttl = cache_ttl
        self._cache: dict = {}
        self._init_db()

    def _init_db(self):
        import psycopg2
        conn = psycopg2.connect(self._dsn)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS constraints (
                id          SERIAL PRIMARY KEY,
                tenant_id   TEXT NOT NULL,
                version     INT NOT NULL,
                content     JSONB NOT NULL,
                active      BOOLEAN DEFAULT FALSE,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                created_by  TEXT,
                reason      TEXT,
                UNIQUE (tenant_id, version)
            );
            CREATE INDEX IF NOT EXISTS idx_constraints_active
                ON constraints(tenant_id, active);
        """)
        conn.commit()
        conn.close()

    def get_constraints(self, tenant_id: str) -> tuple:
        import psycopg2
        now = time.time()

        if tenant_id in self._cache:
            ver, content, cached_at = self._cache[tenant_id]
            if now - cached_at < self._cache_ttl:
                return content, ver

        conn = psycopg2.connect(self._dsn)
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT version, content FROM constraints
                WHERE tenant_id = %s AND active = TRUE
                ORDER BY version DESC LIMIT 1
            """, (tenant_id,))
            row = cur.fetchone()
        finally:
            conn.close()

        if not row:
            return ({"canonical_constraints": []}, 0)

        version, content_json = row
        content = content_json if isinstance(content_json, dict) else json.loads(content_json)
        self._cache[tenant_id] = (version, content, now)
        return content, version
