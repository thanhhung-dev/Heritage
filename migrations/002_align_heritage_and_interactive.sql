-- Migration: Align the tour tables with the ORM (models/ + schema.sql)
-- Date: 2026-10-24
-- Applied to: heritagegraph @ heritage-db.c1q6g24um7wr.ap-southeast-1.rds.amazonaws.com
--
-- Bối cảnh: DB đã được chuẩn hoá đa ngôn ngữ (bảng heritage_translation) trong khi
-- ORM `apps/backend/models/heritage.py` vẫn đọc các cột phẳng trên `heritage`.
-- Hậu quả: GET /api/heritages và GET /api/heritages/{slug} trả 500
-- (42703 column "title" does not exist) nên tour không load được content/audio.
--
-- Migration này đưa DB về đúng shape mà code + schema.sql + frontend mong đợi.
-- Additive, nullable (trừ community_made có default) — không xoá dữ liệu.

-- 1) Bảng interactive thiếu 2 cột mà ORM đã khai báo.
ALTER TABLE interactive
    ADD COLUMN IF NOT EXISTS explore_title TEXT,
    ADD COLUMN IF NOT EXISTS explore_description TEXT;

-- 2) heritage thiếu toàn bộ cột nội dung + ngôn ngữ.
ALTER TABLE heritage
    ADD COLUMN IF NOT EXISTS title TEXT,
    ADD COLUMN IF NOT EXISTS tagline TEXT,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS headline TEXT,
    ADD COLUMN IF NOT EXISTS community_made BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS presented_by_logo_url TEXT,
    ADD COLUMN IF NOT EXISTS language1_id BIGINT REFERENCES language(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS language2_id BIGINT REFERENCES language(id) ON DELETE SET NULL;

-- 3) Backfill từ heritage_translation: ngôn ngữ nguồn = vi (id 2), thứ hai = en (id 1).
--    Chạy lại nhiều lần vẫn idempotent vì chỉ điền khi cột còn NULL.
UPDATE heritage h
SET title = COALESCE(h.title, vi.title, en.title),
    tagline = COALESCE(h.tagline, vi.tagline, en.tagline),
    description = COALESCE(h.description, vi.description, en.description),
    headline = COALESCE(h.headline, vi.headline, en.headline),
    language1_id = COALESCE(h.language1_id, vi.language_id, en.language_id),
    language2_id = COALESCE(h.language2_id, en.language_id)
FROM (SELECT * FROM heritage_translation WHERE language_id = 2) vi
FULL OUTER JOIN (SELECT * FROM heritage_translation WHERE language_id = 1) en
    ON vi.heritage_id = en.heritage_id
WHERE h.id = COALESCE(vi.heritage_id, en.heritage_id);

-- 4) title phải có giá trị (schema.sql: TEXT NOT NULL).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM heritage WHERE title IS NULL) THEN
        ALTER TABLE heritage ALTER COLUMN title SET NOT NULL;
    ELSE
        RAISE NOTICE 'Bỏ qua SET NOT NULL: vẫn còn heritage chưa có title';
    END IF;
END $$;

COMMENT ON COLUMN heritage.title IS 'Tiêu đề ngôn ngữ nguồn (backfill từ heritage_translation)';
COMMENT ON COLUMN heritage.language1_id IS 'Ngôn ngữ nguồn của bản dịch phẳng';
COMMENT ON COLUMN heritage.language2_id IS 'Ngôn ngữ thứ hai của bản dịch phẳng';
