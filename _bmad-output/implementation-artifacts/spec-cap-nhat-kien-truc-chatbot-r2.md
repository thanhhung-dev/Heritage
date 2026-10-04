---
title: 'Cập nhật kiến trúc chatbot dùng R2 làm kho tri thức'
type: 'chore'
created: '2026-10-04'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `docs/chatbot.md` đang xác định PostgreSQL là nguồn sự thật duy nhất và chưa mô tả cách tổ chức kho tri thức trên Cloudflare R2, mapping object key, quy trình biên soạn nhiều nguồn hoặc lộ trình chuyển đổi.

**Approach:** Viết lại kiến trúc để R2 giữ dữ liệu gốc/biên soạn/đã xử lý, tầng search giữ index và mapping phục vụ truy hồi, PostgreSQL giữ dữ liệu nghiệp vụ/cache; bổ sung roadmap triển khai tăng dần từ một địa điểm pilot đến search service có thể mở rộng.

</frozen-after-approval>

## Implementation Notes

- Viết lại `docs/chatbot.md` theo ranh giới R2/search index/PostgreSQL và đánh dấu rõ hiện trạng so với kiến trúc đích.
- Giữ các phần Query Planner, provenance, Evidence Context Builder và grounding phù hợp từ kiến trúc cũ.
- Bổ sung cây object key cho Chùa Thiên Mụ, contract document/passage, pipeline publish theo version, failure modes và roadmap 7 giai đoạn có gate.
- Không thay đổi `schema.sql` hoặc các file code đang có chỉnh sửa ngoài phạm vi.
- Sau review, bổ sung passage-level object mapping, immutable release descriptor/index, request snapshot, provenance cho mọi operator và gate định lượng.

## Review Triage Log

- `medium` — Passage chỉ trỏ source document nên runtime không fetch đúng chunk; đã tách `source_object_key` và `passage_object_key`, kèm phương án shard byte range.
- `high` — Mô tả publish “nguyên tử” qua R2/search/PostgreSQL là sai; đã thay bằng immutable artifacts + PostgreSQL CAS active-release pointer và rollback bằng descriptor cũ.
- `medium` — Request có thể trộn phiên bản khi publish đồng thời; đã ghim một release descriptor và immutable index build cho toàn bộ request.
- `medium` — Exact/graph/timeline chưa đi qua evidence contract; đã bắt buộc supporting passage và hợp nhất qua Context Builder.
- `medium` — Manifest thiếu dữ liệu verify/rebuild; đã thêm object checksum/size, processing digest, index build, lexical config và yêu cầu JSON Schema version hóa.
- `medium` — Idempotency key có thể nhập nhằng source/config; đã tách source identity khỏi processing-config digest đầy đủ.
- `high` — Lifecycle có thể xóa raw input và phá khả năng rebuild; đã giới hạn expiry vào staging/cache/unreferenced release đã archive.
- `high` — Runtime có thể serve curated narrative trước provenance; đã chuyển provenance tối thiểu vào Giai đoạn 2 trước cutover.
- `medium` — Roadmap gate chưa đo được; đã thêm recall@1, citation coverage, p95, checksum, release consistency và rollback criteria.
- `medium` — Giai đoạn 1 tạo processed trước pipeline ổn định; đã giới hạn Giai đoạn 1 ở raw/curated và chuyển processed sang Giai đoạn 2.
