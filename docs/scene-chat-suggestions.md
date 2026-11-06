# Gợi ý chat theo từng câu chuyện trong tour 3D

Ngày kiểm tra: 07/11/2026. Nhánh `feat/HER-area-locked-tour-guide`.

## Hành vi

Khi chọn s0, s1… ở thanh bên trái, chatbox đọc `currentScene.title`,
`currentScene.description` và `currentSceneKey` từ `useHeritageTour`. Bốn câu hỏi
được tạo ngay ở frontend, không cần gọi AI để tải gợi ý.

Theo ảnh UI người dùng cung cấp, nhãn chip luôn ngắn gọn: **“Giới thiệu tổng quan”,
“Lịch sử hình thành”, “Kiến trúc đặc sắc”, “Khám phá cảnh này”**. Nội dung câu hỏi
đầy đủ thay đổi theo câu chuyện đang xem. Ví dụ ở **“Bia đá và những nỗi niềm”**,
chip tổng quan gửi câu hỏi giới thiệu chính mẩu chuyện này tại Khiêm Lăng.
Các mẫu câu hỏi không tự thêm năm xây dựng, tiểu sử hoặc dữ kiện lịch sử.

Mỗi chip có nhãn ngắn để vừa cửa sổ chat; hover hoặc trình đọc màn hình đọc
được câu hỏi đầy đủ. Khi bấm, câu hỏi chứa tên câu chuyện và tên di sản đang
tham quan, đi cùng `active_area_id` và `scene_context` của cảnh đó qua API hiện
có `POST /api/chat/message`. UI chỉ hiển thị ba nút ở header, lời chào **“Bạn muốn khám phá
điều gì về di sản này?”**, bốn chip và ô nhập **“Hỏi về di sản…”** như ảnh mẫu.
Tên khu vực/câu chuyện vẫn được giữ trong request và accessibility labels,
không thêm dòng thông tin vào header hoặc phía trên chip.

Gợi ý được tính từ dữ liệu của cảnh ở mỗi render, không lưu chung trong state
với phản hồi AI. Nếu đang hỏi s0 mà chuyển sang s3, phản hồi s0 vẫn hoàn tất lượt
hỏi cũ trong lịch sử, nhưng không được thay chip s3 bằng gợi ý cũ từ backend.
Trong lúc lượt hỏi cũ chưa xong, các chip mới hiển thị nhưng tạm disabled theo
trạng thái gửi chat hiện có. Lịch sử, bản nháp, vị trí và trạng thái mở cửa sổ
được giữ khi đổi cảnh trong cùng di sản. Đổi di sản/tài khoản vẫn reset theo
cơ chế khóa khu vực đã triển khai trước đó.

Tài khoản đăng nhập lưu và nối tiếp bằng `conversation_id`; server tự lấy history
đã lưu, không nhận lịch sử client thay thế. Pointer được tách theo tài khoản/tour;
đăng nhập lại đúng tài khoản khôi phục qua API history. Guest không giữ UUID trong
localStorage và không được nối tiếp record Guest bằng UUID. Chi tiết và kết quả
hiện tại ở [Chat API](../apps/backend/CHAT_API.md) và
[audit](../apps/backend/CHAT_TASK_AUDIT.md).

Nếu thiếu dữ liệu câu chuyện, widget dùng câu hỏi theo di sản hiện tại. Metadata
nêu một di sản khác đã biết cũng rơi về gợi ý của khu vực đang khóa. Alias check
phía frontend là lớp bảo vệ hiển thị; backend vẫn chịu trách nhiệm enforce
phạm vi, evidence và citations. Tour chưa đăng ký area tiếp tục bị khóa chat.

## Cách tự test trên giao diện

1. Chạy frontend/backend local theo cấu hình dự án. Dùng nhánh ở đầu tài liệu và
   backend hỗ trợ `active_area_id`. Mở tour có area đã đăng ký, ví dụ
   `/content/lang-tu-duc/s0` nếu dữ liệu local có slug này.
2. Mở chatbox ở s0. Kiểm tra lời chào, placeholder và bốn nhãn chip khớp ảnh mẫu;
   không có dòng “Hướng dẫn tại…” hoặc “Câu chuyện đang xem…”.
3. Chọn s1, s2, s3, s4 ở cột trái. Hover chip để kiểm tra câu hỏi đầy đủ đổi theo
   câu chuyện đang chọn; nhãn ngắn gọn vẫn giữ nguyên theo mẫu UI.
4. Tại câu chuyện văn bia, hover chip tổng quan để xem tên mẩu chuyện trong câu
   hỏi đầy đủ. Bấm chip và kiểm tra Network:
   `message` nêu đúng câu chuyện, `scene_context.key/id/title` đúng cảnh,
   `active_area_id` vẫn là `khiem-lang` đối với tour Lăng Tự Đức.
5. Khi một câu hỏi đang chờ AI, chuyển sang cảnh khác. Gợi ý đổi theo cảnh mới;
   lúc câu trả lời cũ về, gợi ý vẫn thuộc cảnh đang xem. Có thể hỏi chip mới khi
   lượt cũ kết thúc. Lịch sử chat trước đó vẫn còn.
6. Bấm tạo hội thoại mới khi đang ở s3: messages/draft reset nhưng gợi ý vẫn ở s3.
   Thu nhỏ, mở lại và kéo chatbox để kiểm tra các thao tác hiện có.
7. Vẫn xoay/zoom mô hình và điều hướng scene bình thường. Tính năng này không
   sửa renderer, camera, dữ liệu mô hình hoặc âm thanh.

## Kiểm thử tự động đã chạy

Từ `apps/frontend`:

```powershell
node --test tests/scene-chat-suggestions.test.mjs tests/scene-chat-request.test.mjs tests/tour-chat-scope.test.mjs
npx tsc --noEmit --incremental false
node node_modules/next/dist/bin/next lint --file features/chat/TourChatWidget.tsx --file features/chat/components/ChatInputBar.tsx --file features/chat/components/ChatOverlayWidget.tsx --file lib/scene-chat-suggestions.mjs --file lib/tour-chat-scope.mjs --file tests/scene-chat-suggestions.test.mjs
```

Kết quả: **14/14 tests pass**, TypeScript pass, ESLint không warning/error.
Các test kiểm tra dữ liệu s0–s4, 20 câu hỏi/transport payload, metadata thiếu/dài,
đổi thứ tự scene, đổi nội dung, đề cập area khác, request scope, auth và bounded
history. HTTP trong test dùng fetch mock.

Đã kiểm tra thêm bằng Edge headless trên preview tạm dùng chính `TourChatWidget`
và context của dự án: khung desktop 375×837 và mobile 366×732 không tràn ngang,
header không có dòng thông tin phụ, đúng lời chào/placeholder/bốn nhãn. Đã gửi
request s0, đổi sang s3 trong lúc chờ, hoàn tất phản hồi cũ rồi gửi chip mới:
request mới giữ `active_area_id=khiem-lang` và nhận đúng `scene_context.key=s3`.
Không có runtime exception. Preview dùng API mock và nền minh họa, không chạy
toàn bộ mô hình 3D hoặc LLM thật. Lượt kiểm tra bổ sung ngày 07/11/2026 xác nhận
khôi phục hội thoại ở cả hai giao diện, tách lịch sử A/B, Guest không gửi bearer,
giữ câu chuyện s3 và không có runtime exception. Production build cũng pass.
Contract lưu hội thoại và migration local hiện tại được ghi ở audit liên kết trên;
không thay camera/model, thêm dependency hoặc triển khai production.
