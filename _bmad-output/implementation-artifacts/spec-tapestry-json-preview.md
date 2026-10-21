---
title: 'Chạy thử tour từ dữ liệu Tapestry HTML'
type: 'feature'
created: '2026-10-12'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent">

## Intent

Tạo tour.json từ dữ liệu trong tapestry.html và dùng model/camera/highlight của chính tour đó để chạy thử trên Three.js. Có trang thử riêng, giữ model Tự Đức và loading gate hiện có. Nối narration/VTT, camera scene/explore/highlight và timeline highlight để thử dữ liệu thật, không sửa DB hoặc triển khai toàn bộ Tapestry.

</frozen-after-approval>

## Implementation Notes

- Source: script application/json id tapestry-data. Model chính từ threeJS_sets[threeJS.set_id]; 7 scene, overview, highlights được join theo ID, không lấy các index trùng lặp.
- Fixture chuẩn hóa tại features/tour/tour.json; script trích xuất tái lập được. Runtime dùng fixture chỉ cho slug tapestry-test, không fetch backend ở trang thử.
- Camera/payload dùng kiểu hiện có; metadata narration/VTT/timed highlights riêng của fixture, không thay contract backend.
- end_time null nghĩa là không đặt mốc tắt trong scene; đọc animation GLB nếu LoopRepeat, không đoán thành rotate. Không triển khai lens shader/FPS/collision/fade.
- Giữ nguyên thay đổi bên ngoài tại apps/backend/models/admin.py và source HTML chưa tracked.

## Verification

- Tự kiểm tra diff, không chạy review subagent thường lệ. JSON khớp toàn bộ kết quả trích xuất lại từ source: 1 overview, 7 scene, 10 marker, 14 instance model timeline.
- Model chính 6,985,864 bytes, có CORS và yêu cầu KHR_draco_mesh_compression + KHR_texture_basisu. Vendored decoder Draco glTF từ Three đang cài, kèm README/license; checksum bản copy khớp nguồn.
- `npm test`: 7 tests pass. Test extractor dùng ID/set/sequence bất đối xứng để bắt join sai; timeline null end/LoopRepeat/seek kiểm tra AnimationMixer thật.
- `npm run lint` và `npx tsc --noEmit --incremental false`: pass. Còn hai cảnh báo img có sẵn và cảnh báo Three CJS trong test runner.
- Browser Chrome/WebGL trên Next thực: deep link/F5 quay về loading; Draco/KTX2 decode, audio play/pause, seek +15 và VTT, model nến/lạc đà theo timeline, camera start/zoom/explore/highlight/close/reset/exit khớp số nguồn; giữ cùng canvas và không tải lại model chính qua scene. Không page error, không request backend trong fixture. Request abort ở StrictMode/navigation là cleanup dự kiến.
- Đã xem ảnh overview/zoom/explore/highlight/timeline/camels/mobile tại .amp/in/artifacts. Marker quá lớn đã sửa và capture lại; lạc đà hiển thị trong scene s3. Góc focus Niches khá tối dù pose khớp nguồn; giữ camera tác giả, chưa collision. Clipping navigation/attribution mobile cũ không sửa.
- Probe HTTP 503: Start vẫn disabled và deep link về landing. Control Tự Đức vẫn yêu cầu /tour-assets/tuduc.glb, không dùng model Petra. Chưa chạy production build; không thay DB/R2 hoặc push.
