-- Additive durable settings/queue, using the existing dated SQL convention.
CREATE TABLE IF NOT EXISTS rag_pipeline (
    id VARCHAR(36) PRIMARY KEY, name VARCHAR(120) NOT NULL UNIQUE,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    chunking JSONB NOT NULL, embedding JSONB NOT NULL, retrieval JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS rag_reindex_job (
    id VARCHAR(36) PRIMARY KEY,
    pipeline_id VARCHAR(36) NOT NULL REFERENCES rag_pipeline(id) ON DELETE RESTRICT,
    pipeline_revision INTEGER NOT NULL,
    config_snapshot JSONB NOT NULL, document_ids JSONB NOT NULL, document_revisions JSONB NOT NULL,
    requested_by VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED')),
    active_slot INTEGER UNIQUE,
    processed_documents INTEGER NOT NULL DEFAULT 0, indexed_passages INTEGER NOT NULL DEFAULT 0,
    error TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
    CHECK ((status IN ('PENDING','RUNNING') AND active_slot IS NOT NULL AND active_slot = 1) OR
           (status IN ('COMPLETED','FAILED') AND active_slot IS NULL))
);
CREATE INDEX IF NOT EXISTS ix_rag_reindex_job_pipeline_id ON rag_reindex_job(pipeline_id);
CREATE INDEX IF NOT EXISTS ix_rag_reindex_job_status ON rag_reindex_job(status);
