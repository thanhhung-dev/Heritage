-- Additive migration for the active account/roles authentication API.
-- Apply manually before deploying admin auth; never store raw bearer tokens.
-- Expired entries may be removed by an operator after JWT expiry has passed.
BEGIN;
CREATE TABLE IF NOT EXISTS revoked_access_token (
    token_hash VARCHAR(64) PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_revoked_access_token_expires_at
    ON revoked_access_token (expires_at);
COMMIT;
