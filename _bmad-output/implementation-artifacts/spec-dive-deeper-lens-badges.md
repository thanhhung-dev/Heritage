---
title: 'Lens badge đánh số trên model 3D'
type: 'feature'
created: '2026-10-13'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Thay marker cầu bằng lens_badge: quad MeshBasicMaterial, texture vòng tròn glow + số có alpha, nằm trong Group tại lens_pos của điểm nguồn. Badge quay mặt về camera mỗi frame, luôn nhìn thấy trên công trình; bấm giữ đúng ID, popup và camera transition hiện có. Giữ các ô thumbnail đã làm. Không đổi môi trường Sky/Fog hoặc dữ liệu camera.

</frozen-after-approval>

## Implementation Notes

- interactive-highlights.ts tạo CanvasTexture trong suốt cho số theo thứ tự sort_order (xếp rồi đánh 1..N), PlaneGeometry và Group cho từng hotspot; dùng NormalBlending để giữ số dễ đọc thay vì đoán Additive là cấu hình nguồn. depthTest/depthWrite=false, toneMapped=false, renderOrder cao.
- Kích thước quad cơ sở 0.1 gồm glow; vòng chính đường kính khoảng 0.05 để giữ đường kính tương đương marker cầu cũ; nhân lens_scale từ JSON. lens_rot không áp lên billboard luôn hướng camera; dữ liệu nguồn vẫn giữ nguyên.
- tour-engine gọi update billboard sau camera/OrbitControls, trước render. Raycaster chọn mesh con theo ID; dispose map/material và geometry khi thay cảnh/engine.
- Kiểm tra raycast trước/sau xoay camera, ID/order, ẩn/hiện và thay scene; browser thật với Petra, click badge trên canvas, desktop/mobile, kiểm tra số/glow/selected bằng screenshot. HTML nguồn untracked giữ nguyên, không push.

## Review Triage

- Góc quad trong suốt nhận click: đã sửa bằng giới hạn UV tròn, có regression RED/GREEN.
- Badge hiện xuyên geometry do depthTest=false: giữ theo yêu cầu overlay người dùng, không coi là lỗi trong phạm vi này.
- Canvas2D stub không chứng minh số thực sự được vẽ: xác minh bằng native Chrome Canvas2D, nhãn 1/2/3 và alpha góc = 0; kiểm tra ảnh texture thực tế có số 1, rim và glow. Không thêm test mock-call riêng tư.
- Sau kéo orbit, camera focus lệch khoảng 0.01225 do damping còn quán tính: tái hiện RED bằng OrbitControls công khai, sửa syncControls xóa quán tính nhưng bảo toàn pose. GREEN và browser click sau orbit đạt JSON trong tolerance 1e-6.

## Validation / Delivery

- npm test: 19/19; TypeScript noEmit: pass; lint: không lỗi, 4 warning img có sẵn.
- Chrome với model/audio thật: CTA ẩn khi narration chưa kết thúc, Skip mở CTA; canvas click mở đúng popup và tới đúng camera JSON ở desktop/mobile, cả sau kéo orbit; scene free không điểm không hiện danh sách.
- Đã xem ảnh desktop/mobile mặc định, selected, sau orbit và texture tại `.amp/in/artifacts/lens-badge-*.png`. Badge nhìn tròn, số đứng thẳng, không có nền vuông. Góc selected “Niches for statues” tối/sát geometry theo JSON, không có badge trong khung hình đó; không coi ảnh selected là bằng chứng badge luôn nhìn thấy. Badge 2 s2 bị tiêu đề che một phần; giữ tọa độ nguồn.
- Không triển khai Sky/Fog, collision, FPS hoặc shader gốc Tapestry. Các ô thumbnail giữ nguyên.
- Thay đổi lưu bằng commit local; chưa push/merge/deploy. HTML nguồn untracked không thay đổi.
