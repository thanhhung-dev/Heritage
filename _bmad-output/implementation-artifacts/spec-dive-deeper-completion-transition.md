---
title: 'Dive Deeper sau thuyết minh và chuyển động camera Explore'
type: 'bugfix'
created: '2026-10-13'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Chỉ hiện Dive Deeper khi thuyết minh của cảnh hiện tại đã kết thúc và cảnh có interactive. Đổi cảnh hoặc Replay ẩn lại; Skip Voiceover dùng pha kết thúc hiện có, cảnh không có audio cũng dùng pha kết thúc hiện có. Camera chuyển mượt khi vào/thoát Explore, reset, focus điểm và đóng điểm; tọa độ vẫn lấy từ tour.json. Giữ chuyển cảnh 1.6 giây và timeline bám toàn bộ audio đã sửa, không thay JSON hoặc thêm FPS/collision.

</frozen-after-approval>

## Implementation Notes

- Dùng isEnded theo playbackKey sẵn có trong HeritageViewer, không tạo đồng hồ/cờ hoàn thành riêng. Replay khi Explore mở trả quyền camera trước khi phát lại.
- useTourPlayer đổi apply preset tương tác/focus thành flyCameraPreset. Dùng thời lượng 1.2 giây của viewer cho chuyển Explore vì JSON không cung cấp thời lượng transition.
- camera-controller.restore nhận thời lượng tùy chọn và tái dùng flight hiện có, flyToPreset dùng chung đường đó; explore-controller.exit và tour-engine truyền thời lượng để không nhảy trước khi timeline hòa vào pose audio.
- Kiểm tra RED/GREEN camera exit và browser với audio 6 giây: ẩn trước khi hết, hiện sau hết, Skip/Replay/đổi scene, chuyển camera không nhảy và tới đúng pose JSON. Không đổi HTML nguồn untracked của người dùng, không push.
- RED thực thi: Explore exit nhảy ngay về pose cũ; browser xác nhận CTA hiện trước kết thúc narration. Sau sửa, cả hai đạt GREEN. Bổ sung RED cho up vector khác world-up, rồi sửa flight/timeline nội suy up và giữ đúng endpoint.
- 17 test frontend, lint và TypeScript đạt; lint chỉ còn 4 cảnh báo img có sẵn. Coverage focused: camera-controller 90.63% dòng/85% nhánh, explore-controller 100% dòng/94.12% nhánh, tổng module được đo 81.71% dòng. Không coi coverage SSR hook là bằng chứng effect đã chạy.
- Chrome dùng GLB Petra thật và fixture WAV 6 giây thay narration trong phiên kiểm thử, không thay asset/JSON trên đĩa. Đạt natural ended, Skip, Replay trước kết thúc, reset gate khi đổi scene, camera entry/Reset/exit không nhảy và endpoint/focus/close khớp JSON. Kiểm tra thêm author data camera null và overview không audio bằng dữ liệu trong bộ nhớ trình duyệt: Reset và Replay trong Explore đều đạt.
- Ảnh trước/sau kết thúc trên desktop và free Explore mobile đã kiểm tra bằng view_media. Bằng chứng: `.amp/in/artifacts/completion-{before,after,mobile-after,mobile-free}.png`, `completion-green.log`, `completion-red.log`, `completion-orientation-red.log` và `completion-coverage.log`. Footsteps thay icon lens trong free mode theo CSS nguồn; clipping attribution/model geometry có sẵn không thuộc thay đổi.

## Review Triage Log

- 1 — medium, patch: bỏ reset entry khiến khu vực không camera riêng không Reset được. applyInteractiveCamera trả kết quả; thiếu/invalid preset thì reset entry bằng flight 1.2 giây. Browser thay cam_pos=null, orbit sang pose khác rồi Reset, xác nhận về pose trước khi Explore.
- 2 — medium, patch: Replay ở cảnh không audio xóa cờ kết thúc mà không có event để bật lại CTA. Giữ endedScene=playbackKey khi không audio. Browser overview với interaction/no narration kiểm tra Replay cả trước và trong Explore: CTA vẫn có, Explore thoát đúng.
- 3 — medium, patch: animated restore lưu up nhưng applyPose ép world-up, làm mất roll của pose đã lưu. Test RED với up=[0,0,1]; nội suy up cùng pose, test midpoint và endpoint GREEN; timeline blend giữ up nguồn chuyến bay.
- 4 — low, reject: thiếu test hook/viewer được giữ trong repo. Đã chạy flow browser với timeline narration kết thúc rồi Exit, Replay trước kết thúc và Replay trong Explore không audio, kiểm tra pose/control availability; không thêm framework UI hoặc giữ script phụ thuộc React inspector/CDN làm regression. Replay trong return flight của narration đã kết thúc không phải đường UI hiện có (nút trái là Previous scene); không thêm state/guard cho đường gọi chưa có.

Không có finding cần HALT hoặc defer trong sửa lỗi này.
