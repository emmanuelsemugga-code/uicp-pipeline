-- GAP‑19: Constraint versioning for zero‑downtime rotation
-- Run once against the PostgreSQL audit database.

CREATE TABLE IF NOT EXISTS constraints (
    id          SERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    version     INT NOT NULL,
    content     JSONB NOT NULL,
    active      BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    created_by  TEXT,
    reason      TEXT,
    UNIQUE (tenant_id, version)
);

CREATE INDEX IF NOT EXISTS idx_constraints_active ON constraints(tenant_id, active);

ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS constraint_version INT;
