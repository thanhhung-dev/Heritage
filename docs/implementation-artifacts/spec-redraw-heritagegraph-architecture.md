---
title: 'Vẽ lại sơ đồ kiến trúc HeritageGraph theo bốn miền đã chốt'
type: 'feature'
created: '2026-09-17'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Sơ đồ hiện tại chưa phản ánh các quyết định mới nhất về Hybrid Retrieval, bốn service trong API Serving, pipeline Jenkins và các nhánh observability nên không còn phù hợp để trình bày kiến trúc đã chốt.

**Approach:** Vẽ lại duy nhất file Excalidraw thành bốn miền rõ ràng: Heritage Dataflow, Application & API Serving, Jenkins CI/CD và Analytics & Observability; giữ phong cách dễ đọc của ảnh `overview.png`, logo công nghệ và các boundary DEV/PROD/media đã thống nhất.

</frozen-after-approval>

## Implementation Notes

- Vẽ lại `kientruc-recsys-agent-platform.excalidraw` thành bốn miền kiến trúc với 145 phần tử đang hoạt động và sáu logo nhúng.
- Dataflow dùng Hybrid Retrieval: BM25, embeddings/pgvector và NetworkX; API Serving dùng một FastAPI container với Chat, Recommendation và Graph Service.
- Jenkins thể hiện đầy đủ detect/test/build/smoke/DEV/k6/approval/PROD; observability tách Prometheus, Loki, Langfuse, Grafana và Quality Analytics theo đúng vai trò.
- Render cuối tại `/private/tmp/heritagegraph-architecture-final-redraw-v2.png`; kiểm tra trực quan xác nhận toàn bộ border nằm trong canvas, không có chữ tràn, logo méo hoặc connector cắt node.
- Kiểm tra JSON, ID, `text == originalText`, binding, image file reference và `git diff --check` đều hợp lệ.

## Review Triage Log

- `false` — Blind review báo lỗi enum trong `schema.sql`; file này đã bẩn trước yêu cầu và không thuộc thay đổi vẽ lại sơ đồ.
- `false` — Blind review báo các mâu thuẫn/phụ thuộc trong `docs/planning-artifacts/epics.md`; file này không được thay đổi bởi công việc hiện tại.
- `false` — Blind review báo chênh lệch schema/provenance/citation trong `docs/chatbot.md`; file này không được thay đổi bởi công việc hiện tại.
- `false` — Blind review báo model và trạng thái triển khai trong `docs/heritagegraph-architecture-presentation.md`; file này không được thay đổi bởi công việc hiện tại.
- `false` — Kiểm tra ảnh tự động ban đầu nghi phần bên phải bị clipping; kiểm tra trực tiếp ảnh 5160×3252 xác nhận border của Artifacts, Observability và Jenkins đều hiển thị đầy đủ với khoảng trắng ngoài canvas.
