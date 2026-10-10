---
title: 'Sửa trạng thái active của ssNavBar'
type: 'bugfix'
created: '2026-10-10'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Ô scene đang chọn phải nhận style active của ssNavBar theo styles.css: rộng 44px, nền active, số có text-shadow. Giữ định tuyến và hover; không tô nền wrapper.

</frozen-after-approval>

## Implementation Notes

- Trước sửa, aria-selected đúng s1 nhưng ô vẫn 36px, text-shadow none; class active và nền được gắn vào wrapper. Chuyển class active sang Link chứa ssNavBar.
- Browser kiểm tra s0, s4, s1 trên desktop1440, tablet768, mobile390: đúng một ô selected, nền wrapper trong suốt, số active có glow. Giữ responsive active/inactive44/36,36/28,32/24; hover50px không thay đổi selected. Click s2 và browserBack cập nhật đúng.
- Bài kiểm tra đầu giả định mobile cũng44px nên thất bại; đối chiếu media queries xác nhận mobile32px là hành vi sẵn có. Sửa kỳ vọng kiểm tra, không đổi responsive ngoài phạm vi.
- Đã xem sáu ảnh mặc định/hover của desktop, tablet, mobile. Lint, TypeScript và git diff --check đạt, giữ nguyên cảnh báo PortraitCard ngoài phạm vi.

## Review Triage Log

- low, không thêm hạ tầng: reviewer đề nghị browser regression test thường trực. Đã chạy probe giao diện và điều hướng; repo chưa có browser runner, không thêm dependency/framework cho thay đổi hai dòng.
- medium, defer: route alias s01 hiển thị scene nhưng không chọn ô nào vì resolver nhận số còn nav so key chính xác. Kiểm chứng trên browser; lỗi sẵn có ngoài phạm vi gắn class active, không đổi contract định tuyến trong bản sửa này.
