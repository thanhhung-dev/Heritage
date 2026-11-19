-- Additive rollout prerequisite. Apply through the approved migration process.
ALTER TABLE account ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;
