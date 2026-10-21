---
title: 'Đồng bộ chuyển cảnh camera và thời lượng audio'
type: 'bugfix'
created: '2026-10-13'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Camera bay tới góc mở đầu khi chuyển cảnh, trừ cảnh đánh dấu instant_move. Camera start → zoom di chuyển liên tục theo toàn bộ thời lượng audio, dừng khi pause và theo đúng vị trí khi tua. Metadata audio không được làm camera nhảy hoặc hủy chuyến bay chuyển cảnh. Giữ nguyên chỉnh sửa splash của người dùng.

</frozen-after-approval>

## Implementation Notes

- camera-controller.ts đang dùng max(duration × 0.35, 4) và easing cubic cho timeline; thay bằng toàn bộ duration và nội suy tuyến tính để không gần như dừng trước cuối audio. Giữ easing cubic cho chuyến bay chuyển cảnh 1.6 giây.
- useTourPlayer.ts đang đặt thời gian chuyển cảnh bằng 0. Dùng chuyến bay có sẵn; startTimeline chờ chuyến bay kết thúc thay vì hủy và restore ngay.
- Reset khóa timeline trong effect đổi cảnh trước khi bật timeline; không dùng duration từ audio URL cũ khi đổi cảnh.
- Kiểm tra hồi quy clip 6 giây, clip ngắn hơn 4 giây, pause/seek, metadata đến trong chuyến bay và thiếu pose zoom. Chạy test frontend, lint, TypeScript và kiểm tra trình duyệt nếu khả dụng.
- Không có thay đổi không thể đảo ngược hay câu hỏi sản phẩm chưa giải quyết. HTML Tapestry chứa preset nhưng không chứa thuật toán camera; không khẳng định mô phỏng chính xác thuật toán đó.
- Triển khai cuối: hòa chuyến bay vào pose audio khi autoplay phát sớm, thay vì chỉ chờ chuyến bay. Khi metadata đến muộn, lấy pose đang hiển thị làm gốc mới và giữ thời gian bay còn lại để tránh giật.
- stopTimeline nhường cả chuyến bay đang chạy; thao tác chọn góc/Explore khóa bật timeline tự động cho đến khi rời Explore hoặc đổi cảnh.
- Đã chạy RED trước sửa: 2 test hồi quy thất bại; GREEN toàn bộ 15 test. Sau review bổ sung RED cho metadata tại currentTime khác 0, sửa và chạy GREEN lại. Lint/TypeScript đạt; chỉ có cảnh báo img sẵn có. Coverage camera-controller: 89.02% dòng, 86.76% nhánh (toàn bộ tập focused: 87.58% dòng).
- Chrome chạy model/preset Petra thật với audio WAV 6s thay thế trong phiên kiểm thử. Camera/target khớp nội suy tại 0, 1.5, 3, 4.5, 6s và khi tua ngược, sai số < 1e-7; đổi s0 → s1 có flight rồi kết thúc; metadata trễ 1.5s không giành camera từ Explore/chọn zoom. Không thay asset nguồn. Đã xem ảnh 0s, 3s, 6s và s1 trong .amp/in/artifacts.

## Review Triage Log

- medium → patch: metadata gắn timeline khi audio đã phát gây bước nhảy ở frame tiếp theo. Test RED xác nhận; rebase chuyến bay từ pose đang hiển thị khắc phục, GREEN đạt.
- medium → patch: metadata trễ bật timeline trong Explore. Khóa tự động theo cảnh khi Explore nhận quyền; browser trì hoãn metadata xác nhận pose giữ nguyên.
- medium → patch: metadata trễ ghi đè lựa chọn zoom thủ công. Khóa tự động sau chuyến bay do người dùng chọn; browser xác nhận zoom cuối giữ đúng preset.
- medium → defer: hai cảnh dùng cùng URL narration giữ state giữa cảnh vì hook chỉ reset theo URL. Đây là lỗi có sẵn, bộ tour hiện tại dùng URL khác nhau; lưu riêng để xử lý định danh phiên audio nếu tích hợp dữ liệu dùng chung URL.
- medium → patch: đổi sang cảnh không có playback hoặc vào Explore vẫn để chuyến bay cảnh cũ chạy. stopTimeline hủy cả flight và đồng bộ controls; test xác nhận camera không tiếp tục di chuyển sau khi nhường quyền.
