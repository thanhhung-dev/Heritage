---
title: 'Đồng bộ nút playback và icon HeritageViewer'
type: 'bugfix'
created: '2026-10-10'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Thay các ảnh icon trong HeritageViewer bằng icon thư viện sẵn có, không tải icon từ CDN. Giữ ảnh đại diện, bố cục đã căn giữa, nhãn truy cập và thao tác của nút. Không sửa PortraitCard.

Theo yêu cầu tiếp theo của người dùng, đối chiếu styles.css và đồng bộ sáu nút playback thành 40 × 40px, giữ padding tua 8px, Play/Pause 13px; không phóng to nút Next khi hover.

</frozen-after-approval>

## Implementation Notes

- Dùng @ant-design/icons đã cài đặt. Giữ SVG tua 15 giây, dùng chữ CC và SVG nội tuyến cho dấu chân trang trí vì không có biểu tượng thư viện tương đương.
- Reset dùng :where(.viewer) button để có độ ưu tiên như button trong CSS gốc, vẫn giới hạn phạm vi tour. Loại rule tua 36px; Replay nhận kích thước từ ssButton. Khôi phục vị trí nhóm audio và padding Pause.
- Xóa tham chiếu accScenePages/accOverviewPages không tồn tại gây class undefined. Không sửa styles.css hoặc docs/sprint.md của người dùng.
- Trình duyệt xác nhận ở 1440, 768, 641, 640, 390, 320px: sáu nút cùng 40 × 40px, cùng cao độ, không chồng hoặc tràn; Play/Pause không dịch vị trí, icon 14px; tua có padding 8px và icon 24px; hover Next vẫn 40px.
- Kiểm tra Play/Pause, Replay và điều hướng scene thành công. Các kiểm tra trước đó xác nhận mute, CC, fullscreen và không có request icon CDN. Đã kiểm tra ảnh desktop/mobile, mặc định và đang phát.
- npm test, npm run lint, TypeScript và git diff --check đạt; giữ nguyên hai cảnh báo img ở PortraitCard ngoài phạm vi.

## Review Triage Log

- false: nhận định Play có 13px padding nhưng icon 20px gây tràn ở bản icon ban đầu; đo thực tế lúc đó reset làm padding về 0, SVG 20px nằm giữa khung 40px. Sau yêu cầu mới sửa reset, đồng thời icon thành 14px đúng vùng nội dung.
- low, đã sửa: Explore thiếu kích thước/màu rõ ràng. Dùng ssExploreImg 22px và màu trắng.
- false: CC là text không đúng mục tiêu; chữ CC đã được chọn rõ trong Implementation Notes, có font-size/font-weight và aria-hidden, không tải ảnh.
- false: thiếu kiểm chứng hồi quy; đã chạy kiểm tra browser trên sáu độ rộng, trạng thái Play/Pause, hover, padding, class, thao tác và điều hướng. Không thêm framework test mới cho lần chỉnh CSS này.
