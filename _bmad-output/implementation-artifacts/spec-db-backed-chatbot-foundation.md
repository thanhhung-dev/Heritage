---
title: 'Nền tảng chatbot truy xuất PostgreSQL Schema v2'
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '11a7e1a5b92577c93976c52b0094bd4a09bb2811'
context:
  - 'docs/chatbot.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Compose đã bỏ importer corpus cũ nhưng chatbot, ORM và Alembic vẫn phụ thuộc hoặc phản ánh kiến trúc file-corpus cũ; `schema.sql` Schema v2 chưa trở thành contract chạy được. Vì vậy stack mới chưa có đường nhập dữ liệu có provenance và chat vẫn không thể tìm passage trong PostgreSQL.

**Approach:** Xây một vertical slice Schema v2 không phá dữ liệu: structured package → document/passage/entity/alias/evidence trong PostgreSQL → entity resolution và lexical retrieval → context/citation cho chat. Slice chạy và kiểm thử retrieval không cần GGUF; generation chỉ chạy khi có evidence và model sẵn sàng.

## Boundaries & Constraints

**Always:** Giữ `schema.sql` hiện tại làm định hướng contract; migration chỉ expand/backfill, không reset volume hoặc drop cấu trúc đang dùng; citation trỏ tới passage và document thật; importer có ID ổn định, transaction và idempotency; API giữ response hiện tại; runtime retrieval chỉ đọc PostgreSQL.

**Never:** Không nối lại importer/corpus crawl cũ; không import fixture vào production; không làm claim/timeline/relation/narrative planner, vector retrieval, web search hoặc training; không áp migration lên volume hiện tại khi chưa được phê duyệt.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Import chuẩn/lặp | Structured JSON hợp lệ chạy một hoặc nhiều lần | Upsert đúng một knowledge package | Commit nguyên transaction |
| Import sai provenance | Span/reference/quote sai | Không ghi bản ghi nào | Báo field lỗi |
| Retrieval có bằng chứng | Query khớp entity, alias hoặc passage | Trả evidence xếp hạng có passage UUID, title, URL, quote | Không gọi LLM trong test model-free |
| Retrieval thiếu bằng chứng | Query không khớp hoặc nguồn đã withdrawn | Trả `insufficient_evidence` | Không cho model tự đoán |
| Database lỗi | DB không truy cập được | Trả `unavailable` có kiểm soát | Không fallback corpus file |

</frozen-after-approval>

## Code Map

- `schema.sql` -- contract v2; sửa lỗi cú pháp, không dùng để reset DB.
- `docker-compose.yml`, requirements, migrations -- pgvector image/type và revision expand sau `d0f4a2c81e7b`.
- `apps/backend/models/kg.py` -- ORM cho document, corpus release, passage, entity, alias và evidence.
- `apps/backend/db/import_structured.py` -- validator/importer mới, độc lập `core.corpus`.
- `apps/backend/services/kg.py` -- entity resolution, lexical passage search và evidence DTO.
- `apps/backend/api/chat.py` -- DB evidence thay file fallback, generation chỉ khi có evidence.
- `apps/backend/tests/`, runtime docs -- fixture và kiểm thử/lệnh vận hành mới.

## Tasks & Acceptance

**Execution:**
- [x] Nền tảng DB -- pgvector image/type, ORM và migration expand không phá dữ liệu.
- [x] Structured importer -- validate/upsert package provenance trong một transaction.
- [x] Retrieval service -- PostgreSQL FTS + trigram, lọc version/source và trả evidence chuẩn.
- [x] Chat orchestration -- DB retrieval thay corpus file, fail closed khi thiếu evidence.
- [x] Tests/docs -- chứng minh migration, import, retrieval và chat model-free.

**Acceptance Criteria:**
- Given DB ở Alembic head, when upgrade, then vertical slice tồn tại và cấu trúc hiện hành không bị drop.
- Given package hợp lệ, when import hai lần, then không nhân bản và mọi nguồn hợp lệ.
- Given query có dấu, không dấu hoặc alias, when retrieval chạy, then trả passage UUID, quote, title và URL từ PostgreSQL.
- Given không có evidence hoặc DB lỗi, when gọi `/api/chat`, then response từ chối có kiểm soát và `generate_response` không được gọi.
- Given không có thư mục corpus và không có GGUF, when chạy test importer/retrieval/chat model-free, then toàn bộ targeted suite pass.

## Implementation Notes

- Thêm revision expand `e741c8a4190f` sau `d0f4a2c81e7b`; downgrade cố ý không drop dữ liệu.
- Importer dùng UUIDv5 theo natural key, xác minh span/quote/reference trước khi ghi và upsert toàn package trong transaction của caller.
- Retrieval dùng PostgreSQL FTS + `pg_trgm`/`unaccent`, chỉ đọc release published và nguồn chưa withdrawn; chat không còn chạy file retrieval trên đường runtime.
- Integration đã chạy trên container `pgvector/pgvector:pg16` cô lập: upgrade head lặp, import hai lần giữ số lượng 1/1/1/1 và alias trả đúng passage citation.

## Spec Change Log

## Review Triage Log

## Design Notes

Migration expand thay vì ép ORM khớp toàn bộ `schema.sql` trong một revision. Các bảng nâng cao và contract 3D xung đột được hoãn. PostgreSQL FTS không được gọi là BM25; trigram xử lý alias/lỗi gõ, vector chưa tham gia ranking.

## Verification

**Commands:**
- `POSTGRES_PASSWORD=test-password docker compose config --quiet` -- Compose hợp lệ và không có service importer legacy.
- `python -m unittest apps.backend.tests.test_docker_database apps.backend.tests.test_migration_bootstrap` -- contract image/migration pass.
- `python -m unittest apps.backend.tests.test_structured_import apps.backend.tests.test_db_retrieval apps.backend.tests.test_db_chat` -- validation, idempotency, evidence và model-free chat pass.
- Chạy migration/import/retrieval integration trên PostgreSQL test cô lập -- extensions có đủ, upgrade lặp an toàn, query trả citation đúng.
