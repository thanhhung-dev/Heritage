---
title: 'Khôi phục đường timeline và thời gian playback'
type: 'bugfix'
created: '2026-10-10'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Khôi phục timeline theo styles.css: line dày 1.2px, màu rgba(240,232,221,.5), thời gian mặc định ẩn và hiện phía trên khi hover, không đè lên line. Giữ nguyên nút playback và thao tác hiện tại.

</frozen-after-approval>

## Implementation Notes

- Đo trước sửa: timeline bị border-box làm vùng nội dung bằng 0px; elapsed/total opacity 1 cả khi không hover do override cuối module.
- Đặt content-box trực tiếp tại playbackTimeline, trả màu line theo tham chiếu và xóa override ép hiện thời gian. Không sửa styles.css hoặc docs/sprint.md của người dùng.
- Browser kiểm tra 1440, 641, 390, 320px: vùng line 1.1875px do làm tròn từ 1.2px; tổng cao 21.1875px; opacity thời gian 0 → 1 → 0 khi hover/rời; đáy chữ cách line 2.8125px. Play/Pause vẫn hoạt động.
- Đã xem bốn ảnh desktop/mobile mặc định và hover. Lint và git diff --check đạt; hai cảnh báo img có sẵn trong PortraitCard không thay đổi.

## Review Triage Log

- low, không thêm hạ tầng test: reviewer đề nghị giữ browser regression test. Repo hiện chỉ có node test, không có browser test runner; đã chạy probe hành vi trên trình duyệt nhưng không thêm dependency/framework chỉ cho bản sửa CSS nhỏ này. Không phát hiện lỗi chức năng trong diff.
