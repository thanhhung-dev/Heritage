---
title: 'Bộ khung player và Three.js cho tour'
type: 'feature'
created: '2026-10-12'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent">

## Intent

Dựng code cơ bản theo cây player/three/components người dùng cung cấp để phát triển tiếp. Giữ model R2, ownership canvas ở content và loading gate F5. Tách renderer/loader/environment/camera/explore/highlights; hooks audio/VTT nhận đầu vào rõ ràng; nối Explore/Reset/Exit cơ bản vào viewer. Không tự tạo dữ liệu DB hoặc triển khai đầy đủ trải nghiệm Tapestry.

</frozen-after-approval>

## Implementation Notes

- Three.js 0.186.1 và types 0.186.0 đã cài từ trước, không cài trùng. Tách module từ engine đang chạy, cache/tài nguyên thuộc một engine.
- Context giữ engine đã sẵn sàng; readiness suy ra từ engine, không thêm trạng thái trùng. Canvas vẫn mount ở layout content.
- Schema chưa có narration/VTT riêng và thời gian highlight; không dùng voice clip hoặc tọa độ demo để giả lập. API và README ghi rõ phần cơ bản/phần chưa nối.
- Thêm tsx cho test TypeScript bằng runner Node hiện có; kiểm tra VTT, khoảng timeline, seek và tải trễ scene cũ.

## Verification

- `npm test`: 5 tests pass (1 test hiện có + 4 test tour). Camera regression dùng tọa độ Tapestry dưới target và ngoài giới hạn fit: fail trước sửa, pass sau sửa, bao gồm Standard/Free/Reset/Exit.
- `npm run lint` và `npx tsc --noEmit --incremental false`: pass. Lint còn 2 cảnh báo img có sẵn ở PortraitCard; test runner có cảnh báo Three CJS deprecation.
- Browser WebGL trên Next/R2: loading gate, render model, drag, Explore/Reset/Exit, desktop/mobile, giữ canvas qua scene và F5 khi tải lỗi đã kiểm tra.
- Browser fixture với GLB/WAV/VTT thật: play/pause/seek/mute, captions chồng nhau và biên cuối, reset damping, preset DB/camera GLB world-space, raycast/panel, cache/timed highlights, scene reset/unmount đều pass; không có page error.
- Đã xem ảnh default, Standard, Free orbit, desktop/mobile và highlight fixture trong `.amp/in/artifacts/`. Fixture không phải dữ liệu highlight Tự Đức.
- Tự kiểm tra diff và quyền sở hữu tài nguyên; chưa triển khai lens shader, FPS/collision, camera tween hoặc adapter DB đầy đủ. API backend chưa chạy, không coi payload demo là dữ liệu thật.
