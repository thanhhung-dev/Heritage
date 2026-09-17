---
title: 'Hoàn thiện knowledge schema cho chatbot HeritageGraph'
type: 'feature'
created: '2026-09-17'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `schema.sql` mới chỉ có phần lõi entity/relation và chưa chứa các bảng claim, timeline, narrative cùng provenance cần cho kiến trúc GraphRAG/KAG-lite trong `docs/chatbot.md`.

**Approach:** Hoàn thiện trực tiếp lớp tri thức trong `schema.sql`, chuẩn hóa metadata nguồn và entity, bổ sung các projection truy vấn cùng bảng evidence ở mức passage, constraint và index cần thiết; không thay đổi code runtime hay migration hiện có.

</frozen-after-approval>

## Implementation Notes

- Hoàn thiện `document` như nguồn metadata chung (`source_url`, `source_type`, `tier`, `observed_at`, hash, license) và giữ passage là đơn vị retrieval/citation.
- Mở rộng entity/alias/place profile với canonical identity, scope/depth/status, Wiki identifiers, review metadata và evidence bắt buộc; loại bỏ mảng alias trùng nguồn thật.
- Bổ sung claim field schema, kiểm tra kiểu giá trị, canonical claim theo corpus; timeline, participant; predicate/relation; narrative; cùng evidence nhiều nguồn ở mức passage.
- Bổ sung registry/publish lifecycle cho corpus, khóa ngoại chống trộn evidence giữa các corpus version, BM25/trigram/vector index và primary passage bắt buộc.
- Bổ sung ba trạng thái chatbot `answered | clarify | abstained` và `chat_message_evidence`; answered phải có citation projection và evidence package trước khi commit.
- Không đổi tên `document` thành `source_doc` vì repository hiện dùng `document`, còn `docs/chatbot.md` đã ghi đây là ánh xạ tương đương.
- Không sửa SQLAlchemy models/Alembic migration vì yêu cầu hiện tại chỉ hoàn thiện file thiết kế `schema.sql`.
- Kiểm tra fresh schema trên PostgreSQL tạm thành công với 35 bảng (thay `VECTOR` bằng mảng khi test vì PostgreSQL local chưa cài pgvector). Các scenario sai kiểu claim, evidence khác corpus version và answered thiếu evidence đều bị từ chối; clarify không citation được chấp nhận.

## Review Triage Log

- `false` — `document` khác tên `source_doc`: tài liệu đã ánh xạ rõ và code hiện dùng `document`; đổi tên riêng schema sẽ tạo bất nhất.
- `medium` — thiếu lifecycle corpus: đã thêm `corpus_release` và FK từ passage/knowledge/chat.
- `medium` — knowledge có thể thiếu evidence: đã thêm primary passage bắt buộc và giữ bảng evidence cho nguồn bổ sung.
- `medium` — có thể trộn corpus version: đã thêm composite FK `(record/passage id, corpus_version)`.
- `medium` — `claim.value` không theo `value_type`: đã thêm trigger kiểm tra JSONB type và default unit.
- `medium` — canonical claim không version hóa: đã thêm `corpus_version` vào partial unique index.
- `medium` — relation triple không version hóa: đã thêm `corpus_version` vào unique key.
- `medium` — passage thiếu dense vector: đã thêm embedding và HNSW cosine index.
- `medium` — event chỉ có actor/artifact: đã thêm participant theo role tổng quát, vẫn giữ hai cột tiện dụng người dùng yêu cầu.
- `medium` — chat không biểu diễn `clarify`: đã thêm `response_status` và constraint trạng thái/citation.
- `medium` — citation JSON không có provenance: đã thêm `chat_message_evidence` và deferred constraint ngăn answered không có evidence.
