---
title: 'Ô điểm Dive Deeper có thumbnail'
type: 'feature'
created: '2026-10-13'
status: 'in-progress'
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
