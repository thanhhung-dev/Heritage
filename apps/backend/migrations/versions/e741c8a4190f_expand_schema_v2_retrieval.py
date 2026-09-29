"""Expand the existing database with the Schema v2 retrieval slice.

Revision ID: e741c8a4190f
Revises: d0f4a2c81e7b
"""
from alembic import op

revision = "e741c8a4190f"
down_revision = "d0f4a2c81e7b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Expand only: every statement is safe for an already populated volume.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("""
        CREATE TABLE IF NOT EXISTS corpus_release (
          version integer PRIMARY KEY CHECK (version > 0),
          status varchar NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'published', 'retired')),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        INSERT INTO corpus_release(version) VALUES (1) ON CONFLICT DO NOTHING;

        ALTER TABLE document ADD COLUMN IF NOT EXISTS source_type varchar;
        ALTER TABLE document ADD COLUMN IF NOT EXISTS tier smallint;
        ALTER TABLE document ADD COLUMN IF NOT EXISTS observed_at timestamptz;
        ALTER TABLE document ADD COLUMN IF NOT EXISTS content_hash text;
        ALTER TABLE document DROP CONSTRAINT IF EXISTS _doc_not_withdrawn;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_document_source_version
          ON document(source_url, content_hash) WHERE source_url IS NOT NULL AND content_hash IS NOT NULL;

        ALTER TABLE entity ADD COLUMN IF NOT EXISTS in_scope boolean NOT NULL DEFAULT false;
        ALTER TABLE entity ADD COLUMN IF NOT EXISTS depth_tier smallint NOT NULL DEFAULT 1;
        ALTER TABLE entity ADD COLUMN IF NOT EXISTS entry_status varchar NOT NULL DEFAULT 'draft';
        ALTER TABLE entity_alias DROP CONSTRAINT IF EXISTS chk_alias_type;
        ALTER TABLE entity_alias ADD CONSTRAINT chk_alias_type CHECK (
          alias_type IN ('official', 'historical', 'common', 'sino_vietnamese', 'english', 'typo')
        );
        DO $$ BEGIN
          ALTER TABLE passage ADD CONSTRAINT fk_passage_corpus_release
            FOREIGN KEY (corpus_version) REFERENCES corpus_release(version);
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        CREATE TABLE IF NOT EXISTS entity_evidence (
          entity_id uuid NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
          passage_id uuid NOT NULL REFERENCES passage(id) ON DELETE CASCADE,
          PRIMARY KEY(entity_id, passage_id)
        );
        CREATE TABLE IF NOT EXISTS entity_alias_evidence (
          entity_alias_id uuid NOT NULL REFERENCES entity_alias(id) ON DELETE CASCADE,
          passage_id uuid NOT NULL REFERENCES passage(id) ON DELETE CASCADE,
          PRIMARY KEY(entity_alias_id, passage_id)
        );
        CREATE INDEX IF NOT EXISTS idx_passage_text_trgm ON passage USING gin(text gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS idx_entity_name_v2_trgm ON entity USING gin(name gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS idx_entity_alias_v2_trgm ON entity_alias USING gin(alias gin_trgm_ops);
    """)


def downgrade() -> None:
    # Deliberately non-destructive: this revision is an adoption/expand boundary.
    pass
