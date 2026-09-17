---
title: 'Bổ sung Recommendation Service và logo công nghệ vào sơ đồ kiến trúc'
type: 'feature'
created: '2026-09-17'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Sơ đồ kiến trúc HeritageGraph chưa thể hiện Recommendation Service và đang trình bày các công nghệ chủ yếu bằng chữ, nên thiếu một capability quan trọng của đề tài và khó nhận diện nhanh stack triển khai.

**Approach:** Cập nhật riêng file Excalidraw, thêm Recommendation Service sử dụng NetworkX cùng hồ sơ sở thích/lịch sử tương tác, đồng thời bổ sung logo cho các công nghệ chính như Jenkins nhưng giữ nhãn ngắn để sơ đồ vẫn rõ nghĩa.

</frozen-after-approval>

## Implementation Notes

- Cập nhật `kientruc-recsys-agent-platform.excalidraw`: thêm Recommendation Service, `/api/recommend` trong FastAPI, luồng NetworkX, hồ sơ sở thích/tương tác PostgreSQL, fallback graph-only và recommendation metrics.
- Nhúng trực tiếp logo PNG cho Vercel, Cloudflare, FastAPI, GitHub, Jenkins và Docker; giữ nhãn chức năng cạnh logo để sơ đồ vẫn đọc được và không phụ thuộc mạng.
- Logo lấy từ Simple Icons/CDN chính thức, chuyển thành PNG 32 px và nhúng bằng data URL. Không thêm file asset rời.
- Kiểm tra JSON, tham chiếu image/file, text/originalText, arrow bindings và `git diff --check` đều hợp lệ.
- Render bằng `@moona3k/excalidraw-export` tại scale 1; ảnh cuối 2530×1703. Kiểm tra trực quan xác nhận không còn logo che chữ hoặc nội dung bị cắt.

## Review Triage Log

- `medium` — Thiếu nguồn profile/history: đã thêm `Interest profile + interactions` với PostgreSQL và views/clicks/saves.
- `medium` — Chưa thể hiện đường trả recommendation: đã ghi rõ `/api/recommend` tại API và bên trong FastAPI Recommendation Service.
- `medium` — Mũi tên KG chưa binding: đã binding hai đầu với Deterministic KG và Recommendation Service.
- `medium` — API chưa có route: đã thêm `GET /api/recommend`; request/response chi tiết không thuộc mức sơ đồ tổng quan.
- `low` — Công thức graph affinity chưa chi tiết: từ chối mở rộng vì không phù hợp mức kiến trúc hệ thống.
- `medium` — Thiếu cold start: đã thêm `anonymous: graph-only`.
- `medium` — Thiếu nguồn interaction: đã thêm profile/interactions store cùng các tín hiệu views/clicks/saves.
- `low` — Thiếu recommendation evaluation: đã mở rộng khối metrics để bao gồm recommendation.
- `false` — Chưa có Jenkinsfile: Jenkins là quyết định CI tương lai đã được người dùng yêu cầu thể hiện trong kiến trúc đích.
- `medium` — Chưa rõ deployment boundary: đã ghi Recommendation Service chạy bên trong FastAPI, nên dùng cùng DEV/PROD runtime hiện có.
- `medium` — Implementation Notes trống: đã bổ sung thay đổi và bằng chứng kiểm tra.
- `false` — Spec thiếu acceptance/verification sections: route `oneshot` chủ ý dùng spec tối giản theo workflow; verification được ghi tại Implementation Notes.
- `false` — `context: []`: thay đổi chỉ cần file sơ đồ và source/research đã được kiểm tra trực tiếp, không cần nạp context toàn dự án.
- `low` — Bộ logo chưa được liệt kê: đã ghi rõ sáu logo được nhúng trong Implementation Notes.
- `low` — Provenance/accessibility: đã ghi nguồn logo; nhãn chữ cạnh logo được giữ lại để không truyền nghĩa chỉ bằng hình ảnh.
