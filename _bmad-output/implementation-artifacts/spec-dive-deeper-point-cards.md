---
title: 'Ô điểm Dive Deeper có thumbnail'
type: 'feature'
created: '2026-10-13'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Đổi danh sách nút chữ của điểm Dive Deeper thành ô có thumbnail, tên điểm và trạng thái đang chọn. Ảnh/thứ tự lấy từ dữ liệu nguồn; thiếu ảnh vẫn chọn được điểm. Giữ điều kiện hiện sau narration, camera transition, popup và keyboard/Reset/Exit. Không đổi môi trường render, shader lens, loại media popup hay thêm canvas riêng.

</frozen-after-approval>

## Implementation Notes

- Bổ sung thumb_url tùy chọn vào HeritageInteractiveHighlight để không phá payload backend cũ. Extractor ánh xạ highlight_thumbnail sang thumb_url; tạo lại tour.json bằng script sẵn có, kiểm tra diff chỉ thêm thumbnail.
- ExploreControls giữ panel góc hiện có, chuyển nút sang tile ảnh bên trái/tên bên phải và sort theo sort_order; highlight đang chọn có viền/nền cam, aria-pressed giữ nguyên. Ảnh trang trí alt rỗng; missing thumbnail dùng lens icon.
- Giữ palette tối/cam và kích thước panel hiện có, không thêm carousel/framework. Kiểm tra desktop/mobile, chọn/đóng, bàn phím, thiếu thumbnail, source order và popup màn hình thấp.
- HTML nguồn untracked được giữ nguyên, không stage; không push. Phạm vi nhỏ, không có câu hỏi sản phẩm chưa giải quyết hoặc hành động không thể đảo ngược.
- RED cho ảnh lỗi: browser dùng GLB/audio thật, thumbnail 404 không thay bằng lens icon; assertion thất bại tại point-cards-image-red.log. Các scenario trước đó (thumbnail nguồn, selected, camera, keyboard, width/scroll, null thumbnail, order đảo và một điểm) đã thực thi đạt trong cùng lượt.
- GREEN: fallback lưu URL lỗi theo ID; đổi URL sẽ thử tải ảnh mới, không bị trạng thái lỗi cũ giữ lại. Browser kiểm tra cả 404 và phục hồi URL nguồn đạt.
- 17 test frontend, lint và TypeScript đạt; lint có 4 cảnh báo img có sẵn. Script tạo JSON chạy lại chỉ thêm 10 thumb_url, không đổi camera, media, environment hoặc thứ tự dữ liệu.
- Chrome với GLB/audio thật đạt: thumb URL/ảnh nguồn tải được, tên/order, viền/nền selected, chọn bằng Enter và Escape trả focus, camera khớp JSON; widths 320/390/640/641/900/1440 không tràn. Viewport 390×400 cuộn panel được và popup giữ focus. Source array đảo + order 30/10/20 vẫn chọn đúng ID/camera, missing/404 ảnh có icon, đổi URL phục hồi, scene một điểm hoạt động.
- Đã inspect ảnh desktop/mobile default/selected và fallback bằng view_media. Bằng chứng `.amp/in/artifacts/point-cards-*.png`, `point-cards-validation.log`, `point-cards-image-red.log`. Clipping attribution/model và giới hạn môi trường render có sẵn không thuộc sửa UI điểm này.

## Review Triage Log

- 1 — medium, patch: URL có giá trị nhưng 404 không có fallback. Browser RED xác nhận; onError chuyển sang lens icon, lỗi gắn với URL theo ID nên URL mới phục hồi được; browser GREEN.
- 2 — low, reject: test được giữ chỉ bao phủ extractor, chưa có test rendered-controls. Browser đã thực thi multi-point/order đảo, ảnh nguồn/null/404, callback ID bằng popup title + camera pose, keyboard/selected và responsive. Không thêm framework UI riêng hoặc giữ test dùng React inspector/CDN thiếu ổn định; contract thumbnail extractor đã mở rộng test hiện có.
- 3 — low, patch documentation: backend hiện không có thumb_url. Đã kiểm tra InteractiveHighlightOut trong apps/backend/schemas/heritage.py; type comment và README ghi rõ thumbnail lấy từ tour nguồn, backend cũ dùng icon fallback. Không thêm migration/ingestion/API ngoài yêu cầu UI tour JSON.

Không có finding cần HALT hoặc defer trong thay đổi này.
