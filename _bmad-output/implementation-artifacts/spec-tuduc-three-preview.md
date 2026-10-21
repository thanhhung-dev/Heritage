---
title: 'Xem model GLB Tự Đức bằng Three.js'
type: 'feature'
created: '2026-10-11'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent">

## Intent

Thêm bản xem 3D đầu tiên vào giao diện tour hiện có, cài Three.js và tải model từ https://pub-2fc54e5237344dc9b845f2ff2c9309f8.r2.dev/TuDuc/TuDuckt.glb. Cho phép xoay/zoom để kiểm tra model, giữ giao diện và không tải lại khi đổi scene. Chưa triển khai camera database, highlight hoặc audio.

</frozen-after-approval>

## Implementation Notes

- Theo yêu cầu sửa của người dùng, canvas client và engine Three.js được mount trực tiếp ở layout `/content/[slug]`, không nằm trong viewer: tải ngay trên trang bắt đầu và giữ canvas khi vào scene hoặc quay lại trang bắt đầu. Viewer chỉ là lớp UI trong suốt, không chặn thao tác camera ở vùng trống. Không dùng camera demo vì không tương ứng model thật.
- GLB 110765772 bytes, không có camera, có KHR_texture_basisu; cần KTX2Loader và decoder Basis.
- R2 GET với Origin localhost chưa trả Access-Control-Allow-Origin. Dùng rewrite một đường dẫn cố định tới asset này, không proxy URL do người dùng cung cấp.
- Tự fit camera theo bounding box nhưng không thay đổi transform model. Cần loading/error, resize, huỷ tải và giải phóng renderer/geometry/material/texture lúc unmount, kể cả StrictMode.
- Kiểm tra lint/TypeScript, tải và render model thật, kéo/zoom, resize, scene navigation, lỗi tải và unmount. Không sửa file tapestry.html do người dùng cung cấp.
- Thêm HeritageCanvas.tsx và tour-engine.ts; cài three 0.186.1 và @types/three 0.186.0. Decoder Basis lấy từ package Three.js cùng README và giấy phép Apache-2.0, phục vụ tại public/three/basis.
- Tự review thay vì dùng subagent cho review thường lệ. Không thay đổi camera/database/audio hoặc các lỗi giao diện có sẵn.
- Đã chạy lint, TypeScript và test hiện có trên Node 20.19.6: đạt, chỉ hai cảnh báo img cũ trong PortraitCard. Kiểm tra browser với WebGL/SwiftShader tải model R2 thật và decoder, xoay/zoom làm đổi hình canvas, đổi scene không thêm request GLB, resize 390px, menu, rời tour xoá canvas và không phát sinh pageerror.
- Probe HTTP503 và WebGL không hỗ trợ hiển thị thông báo lỗi; loading hiển thị dung lượng model. Đã xem ảnh desktop/orbit/mobile/loading/error trong .amp/in/artifacts.
- Kiểm tra lại sau sửa ownership: model tải tại `/content/tu-duc` trước Start; Start và browser Back giữ cùng canvas, không thêm request GLB; viewer có nền trong suốt và vùng trống nhận pointer tại canvas. Không có pageerror. Đã xem ảnh content loading/ready và scene desktop/mobile. Hai request ban đầu trong dev là do StrictMode, không phải do đổi route. API payload hiện lỗi kết nối nên landing vẫn có thông báo `Failed to fetch`, độc lập với model đã render.

## Review Triage Log

- Đã sửa: resize từ desktop sang mobile có thể crop model do aspect; điều chỉnh khoảng cách camera và giới hạn zoom theo góc nhìn, browser và ảnh xác nhận model nằm trong viewport.
- Đã sửa: render liên tục model scan tĩnh gây tiêu hao GPU không cần thiết; chỉ render khi controls, kích thước hoặc model thay đổi, orbit/zoom vẫn cập nhật hình.
- Giữ ngoài phạm vi: file khoảng 111MB và khoảng 2,3 triệu vertices cần tối ưu/LOD trước triển khai rộng; không tự thay đổi asset R2. Camera DB và highlight là bước tiếp theo, không thuộc bản load model này.
