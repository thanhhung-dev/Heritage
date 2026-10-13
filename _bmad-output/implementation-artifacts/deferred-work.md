- source_spec: `_bmad-output/implementation-artifacts/spec-active-stop-nav.md`
  summary: Chuẩn hóa hoặc từ chối scene key không canonical như s01 để resolver, nav và điều hướng dùng cùng key.
  evidence: Browser tại /content/son-tra-peninsula/s01 hiển thị Hồ Lưu Khiêm nhưng có 0 aria-selected=true; resolver parse số còn viewer so chuỗi chính xác. Lỗi đã có trước thay đổi class active; cần quyết định contract route riêng.
- source_spec: `_bmad-output/implementation-artifacts/spec-camera-audio-sync.md`
  summary: Reset phiên narration theo scene khi nhiều cảnh dùng chung URL audio.
  evidence: useNarration chỉ reset theo URL, nên giữ duration/currentTime giữa hai cảnh dùng chung URL trước khi seeked cập nhật state. Lỗi đã có trước bản sửa camera; tour Tapestry hiện dùng URL riêng từng cảnh. Cần thêm định danh phiên khi tích hợp nguồn dữ liệu dùng chung URL.
