---
title: 'Dive Deeper theo dữ liệu tour JSON'
type: 'feature'
created: '2026-10-13'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Thêm nút góc trên phải Dive Deeper theo markup được cung cấp: kính tròn, icon lens, glow/rays, shine và dấu chân cho khu vực free_explore. Nút chỉ hiện khi cảnh có dữ liệu interactive của tour; ID, mode, camera và các điểm tương tác phải lấy từ tour.json, không hard-code 332. Bấm nút tạm dừng audio và vào góc Explore của khu vực; có Reset/Exit và chọn điểm để xem nội dung, camera focus; đóng nội dung khôi phục góc trước. Giữ phần ExploreControls cũ đã gỡ của người dùng, không đưa lại hàng nút cũ. Không thay dữ liệu JSON hoặc bổ sung FPS/collision.

</frozen-after-approval>

## Implementation Notes

- Tận dụng components/ExploreControls.tsx để sở hữu CTA/điều khiển Explore mới và style góc đã có trong styles.module.css. HeritageViewer.tsx gắn UI mới thay vị trí cũ đã gỡ; useTourPlayer cung cấp interactive đầu tiên của cảnh (JSON hiện tối đa một khu vực/cảnh) và ánh xạ free_explore → free orbit.
- Tái sử dụng enterExplore/resetExplore/exitExplore, selectHighlight của engine, HighlightPanel và raycast marker hiện có. Danh sách điểm tương tác cung cấp lối chọn bằng bàn phím, không phụ thuộc raycast.
- CSS tham chiếu lấy từ stylesheet Tapestry trong HTML nguồn; bổ sung phần rays/glow/tilt/shine/footsteps còn thiếu. Giữ breakpoint mobile 640px của repo, kiểm tra nút không che title và điều khiển playback.
- Không có thay đổi không thể đảo ngược hoặc câu hỏi sản phẩm còn mở; phạm vi nhỏ, không thêm API công khai hay framework. Asset glow PNG dùng đúng ảnh tham chiếu để tránh lỗi SVG blur iOS; SVG icon dùng CDN đã có trong markup.
- Kiểm tra hiển thị/ẩn theo scene, ID 332 và các ID khác, mode standard/free_explore, camera đúng preset, pause audio, chọn/đóng điểm, reset/exit, đổi cảnh và keyboard; render desktop/mobile/reduced-motion, chạy test/lint/TypeScript.
- Kết quả: 16 test frontend đạt; lint không có lỗi (4 cảnh báo img có sẵn ở splash/PortraitCard); TypeScript và git diff --check đạt. Test dữ liệu có fixture ID/mode thay thế để bắt hard-code, không giả định effect được thực thi trong SSR.
- Kiểm tra Chrome với GLB Petra/audio thật đạt: camera/target khớp JSON (sai số dưới 1e-7), audio pause khi vào Explore, Reset/Exit, chọn/đóng điểm, focus bàn phím, đổi scene, các chiều rộng 320/390/640/641/900/1440 và reduced motion. Ở viewport 390×400, popup có scrollHeight > clientHeight và scrollTop tăng được; link scene s7 giữ focus sau khi rời Explore.
- Ảnh desktop/mobile/tablet/popup/màn hình thấp/free đã kiểm tra trực quan. Bằng chứng lưu ở `.amp/in/artifacts/dive-*.png` và `dive-validation.log`. Hình học model/góc nguồn tối và hạn chế orbit/collision có sẵn không thuộc thay đổi này; giữ tọa độ JSON nguyên vẹn.
- Cập nhật README thay hướng dẫn hàng nút cũ bằng Dive Deeper, mode JSON, danh sách điểm, Reset/Exit và Escape.

## Review Triage Log

- 1 — medium, patch: CTA che header ở tablet; chuyển CTA/panel xuống dưới header ở ≤900px, kiểm tra hình và bounding box tại 641/900px đạt.
- 2 — medium, patch: panel/popup chồng nhau trên màn hình thấp; giới hạn chiều cao, ẩn panel khi popup mở ở ≤600px và cho popup cuộn. Chrome 390×400 xác nhận vị trí, cuộn và Escape/focus khôi phục.
- 3 — medium, patch: effect theo mode có thể lấy focus khi đổi scene; chỉ chuyển focus sau thao tác Enter/Exit rõ ràng. Đổi scene trong Explore giữ focus trên link điều hướng.
- 4 — false: thiếu fallback focus khi scene bỏ điều khiển đang focus được nêu như lỗi điều hướng; đường điều hướng hiện dùng link, link nhận và giữ focus sau chuyển sang s7 trong Chrome. Không bổ sung xử lý cho chuyển scene tự động chưa có đường gọi.
- 5 — medium, patch: popup không có luồng keyboard focus/thoát; focus Close khi chọn điểm, Escape đóng và trả focus về nút điểm. Chrome xác nhận cả desktop và màn hình thấp.
- 6 — low, patch: reduced motion vẫn scale khi hover; tắt transform hover, Chrome xác nhận transform none và animation none.
- 7 — medium, patch: accessible name không chứa nhãn Dive Deeper; đổi aria-label thành “Dive Deeper — Explore Area in 3D”, browser chọn nút bằng tên này.
- 8 — low, reject: thiếu test lifecycle được giữ trong repo; đã chạy lifecycle trên trình duyệt thật. Thêm framework/dependency browser chỉ cho thay đổi này lớn hơn sửa nhỏ, trong khi script kiểm tra phụ thuộc CDN/model và React inspector không phù hợp làm regression ổn định.
- 9 — low, reject: thiếu test UI được giữ trong repo; đã thực thi các trạng thái render, keyboard và geometry qua Chrome, kiểm tra ảnh trực quan; không thêm hạ tầng test UI mới chỉ để đáp ứng đề nghị này.
- 10 — low, patch: chỉ assert ID production có thể bỏ sót hard-code; thêm fixture cùng scene key nhưng area 901, highlight 987 và mode free, assert dữ liệu trả về thay đổi tương ứng.

Không có finding cần HALT hoặc defer trong thay đổi Dive Deeper này.
