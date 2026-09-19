-- ============================================================
-- Initial schema for the API key management service.
-- This file is auto-loaded by Postgres the first time the
-- container starts (see docker-compose.yml).
-- ============================================================

-- Lets Postgres generate UUIDs for us (gen_random_uuid()).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ------------------------------------------------------------
-- tenants: one row per organisation using the service.
-- Everything else in this schema hangs off tenant_id, which is
-- how we keep one tenant's data invisible to every other tenant.
-- ------------------------------------------------------------
CREATE TABLE tenants (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- api_keys: one row per issued key.
-- We NEVER store the raw key -- only its hash. The prefix is
-- stored in plain text so we can find the one candidate row
-- fast, then do a single (slow, deliberate) hash comparison
-- against just that row instead of every key in the table.
-- ------------------------------------------------------------
CREATE TABLE api_keys (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenants(id),
    key_prefix  text NOT NULL UNIQUE,   -- e.g. "sk_live_a3f29d"
    key_hash    text NOT NULL,          -- Argon2 hash of the full key
    scopes      text[] NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now(),
    revoked_at  timestamptz             -- NULL means still active
);

-- Every lookup during request auth is "find this prefix", so
-- this index is the one that makes the hot path fast.
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);

-- Every other query we'll write ("all keys for tenant X") filters
-- by tenant_id, so it earns an index of its own.
CREATE INDEX idx_api_keys_tenant ON api_keys(tenant_id);

-- ------------------------------------------------------------
-- request_logs: one row per request made with a key.
-- This table grows fast, so it's partitioned by month from day
-- one -- each partition is its own physical chunk, which keeps
-- queries and maintenance fast even once there are millions of
-- rows, and makes old data easy to drop later if you add a
-- retention policy.
-- ------------------------------------------------------------
CREATE TABLE request_logs (
    id           bigserial,
    key_id       uuid NOT NULL,
    tenant_id    uuid NOT NULL,
    endpoint     text NOT NULL,
    status_code  int NOT NULL,
    logged_at    timestamptz NOT NULL DEFAULT now()
) PARTITION BY RANGE (logged_at);

-- Partitioned tables need at least one partition to accept rows.
-- A DEFAULT partition catches anything that doesn't match a more
-- specific partition, so inserts work right away. In week 6, when
-- we generate millions of synthetic rows, we'll add real monthly
-- partitions (e.g. FOR VALUES FROM ('2026-09-01') TO ('2026-10-01'))
-- -- that's where the performance payoff of partitioning actually
-- shows up. For now, the default partition is enough to get started.
CREATE TABLE request_logs_default PARTITION OF request_logs DEFAULT;

CREATE INDEX idx_request_logs_tenant_time ON request_logs(tenant_id, logged_at);
