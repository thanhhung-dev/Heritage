---
title: 'Giữ viewer và nav khi chuyển scene'
type: 'bugfix'
created: '2026-10-10'
status: 'done'
route: 'oneshot'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Chuyển scene trong cùng tour không mount lại HeritageViewer/nav, không chạy lại animation vào màn hình hoặc reset trạng thái điều khiển. Active, tiêu đề và mô tả vẫn cập nhật theo scene, Back/Forward hoạt động. Landing /content/slug giữ nguyên màn hình bắt đầu, không hiện viewer sớm.

Yêu cầu bổ sung: bỏ glow quanh viền ô nav active, giữ nền active và hiệu ứng chữ hiện có.

</frozen-after-approval>

## Implementation Notes

- Trước sửa, kiểm tra s1 → s2 xác nhận DOM nav cũ bị gỡ, năm animation slideInFromLeft chạy lại và trạng thái Play reset.
- Layout [slug] sở hữu HeritageViewer khi có sceneKey. Page [sceneKey] chỉ đồng bộ scene với context và trả null. Khởi tạo provider từ sceneKey hiện tại để vào trực tiếp scene sâu đúng dữ liệu.
- Thiết kế cuối: provider nhận currentSceneKey trực tiếp từ URL qua layout, không giữ bản sao state và setter. Scene page chỉ trả null. Điều này tránh tiêu đề cũ ở render đầu khi vào lại từ landing.
- Kiểm chứng trường hợp s3 → history.go(-2) về landing → Start: bản trung gian chèn viewer với tiêu đề Xung Khiêm Tạ; bản cuối chèn đúng Lăng Tự Đức ngay từ đầu.
- Xóa animation activeNavBarGlow và keyframes chỉ phục vụ glow viền. Box-shadow/animation active là none trên desktop/mobile; giữ text-shadow chữ và nền active.
- Browser1440/390 kiểm tra s1 → s2 → s3, Back/Forward, Next/Previous: DOM nav giữ nguyên, không animation vào lại, trạng thái Play/mute/CC giữ nguyên, tiêu đề/active cập nhật, không fetch payload thêm. Landing và Start đúng. Đã xem bốn ảnh mặc định/hover không glow viền.
- npm test, lint, TypeScript và git diff --check đạt; giữ nguyên hai cảnh báo img trong PortraitCard.

## Review Triage Log

- medium, đã sửa: provider giữ scene cũ khi tái nhập từ landing do initialSceneKey chỉ dùng khi mount. Đã tái hiện render đầu sai bằng MutationObserver, rồi đổi nguồn scene sang URL có kiểm chứng trước/sau.
- low, không thêm hạ tầng: reviewer đề nghị browser regression thường trực. Đã chạy probe hành vi và vòng đời thật; repo chưa có browser runner, không bổ sung framework/dependency cho bản sửa này.
