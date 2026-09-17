-- ============================================================
-- Cultural Memory GraphRAG + 3D Virtual Tour — Schema v2
-- SQL dump (PostgreSQL) sinh từ file DBML
-- Thứ tự tạo bảng đã sắp theo phụ thuộc khoá ngoại (FK)
-- ============================================================

BEGIN;

-- ---------- EXTENSIONS ----------
-- gen_random_uuid() có sẵn từ PostgreSQL 13+; nếu bản cũ hơn cần pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- pgvector CHƯA cài trên máy local (thiếu vector.control) và project hiện
-- cũng chưa dùng vector search (retriever đang chạy BM25 + KG rerank).
-- Khi nào cần similarity search thật, cài pgvector rồi bật dòng dưới:
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ---------- ENUM ----------
CREATE TYPE predicate_type AS ENUM (
  'THỜ',
  'XÂY_NĂM',
  'THUỘC  _LÀNG',
  'THUỘC_VÙNG',
  'LÀ_LOẠI',
  'LIÊN_QUAN'
);

-- ============================================================
-- LỚP ADMIN (không phụ thuộc bảng khác)
-- ============================================================

CREATE TABLE admin_account (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username            TEXT NOT NULL UNIQUE,
  password_hash       TEXT NOT NULL, -- argon2id
  session_token_hash  TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- LỚP TRI THỨC (KG)
-- ============================================================

CREATE TABLE document (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title        TEXT NOT NULL,
  region       VARCHAR NOT NULL, -- 'hue' | 'da_nang'
  source_url   TEXT,
  raw_text     TEXT NOT NULL, -- toàn văn gốc, dùng để re-chunk
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE passage (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id    UUID NOT NULL REFERENCES document(id),
  text           TEXT NOT NULL, -- BẤT BIẾN - không UPDATE
  char_start     INT NOT NULL,
  char_end       INT NOT NULL,
  corpus_version INT NOT NULL DEFAULT 1,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE entity (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                 TEXT NOT NULL,
  type                 TEXT NOT NULL, -- person | place | event | artifact
  aliases              TEXT[],
  embedding            FLOAT8[], -- TẠM: chưa cài pgvector. Khi cài xong đổi lại
                                  -- thành VECTOR(1024) bằng ALTER TABLE để có index ANN.
  source_document_id   UUID REFERENCES document(id),
  source_passage_id    UUID REFERENCES passage(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_entity_type CHECK (type IN ('person', 'place', 'event', 'artifact'))
);

CREATE INDEX idx_entity_name ON entity (name);

-- Tên thay thế được chuẩn hóa riêng để hỗ trợ entity resolution.
-- Ví dụ: "lăng an định" -> entity chuẩn "Cung An Định".
CREATE TABLE entity_alias (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id            UUID NOT NULL REFERENCES entity(id),
  alias                TEXT NOT NULL,
  normalized_alias     TEXT NOT NULL,
  alias_type           VARCHAR NOT NULL, -- official | historical | common | typo
  confidence           NUMERIC(4,3) NOT NULL DEFAULT 1.0,
  source_document_id   UUID REFERENCES document(id),
  source_passage_id    UUID REFERENCES passage(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_entity_alias_confidence CHECK (confidence BETWEEN 0 AND 1),
  CONSTRAINT uq_entity_alias_normalized UNIQUE (normalized_alias),
  CONSTRAINT uq_entity_alias_entity_alias UNIQUE (entity_id, alias)
);

CREATE TABLE relation (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id           UUID NOT NULL REFERENCES entity(id),
  predicate            predicate_type NOT NULL,
  object_id            UUID NOT NULL REFERENCES entity(id),
  source_document_id   UUID REFERENCES document(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_relation_triple UNIQUE (subject_id, predicate, object_id)
);

-- ============================================================
-- LỚP NỘI DUNG 3D (CMG)
-- ============================================================

-- site: 1 công trình/di tích thực tế (vd: An Định Palace)
CREATE TABLE site (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                 TEXT NOT NULL,
  region               VARCHAR NOT NULL, -- 'hue' | 'da_nang'
  entity_id            UUID NOT NULL REFERENCES entity(id), -- liên kết site với entity trong KG
  description          TEXT,
  source_document_id   UUID REFERENCES document(id),
  source_passage_id    UUID REFERENCES passage(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- scene: 1 khu vực/phòng cụ thể trong site — chỉ lưu metadata,
-- file 3D thật nằm ở object storage/CDN (xem model_asset).
CREATE TABLE scene (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id         UUID NOT NULL REFERENCES site(id),
  name            TEXT NOT NULL, -- vd: "Tầng 1 - Sảnh chính"
  transform_7dof  JSONB NOT NULL, -- translate+rotate(quat)+scale để căn trục
  order_index     INT, -- thứ tự khu vực trong site, dùng cho điều hướng
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- model_asset: mỗi scene có thể có nhiều bản .glb khác độ chi tiết (LOD)
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

-- raw_asset: ghi lại nguồn dữ liệu gốc (Tầng 1 - RAW) để truy vết/tái xử lý,
-- KHÔNG serve cho web, chỉ lưu path nội bộ hoặc ghi chú lưu trữ ngoài.
CREATE TABLE raw_asset (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scene_id         UUID NOT NULL REFERENCES scene(id),
  capture_method   VARCHAR NOT NULL, -- photogrammetry | gaussian_splat_source | drone_video
  storage_location TEXT NOT NULL, -- path local/external SSD, không public
  captured_at      TIMESTAMPTZ,
  notes            TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
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

-- ============================================================
-- LỚP ADMIN (bảng phụ thuộc admin_account)
-- ============================================================

CREATE TABLE audit_log (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_id     UUID NOT NULL REFERENCES admin_account(id),
  action       TEXT NOT NULL, -- publish_story, upload_model_asset, withdraw_document...
  target_type  TEXT NOT NULL,
  target_id    UUID NOT NULL,
  detail       JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- LỚP CHATBOT
-- ============================================================

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
  citations           JSONB NOT NULL DEFAULT '[]',
  abstained           BOOLEAN NOT NULL DEFAULT false,
  retrieval_strategy  VARCHAR, -- bm25_ngram_graph | bm25_only
  latency_ms          INT,
  model               TEXT,
  corpus_version      INT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_chat_message_role CHECK (role IN ('user', 'assistant')),
  CONSTRAINT chk_chat_message_citations CHECK (
    role = 'user' OR abstained = true OR jsonb_array_length(citations) > 0
  )
);

CREATE TABLE chat_feedback (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id  UUID NOT NULL REFERENCES chat_message(id),
  rating      INT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_chat_feedback_rating CHECK (rating IN (-1, 1))
);

COMMIT;