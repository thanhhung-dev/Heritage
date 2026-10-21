---
title: 'Quay về loading khi refresh tour 3D'
type: 'bugfix'
created: '2026-10-11'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent">

## Intent

Khi F5 hoặc mở thẳng URL scene mà model chưa sẵn sàng trong bộ nhớ trang, đưa người dùng về `/content/{slug}` để tải model. Chỉ cho bấm Bắt đầu khi GLB đã tải và giải mã thành công. Chuyển scene trong phiên đã sẵn sàng không tải lại model. Không thêm lưu scene, camera database hoặc highlight.

</frozen-after-approval>

## Implementation Notes

- Layout content sở hữu trạng thái model sẵn sàng, chia sẻ qua context; canvas báo sẵn sàng sau khi engine tải/giải mã thành công. Trạng thái payload API độc lập với model.
- Scene chưa sẵn sàng dùng router.replace về content và không render viewer; giữ canvas mounted để không tải lại khi redirect.
- Nút Start là button disabled khi chưa sẵn sàng; lỗi GLB không mở khóa nút. Tải thành công vào s0 khi người dùng bấm Start.
- Đã tái hiện trước sửa với asset HTTP503: mở scene/F5 giữ URL s2; Start vẫn là link có thể bấm.
- Kiểm tra browser loading có chặn Start, model thật mở khóa Start, F5 về content, đổi scene giữ canvas/request, lỗi tải vẫn chặn; kiểm tra lint/TypeScript/test. Giữ file tapestry.html và các sửa local từ lượt trước.
- Đã kiểm tra sau sửa bằng Chromium/WebGL: model R2 thật mở khóa Start; content → s0 → s2 giữ cùng canvas và số request; F5 tại s2 về content với nút disabled, không render viewer; lỗi HTTP503 vẫn disabled; mở thẳng s3 cũng về content. Không có pageerror. Đã xem ảnh loading/ready/F5 desktop/mobile/lỗi tải trong .amp/in/artifacts.
- Lint, TypeScript và test hiện có đạt trên Node 20.19.6; chỉ hai cảnh báo img cũ trong PortraitCard. API payload vẫn lỗi kết nối trong môi trường kiểm tra, độc lập với model đã tải thành công.
- Tự kiểm tra diff và các trường hợp hồi quy thay vì review subagent thường lệ theo quy tắc executor. Callback onReady ổn định, chỉ báo thành công sau giải mã GLB; redirect không remount canvas. Không thêm phạm vi hoặc review gate bên ngoài.
