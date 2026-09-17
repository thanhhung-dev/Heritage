-- ============================================================
-- Cultural Memory GraphRAG + 3D Virtual Tour — Schema v2
-- SQL dump (PostgreSQL) sinh từ file DBML
-- Thứ tự tạo bảng đã sắp theo phụ thuộc khoá ngoại (FK)
-- ============================================================

BEGIN;

-- ---------- EXTENSIONS ----------
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------- ENUM ----------

-- LỚP ADMIN (không phụ thuộc bảng khác)

CREATE TABLE admin_account (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username            TEXT NOT NULL UNIQUE,
  password_hash       TEXT NOT NULL, -- argon2id
  session_token_hash  TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LỚP TRI THỨC (KG)

CREATE TABLE document (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title         TEXT NOT NULL,
  region        VARCHAR NOT NULL, -- 'hue' | 'da_nang'
  source_url    TEXT NOT NULL,
  source_type   VARCHAR NOT NULL, -- official | academic | management | press | encyclopedia | other
  tier          SMALLINT NOT NULL, -- 1 = ưu tiên cao nhất
  observed_at   TIMESTAMPTZ NOT NULL, -- thời điểm nội dung nguồn được quan sát/thu thập
  license       TEXT,
  content_hash  TEXT NOT NULL, -- phát hiện thay đổi và tránh nhập trùng
  raw_text      TEXT NOT NULL, -- toàn văn gốc, dùng để re-chunk
  withdrawn_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_document_source_type CHECK (
    source_type IN ('official', 'academic', 'management', 'press', 'encyclopedia', 'other')
  ),
  CONSTRAINT chk_document_tier CHECK (tier BETWEEN 1 AND 4),
  CONSTRAINT uq_document_source_version UNIQUE (source_url, content_hash)
);

CREATE INDEX idx_document_region ON document (region);
CREATE INDEX idx_document_source ON document (source_type, tier);

CREATE TABLE corpus_release (
  version       INT PRIMARY KEY,
  status        VARCHAR NOT NULL DEFAULT 'draft',
  published_by  UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  published_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_corpus_release_version CHECK (version > 0),
  CONSTRAINT chk_corpus_release_status CHECK (status IN ('draft', 'published', 'retired')),
  CONSTRAINT chk_corpus_release_publish CHECK (
    (status = 'draft' AND published_by IS NULL AND published_at IS NULL)
    OR (status <> 'draft' AND published_by IS NOT NULL AND published_at IS NOT NULL)
  )
);

INSERT INTO corpus_release (version) VALUES (1);

CREATE TABLE passage (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id    UUID NOT NULL REFERENCES document(id),
  text           TEXT NOT NULL, -- BẤT BIẾN - không UPDATE
  char_start     INT NOT NULL,
  char_end       INT NOT NULL,
  corpus_version INT NOT NULL DEFAULT 1 REFERENCES corpus_release(version),
  tsv            TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED,
  embedding      VECTOR(1024),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_passage_char_start CHECK (char_start >= 0),
  CONSTRAINT chk_passage_span CHECK (char_end > char_start),
  CONSTRAINT uq_passage_span UNIQUE (document_id, corpus_version, char_start),
  CONSTRAINT uq_passage_id_version UNIQUE (id, corpus_version)
);

CREATE INDEX idx_passage_document ON passage (document_id, corpus_version);
CREATE INDEX idx_passage_tsv ON passage USING GIN (tsv);
CREATE INDEX idx_passage_text_trgm ON passage USING GIN (text gin_trgm_ops);
CREATE INDEX idx_passage_embedding ON passage USING HNSW (embedding vector_cosine_ops);

CREATE TABLE entity (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type             VARCHAR NOT NULL, -- person | place | event | artifact
  canonical_name   TEXT NOT NULL,
  normalized_name  TEXT NOT NULL,
  subtype          TEXT, -- phân loại domain chi tiết, không thay thế type
  wikipedia_title  TEXT, -- external identifier, không phải evidence
  wikidata_qid     VARCHAR,
  in_scope         BOOLEAN NOT NULL DEFAULT false,
  depth_tier       SMALLINT NOT NULL DEFAULT 1,
  entry_status     VARCHAR NOT NULL DEFAULT 'draft',
  embedding        VECTOR(1024), -- optional; dimension must match embedding model
  primary_passage_id UUID NOT NULL REFERENCES passage(id),
  created_by       UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_by      UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_at      TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_entity_type CHECK (type IN ('person', 'place', 'event', 'artifact')),
  CONSTRAINT chk_entity_depth_tier CHECK (depth_tier BETWEEN 1 AND 3),
  CONSTRAINT chk_entity_entry_status CHECK (entry_status IN ('draft', 'reviewed', 'published', 'withdrawn')),
  CONSTRAINT chk_entity_review CHECK (
    (entry_status = 'draft' AND reviewed_by IS NULL AND reviewed_at IS NULL)
    OR (entry_status <> 'draft' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
  ),
  CONSTRAINT chk_entity_wikidata_qid CHECK (wikidata_qid IS NULL OR wikidata_qid ~ '^Q[1-9][0-9]*$'),
  CONSTRAINT uq_entity_normalized_type UNIQUE (normalized_name, type),
  CONSTRAINT uq_entity_wikidata_qid UNIQUE (wikidata_qid)
);

CREATE INDEX idx_entity_name_trgm ON entity USING GIN (canonical_name gin_trgm_ops);
CREATE INDEX idx_entity_scope ON entity (in_scope, entry_status, depth_tier);

CREATE TABLE entity_evidence (
  entity_id  UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  passage_id UUID NOT NULL REFERENCES passage(id) ON DELETE CASCADE,
  PRIMARY KEY (entity_id, passage_id)
);

CREATE TABLE entity_alias (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id            UUID NOT NULL REFERENCES entity(id),
  alias                TEXT NOT NULL,
  normalized_alias     TEXT NOT NULL,
  alias_type           VARCHAR NOT NULL, -- official | historical | common | typo
  confidence           NUMERIC(4,3) NOT NULL DEFAULT 1.0,
  primary_passage_id   UUID NOT NULL REFERENCES passage(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_entity_alias_confidence CHECK (confidence BETWEEN 0 AND 1),
  CONSTRAINT chk_entity_alias_type CHECK (
    alias_type IN ('official', 'historical', 'common', 'sino_vietnamese', 'english', 'typo')
  ),
  CONSTRAINT uq_entity_alias_normalized UNIQUE (entity_id, normalized_alias)
);

CREATE INDEX idx_entity_alias_entity ON entity_alias (entity_id);
CREATE INDEX idx_entity_alias_normalized ON entity_alias (normalized_alias);
CREATE INDEX idx_entity_alias_trgm ON entity_alias USING GIN (alias gin_trgm_ops);

CREATE TABLE entity_alias_evidence (
  entity_alias_id UUID NOT NULL REFERENCES entity_alias(id) ON DELETE CASCADE,
  passage_id      UUID NOT NULL REFERENCES passage(id) ON DELETE CASCADE,
  PRIMARY KEY (entity_alias_id, passage_id)
);

CREATE TABLE place_profile (
  entity_id    UUID PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
  address      TEXT,
  ward         TEXT,
  district     TEXT,
  province     TEXT,
  latitude     NUMERIC(9,6),
  longitude    NUMERIC(9,6),
  primary_passage_id UUID NOT NULL REFERENCES passage(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_place_profile_latitude CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  CONSTRAINT chk_place_profile_longitude CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);

CREATE TABLE place_profile_evidence (
  entity_id  UUID NOT NULL REFERENCES place_profile(entity_id) ON DELETE CASCADE,
  passage_id UUID NOT NULL REFERENCES passage(id) ON DELETE CASCADE,
  PRIMARY KEY (entity_id, passage_id)
);

CREATE TABLE claim_field (
  code              TEXT PRIMARY KEY,
  label_vi          TEXT NOT NULL,
  value_type        VARCHAR NOT NULL,
  default_unit      TEXT,
  is_time_sensitive BOOLEAN NOT NULL DEFAULT false,
  CONSTRAINT chk_claim_field_value_type CHECK (
    value_type IN ('text', 'number', 'boolean', 'date', 'year', 'money', 'json')
  )
);

CREATE FUNCTION validate_claim_value() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
  expected_type VARCHAR;
  fallback_unit TEXT;
BEGIN
  SELECT value_type, default_unit
    INTO expected_type, fallback_unit
    FROM claim_field
   WHERE code = NEW.field_code;

  IF expected_type IS NULL THEN
    RETURN NEW; -- FK claim.field_code sẽ báo lỗi rõ ràng hơn.
  END IF;

  NEW.unit := COALESCE(NEW.unit, fallback_unit);

  IF (expected_type = 'text' AND jsonb_typeof(NEW.value) <> 'string')
     OR (expected_type IN ('number', 'money') AND jsonb_typeof(NEW.value) <> 'number')
     OR (expected_type = 'boolean' AND jsonb_typeof(NEW.value) <> 'boolean')
     OR (expected_type = 'date' AND (
       jsonb_typeof(NEW.value) <> 'string'
       OR NEW.value #>> '{}' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     ))
     OR (expected_type = 'year' AND (
       jsonb_typeof(NEW.value) <> 'number'
       OR NEW.value #>> '{}' !~ '^-?[0-9]+$'
     )) THEN
    RAISE EXCEPTION 'claim value does not match field % type %', NEW.field_code, expected_type
      USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TABLE claim (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id      UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  field_code     TEXT NOT NULL REFERENCES claim_field(code),
  value          JSONB NOT NULL,
  unit           TEXT,
  observed_at    TIMESTAMPTZ NOT NULL,
  valid_from     DATE,
  valid_until    DATE,
  confidence     NUMERIC(4,3) NOT NULL DEFAULT 1.0,
  is_canonical   BOOLEAN NOT NULL DEFAULT false,
  entry_status   VARCHAR NOT NULL DEFAULT 'draft',
  corpus_version INT NOT NULL DEFAULT 1 REFERENCES corpus_release(version),
  primary_passage_id UUID NOT NULL,
  created_by     UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_by    UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_at    TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_claim_confidence CHECK (confidence BETWEEN 0 AND 1),
  CONSTRAINT chk_claim_valid_range CHECK (
    valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from
  ),
  CONSTRAINT chk_claim_status CHECK (entry_status IN ('draft', 'reviewed', 'published', 'withdrawn')),
  CONSTRAINT chk_claim_review CHECK (
    (entry_status = 'draft' AND reviewed_by IS NULL AND reviewed_at IS NULL)
    OR (entry_status <> 'draft' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
  ),
  CONSTRAINT fk_claim_primary_evidence FOREIGN KEY (primary_passage_id, corpus_version)
    REFERENCES passage(id, corpus_version),
  CONSTRAINT uq_claim_id_version UNIQUE (id, corpus_version)
);

CREATE TRIGGER trg_validate_claim_value
BEFORE INSERT OR UPDATE OF field_code, value, unit ON claim
FOR EACH ROW EXECUTE FUNCTION validate_claim_value();

CREATE INDEX idx_claim_lookup ON claim (entity_id, field_code, is_canonical);
CREATE UNIQUE INDEX uq_claim_canonical
  ON claim (entity_id, field_code, corpus_version)
  WHERE is_canonical = true AND entry_status = 'published';

CREATE TABLE claim_evidence (
  claim_id       UUID NOT NULL,
  passage_id     UUID NOT NULL,
  corpus_version INT NOT NULL REFERENCES corpus_release(version),
  PRIMARY KEY (claim_id, passage_id, corpus_version),
  FOREIGN KEY (claim_id, corpus_version) REFERENCES claim(id, corpus_version) ON DELETE CASCADE,
  FOREIGN KEY (passage_id, corpus_version) REFERENCES passage(id, corpus_version) ON DELETE CASCADE
);

CREATE TABLE event_type (
  code     TEXT PRIMARY KEY,
  label_vi TEXT NOT NULL
);

CREATE TABLE timeline_event (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id      UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  year_start     INT NOT NULL,
  year_end       INT,
  precision      VARCHAR NOT NULL DEFAULT 'year',
  event_type     TEXT NOT NULL REFERENCES event_type(code),
  title          TEXT NOT NULL,
  actor_id       UUID REFERENCES entity(id) ON DELETE SET NULL,
  summary        TEXT,
  artifact_id    UUID REFERENCES entity(id) ON DELETE SET NULL,
  entry_status   VARCHAR NOT NULL DEFAULT 'draft',
  corpus_version INT NOT NULL DEFAULT 1 REFERENCES corpus_release(version),
  primary_passage_id UUID NOT NULL,
  created_by     UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_by    UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_at    TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_timeline_year_range CHECK (year_end IS NULL OR year_end >= year_start),
  CONSTRAINT chk_timeline_precision CHECK (
    precision IN ('year', 'decade', 'century', 'range', 'circa')
  ),
  CONSTRAINT chk_timeline_status CHECK (entry_status IN ('draft', 'reviewed', 'published', 'withdrawn')),
  CONSTRAINT chk_timeline_review CHECK (
    (entry_status = 'draft' AND reviewed_by IS NULL AND reviewed_at IS NULL)
    OR (entry_status <> 'draft' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
  ),
  CONSTRAINT fk_timeline_primary_evidence FOREIGN KEY (primary_passage_id, corpus_version)
    REFERENCES passage(id, corpus_version),
  CONSTRAINT uq_timeline_id_version UNIQUE (id, corpus_version)
);

CREATE INDEX idx_timeline_entity_year ON timeline_event (entity_id, year_start, year_end);
CREATE INDEX idx_timeline_type ON timeline_event (event_type);

CREATE TABLE timeline_event_evidence (
  timeline_event_id UUID NOT NULL,
  passage_id        UUID NOT NULL,
  corpus_version    INT NOT NULL REFERENCES corpus_release(version),
  PRIMARY KEY (timeline_event_id, passage_id, corpus_version),
  FOREIGN KEY (timeline_event_id, corpus_version)
    REFERENCES timeline_event(id, corpus_version) ON DELETE CASCADE,
  FOREIGN KEY (passage_id, corpus_version)
    REFERENCES passage(id, corpus_version) ON DELETE CASCADE
);

CREATE TABLE participant_role (
  code             TEXT PRIMARY KEY,
  label_vi         TEXT NOT NULL,
  label_en         TEXT,
  description      TEXT,
  is_contribution  BOOLEAN NOT NULL DEFAULT false
);

INSERT INTO participant_role (code, label_vi, label_en, is_contribution) VALUES
  ('actor',        'Chủ thể thực hiện',  'Actor',        false),
  ('founder',      'Người sáng lập',     'Founder',      true),
  ('commissioner', 'Người chủ trì',      'Commissioner', true),
  ('sponsor',      'Người bảo trợ',      'Sponsor',      true),
  ('architect',    'Kiến trúc sư',       'Architect',    true),
  ('builder',      'Người xây dựng',     'Builder',      true),
  ('restorer',     'Người trùng tu',     'Restorer',     true),
  ('donor',        'Người hiến tặng',    'Donor',        true),
  ('manager',      'Người quản lý',      'Manager',      true),
  ('contributor',  'Người đóng góp',     'Contributor',  true),
  ('witness',      'Nhân chứng',         'Witness',      false),
  ('subject',      'Đối tượng sự kiện',  'Subject',      false),
  ('object',       'Đối tượng tác động', 'Object',       false),
  ('place',        'Địa điểm',           'Place',        false),
  ('artifact',     'Hiện vật',           'Artifact',     false),
  ('other',        'Vai trò khác',       'Other',        false);

CREATE INDEX idx_participant_role_contribution
  ON participant_role (is_contribution)
  WHERE is_contribution = true;

CREATE TABLE timeline_event_participant (
  timeline_event_id UUID NOT NULL REFERENCES timeline_event(id) ON DELETE CASCADE,
  entity_id         UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  role_code         TEXT NOT NULL REFERENCES participant_role(code),
  PRIMARY KEY (timeline_event_id, entity_id, role_code)
);

CREATE INDEX idx_timeline_participant_entity
  ON timeline_event_participant (entity_id, role_code);

CREATE TABLE predicate (
  code         TEXT PRIMARY KEY,
  label_vi     TEXT NOT NULL,
  label_en     TEXT,
  is_symmetric BOOLEAN NOT NULL DEFAULT false,
  inverse_of   TEXT REFERENCES predicate(code),
  weight       REAL NOT NULL DEFAULT 1.0,
  CONSTRAINT chk_predicate_weight CHECK (weight > 0)
);

CREATE TABLE relation (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id           UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  predicate            TEXT NOT NULL REFERENCES predicate(code),
  object_id            UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  confidence           NUMERIC(4,3) NOT NULL DEFAULT 1.0,
  entry_status         VARCHAR NOT NULL DEFAULT 'draft',
  corpus_version       INT NOT NULL DEFAULT 1 REFERENCES corpus_release(version),
  primary_passage_id   UUID NOT NULL,
  created_by           UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_by          UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_at          TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_relation_no_loop CHECK (subject_id <> object_id),
  CONSTRAINT chk_relation_confidence CHECK (confidence BETWEEN 0 AND 1),
  CONSTRAINT chk_relation_status CHECK (entry_status IN ('draft', 'reviewed', 'published', 'withdrawn')),
  CONSTRAINT chk_relation_review CHECK (
    (entry_status = 'draft' AND reviewed_by IS NULL AND reviewed_at IS NULL)
    OR (entry_status <> 'draft' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
  ),
  CONSTRAINT fk_relation_primary_evidence FOREIGN KEY (primary_passage_id, corpus_version)
    REFERENCES passage(id, corpus_version),
  CONSTRAINT uq_relation_id_version UNIQUE (id, corpus_version),
  CONSTRAINT uq_relation_triple UNIQUE (subject_id, predicate, object_id, corpus_version)
);

CREATE INDEX idx_relation_subject ON relation (subject_id, predicate);
CREATE INDEX idx_relation_object ON relation (object_id, predicate);

CREATE TABLE relation_evidence (
  relation_id    UUID NOT NULL,
  passage_id     UUID NOT NULL,
  corpus_version INT NOT NULL REFERENCES corpus_release(version),
  PRIMARY KEY (relation_id, passage_id, corpus_version),
  FOREIGN KEY (relation_id, corpus_version)
    REFERENCES relation(id, corpus_version) ON DELETE CASCADE,
  FOREIGN KEY (passage_id, corpus_version)
    REFERENCES passage(id, corpus_version) ON DELETE CASCADE
);

CREATE TABLE narrative_section (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id      UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  section_code   VARCHAR NOT NULL,
  title          TEXT NOT NULL,
  body_md        TEXT NOT NULL,
  author_id      UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_by    UUID REFERENCES admin_account(id) ON DELETE SET NULL,
  reviewed_at    TIMESTAMPTZ,
  entry_status   VARCHAR NOT NULL DEFAULT 'draft',
  corpus_version INT NOT NULL DEFAULT 1 REFERENCES corpus_release(version),
  primary_passage_id UUID NOT NULL,
  order_index    INT NOT NULL DEFAULT 0,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_narrative_section_code CHECK (
    section_code IN (
      'tong_quan', 'ten_goi', 'khoi_lap', 'vai_tro_lich_su', 'kien_truc',
      'hien_vat', 'nhan_vat', 'bien_dong_hien_dai', 'tham_quan'
    )
  ),
  CONSTRAINT chk_narrative_status CHECK (entry_status IN ('draft', 'reviewed', 'published', 'withdrawn')),
  CONSTRAINT chk_narrative_review CHECK (
    (entry_status = 'draft' AND reviewed_by IS NULL AND reviewed_at IS NULL)
    OR (entry_status <> 'draft' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
  ),
  CONSTRAINT fk_narrative_primary_evidence FOREIGN KEY (primary_passage_id, corpus_version)
    REFERENCES passage(id, corpus_version),
  CONSTRAINT uq_narrative_id_version UNIQUE (id, corpus_version),
  CONSTRAINT uq_narrative_section UNIQUE (entity_id, section_code, corpus_version)
);

CREATE INDEX idx_narrative_entity ON narrative_section (entity_id, section_code, entry_status);

CREATE TABLE narrative_evidence (
  narrative_section_id UUID NOT NULL,
  passage_id            UUID NOT NULL,
  corpus_version        INT NOT NULL REFERENCES corpus_release(version),
  PRIMARY KEY (narrative_section_id, passage_id, corpus_version),
  FOREIGN KEY (narrative_section_id, corpus_version)
    REFERENCES narrative_section(id, corpus_version) ON DELETE CASCADE,
  FOREIGN KEY (passage_id, corpus_version)
    REFERENCES passage(id, corpus_version) ON DELETE CASCADE
);

-- ============================================================
-- LỚP NỘI DUNG 3D (CMG)
-- ============================================================

CREATE TABLE site (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                 TEXT NOT NULL,
  region               VARCHAR NOT NULL,
  entity_id            UUID NOT NULL REFERENCES entity(id),
  description          TEXT,
  source_document_id   UUID REFERENCES document(id),
  source_passage_id    UUID REFERENCES passage(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE scene (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id         UUID NOT NULL REFERENCES site(id),
  name            TEXT NOT NULL, -- vd: "Tầng 1 - Sảnh chính"
  transform_7dof  JSONB NOT NULL, -- translate+rotate(quat)+scale để căn trục
  order_index     INT, -- thứ tự khu vực trong site, dùng cho điều hướng
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE model_asset (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scene_id         UUID NOT NULL REFERENCES scene(id),
  lod_level        INT NOT NULL, -- 0 = cao nhất, tăng dần = càng nén nhẹ
  file_url         TEXT NOT NULL, -- URL trên object storage/CDN, KHÔNG lưu blob
  format           VARCHAR NOT NULL DEFAULT 'glb', -- glb | splat | sog
  compression      VARCHAR, -- draco+ktx2 | meshopt | none
  file_size_bytes  BIGINT,
  is_proxy         BOOLEAN NOT NULL DEFAULT false, -- bản cực nhẹ dùng raycast/preview lúc đang tải
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_model_asset_scene_lod UNIQUE (scene_id, lod_level)
);



CREATE TABLE story (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id      UUID NOT NULL REFERENCES site(id), -- 1 story có thể đi qua nhiều scene trong cùng site
  title        TEXT NOT NULL,
  camera_path  JSONB NOT NULL, -- mảng keyframe camera, mỗi keyframe có scene_id kèm theo
  created_by   UUID REFERENCES admin_account(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE narration (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  story_id    UUID NOT NULL UNIQUE REFERENCES story(id),
  audio_path  TEXT NOT NULL, -- URL trên object storage
  duration_ms INT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE transcript (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  story_id  UUID NOT NULL REFERENCES story(id),
  text      TEXT NOT NULL,
  start_ms  INT NOT NULL,
  end_ms    INT NOT NULL,
  seq       INT NOT NULL
);

CREATE TABLE hotspot (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scene_id    UUID NOT NULL REFERENCES scene(id),
  entity_id   UUID NOT NULL REFERENCES entity(id),
  x           FLOAT NOT NULL,
  y           FLOAT NOT NULL,
  z           FLOAT NOT NULL, -- toạ độ LOCAL, trước transform_7dof
  label       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE citation (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  passage_id     UUID REFERENCES passage(id),
  transcript_id  UUID REFERENCES transcript(id),
  quote          TEXT NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_citation_exactly_one_source CHECK (
    (passage_id IS NOT NULL)::int + (transcript_id IS NOT NULL)::int = 1
  )
);

-- LỚP ADMIN (bảng phụ thuộc admin_account)

CREATE TABLE audit_log (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_id     UUID NOT NULL REFERENCES admin_account(id),
  action       TEXT NOT NULL, -- publish_story, upload_model_asset, withdraw_document...
  target_type  TEXT NOT NULL,
  target_id    UUID NOT NULL,
  detail       JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LỚP CHATBOT

CREATE TABLE chat_session (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ip_hash     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_message (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id          UUID NOT NULL REFERENCES chat_session(id),
  role                VARCHAR NOT NULL, -- user | assistant
  content             TEXT NOT NULL,
  citations           JSONB NOT NULL DEFAULT '[]', -- projection phục vụ API; bảng evidence là nguồn thật
  response_status     VARCHAR, -- answered | clarify | abstained; NULL cho user message
  abstained           BOOLEAN NOT NULL DEFAULT false,
  retrieval_strategy  VARCHAR, -- bm25_ngram_graph | bm25_only
  latency_ms          INT,
  model               TEXT,
  corpus_version      INT REFERENCES corpus_release(version),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_chat_message_role CHECK (role IN ('user', 'assistant')),
  CONSTRAINT chk_chat_message_citations_array CHECK (jsonb_typeof(citations) = 'array'),
  CONSTRAINT chk_chat_message_response CHECK (
    (role = 'user' AND response_status IS NULL AND abstained = false)
    OR (
      role = 'assistant'
      AND response_status IN ('answered', 'clarify', 'abstained')
      AND abstained = (response_status = 'abstained')
      AND (response_status <> 'answered' OR jsonb_array_length(citations) > 0)
    )
  )
);

CREATE TABLE chat_message_evidence (
  message_id       UUID NOT NULL REFERENCES chat_message(id) ON DELETE CASCADE,
  passage_id       UUID NOT NULL,
  corpus_version   INT NOT NULL REFERENCES corpus_release(version),
  citation_label   TEXT NOT NULL, -- ví dụ P17, do backend cấp trước khi gọi model
  evidence_type    VARCHAR NOT NULL,
  retrieval_score  REAL,
  reason           TEXT,
  PRIMARY KEY (message_id, passage_id),
  CONSTRAINT uq_chat_message_citation_label UNIQUE (message_id, citation_label),
  CONSTRAINT fk_chat_evidence_passage FOREIGN KEY (passage_id, corpus_version)
    REFERENCES passage(id, corpus_version),
  CONSTRAINT chk_chat_evidence_score CHECK (
    retrieval_score IS NULL OR retrieval_score BETWEEN 0 AND 1
  )
);

CREATE FUNCTION enforce_chat_answer_evidence() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
  target_message_id UUID;
BEGIN
  IF TG_TABLE_NAME = 'chat_message_evidence' THEN
    target_message_id := OLD.message_id;
  ELSE
    target_message_id := NEW.id;
  END IF;

  IF EXISTS (
    SELECT 1
      FROM chat_message
     WHERE id = target_message_id
       AND role = 'assistant'
       AND response_status = 'answered'
  ) AND NOT EXISTS (
    SELECT 1 FROM chat_message_evidence WHERE message_id = target_message_id
  ) THEN
    RAISE EXCEPTION 'answered chat message % requires at least one evidence passage', target_message_id
      USING ERRCODE = '23514';
  END IF;

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_chat_answer_requires_evidence
AFTER INSERT OR UPDATE ON chat_message
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION enforce_chat_answer_evidence();

CREATE CONSTRAINT TRIGGER trg_chat_evidence_cannot_orphan_answer
AFTER DELETE OR UPDATE ON chat_message_evidence
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION enforce_chat_answer_evidence();

CREATE TABLE chat_feedback (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id  UUID NOT NULL REFERENCES chat_message(id),
  rating      INT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_chat_feedback_rating CHECK (rating IN (-1, 1))
);

COMMIT;
