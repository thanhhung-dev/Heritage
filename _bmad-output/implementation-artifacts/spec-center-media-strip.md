---
title: 'Căn giữa thanh điều khiển tour'
type: 'bugfix'
created: '2026-10-10'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Thanh media của HeritageViewer cần gom về giữa thay vì kéo nhóm thông tin và hệ thống ra hai mép. Giữ nguyên chức năng, cân giữa playback trên desktop và tránh chồng nút trên màn hình hẹp.

</frozen-after-approval>

## Implementation Notes

- CSS module đang có override width 100% và khai báo playbackControls trùng. Sửa trực tiếp các rule sở hữu bố cục, không thêm override mới. Không thay đổi docs/sprint.md chưa được theo dõi.
- Giới hạn chiều rộng 720px; dùng grid cân giữa playback và hai nhóm phụ. Dưới 640px chuyển sang hai hàng, chừa 32px ở đáy tránh attribution.
- Kiểm tra trình duyệt ở 1440, 768, 641, 640, 390, 320px: tâm playback đúng, không chồng nhóm, không tràn viewport. Play/Pause, mute/unmute, toggle CC đạt. Đã xem ảnh desktop và mobile cuối cùng.
- npm test và npm run lint đạt; lint còn hai cảnh báo img có sẵn trong PortraitCard. git diff --check đạt.

## Review Triage Log

- low, không sửa: thứ tự Tab theo DOM vẫn info → playback → system; trên mobile không trùng hoàn toàn thứ tự hàng hiển thị. Chuỗi chức năng vẫn có nghĩa; đảo DOM chỉ chuyển khác biệt này sang desktop, không cải thiện đồng thời cả hai bố cục.
- false: nhận định playback rộng khoảng 300px gây thiếu chỗ ở 641px. Đo trên trình duyệt: playback 250px, info 169.5px, system 140px; khoảng hở 10px bên trái và 39.5px bên phải. Không có chồng lấn.
