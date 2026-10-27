-- Thêm cột quỹ đạo camera dạng GLB (chỉ camera + animation clip, không mesh).
--
-- Áp dụng cho DB đã tồn tại (schema.sql chỉ dùng khi tạo mới):
--   psql "$DATABASE_URL" -f apps/backend/migrations/2026-10-26_scene_camera_path_url.sql
--
-- Idempotent: chạy lại nhiều lần không lỗi.

ALTER TABLE scene
    ADD COLUMN IF NOT EXISTS camera_path_url TEXT;

COMMENT ON COLUMN scene.camera_path_url IS
    'URL GLB chỉ chứa camera + animation clip (không mesh). Có giá trị thì quỹ đạo '
    'camera của cảnh do clip quyết định và được seek theo thời gian audio.';
