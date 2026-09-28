---
title: 'Loại bỏ importer corpus cũ khỏi Docker Compose'
type: 'bugfix'
created: '2026-09-28'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Docker Compose vẫn chạy `apps.backend.db.import_corpus`, phụ thuộc các artifact crawl `locations_index.json` và `wiki_by_location` không còn thuộc luồng dữ liệu mới, khiến stack dừng ở service `import-data`.

**Approach:** Loại service import corpus cũ khỏi chuỗi khởi động local và cho backend chờ migration hoàn tất trực tiếp. Không crawl, không giả lập import thành công và không sửa `schema.sql` đang có thay đổi của người dùng.

</frozen-after-approval>

## Implementation Notes

- Đã xóa service `import-data` khỏi `docker-compose.yml`; backend chờ trực tiếp `migrate` hoàn tất.
- Đã bỏ điều kiện artifact crawl khỏi `/api/health`, vì dữ liệu mới được quản lý trong PostgreSQL.
- Đã cập nhật và chạy unit test health; `docker compose config` không còn tham chiếu `import-data`, `import_corpus` hay `locations_index`.
- Đã dừng crawler chạy nhầm, xóa artifact crawl dở và xóa riêng container `heritagegraph-import-data-1`; không xóa database volume.

## Review Triage Log

- `medium` — test cấu hình Docker vẫn yêu cầu service `import-data`; đã cập nhật để xác nhận service bị loại và backend chờ `migrate`.
- `medium` — README vẫn hướng dẫn chạy importer cũ và mô tả `corpus_ready`; đã đồng bộ hướng dẫn và response health.
- `medium` — tài liệu Docker local vẫn mô tả/log service importer cũ; đã cập nhật theo chuỗi `migrate → backend`.
