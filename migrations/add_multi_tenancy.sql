-- GAP‑18: Multi‑tenancy schema
-- Run once against the PostgreSQL audit database.

CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    status      TEXT DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS api_keys (
    key         TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    active      BOOLEAN DEFAULT TRUE
);

ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS tenant_id TEXT;
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log(tenant_id);
