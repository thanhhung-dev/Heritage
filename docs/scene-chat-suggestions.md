# Gợi ý chat theo từng câu chuyện trong tour 3D

Ngày kiểm tra: 06/11/2026. Nhánh `feat/HER-area-locked-tour-guide`.

## Hành vi

Khi chọn s0, s1… ở thanh bên trái, chatbox đọc `currentScene.title`,
`currentScene.description` và `currentSceneKey` từ `useHeritageTour`. Bốn chip
gợi ý được tạo ngay ở frontend, không cần gọi AI để tải gợi ý.

Ví dụ với câu chuyện **“Bia đá và những nỗi niềm”** và mô tả nói về văn bia,
các chip gồm “Về Bia đá và những nỗi niềm”, “Ý nghĩa văn bia”, một câu hỏi theo
chủ đề tiếp theo trong dữ liệu và “Giải thích thêm”. Đổi sang câu chuyện về
kiến trúc/cảnh quan/nhân vật/bảo tồn sẽ đổi chủ đề tương ứng. Các mẫu câu hỏi
không tự thêm năm xây dựng, tiểu sử hoặc dữ kiện lịch sử.

Mỗi chip có nhãn ngắn để vừa cửa sổ chat; hover hoặc trình đọc màn hình đọc
được câu hỏi đầy đủ. Khi bấm, câu hỏi chứa tên câu chuyện và tên di sản đang
tham quan, đi cùng `active_area_id` và `scene_context` của cảnh đó qua API hiện
có `POST /api/chat`. Chatbox hiển thị dòng “Câu chuyện đang xem: sN · …” và
placeholder “Hỏi về câu chuyện này…”.

Gợi ý được tính từ dữ liệu của cảnh ở mỗi render, không lưu chung trong state
với phản hồi AI. Nếu đang hỏi s0 mà chuyển sang s3, phản hồi s0 vẫn hoàn tất lượt
hỏi cũ trong lịch sử, nhưng không được thay chip s3 bằng gợi ý cũ từ backend.
Trong lúc lượt hỏi cũ chưa xong, các chip mới hiển thị nhưng tạm disabled theo
trạng thái gửi chat hiện có. Lịch sử, bản nháp, vị trí và trạng thái mở cửa sổ
được giữ khi đổi cảnh trong cùng di sản. Đổi di sản/tài khoản vẫn reset theo
cơ chế khóa khu vực đã triển khai trước đó.

Nếu thiếu dữ liệu câu chuyện, widget dùng câu hỏi theo di sản hiện tại. Metadata
nêu một di sản khác đã biết cũng rơi về gợi ý của khu vực đang khóa. Alias check
phía frontend là lớp bảo vệ hiển thị; backend vẫn chịu trách nhiệm enforce
phạm vi, evidence và citations. Tour chưa đăng ký area tiếp tục bị khóa chat.

## Cách tự test trên giao diện

1. Chạy frontend/backend local theo cấu hình dự án. Dùng nhánh ở đầu tài liệu và
   backend hỗ trợ `active_area_id`. Mở tour có area đã đăng ký, ví dụ
   `/content/lang-tu-duc/s0` nếu dữ liệu local có slug này.
2. Mở chatbox ở s0. Kiểm tra tên câu chuyện và chip đầu khớp tiêu đề cảnh.
3. Chọn s1, s2, s3, s4 ở cột trái. Tên câu chuyện và các câu hỏi phải đổi ngay
   theo nội dung từng cảnh, không cần reload hoặc mở lại chatbox.
4. Tại câu chuyện văn bia, kiểm tra có chip “Ý nghĩa văn bia”. Hover chip để xem
   câu hỏi đầy đủ. Bấm chip và kiểm tra Network:
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
history. HTTP trong test dùng fetch mock; chưa chạy E2E trình duyệt hoặc đánh giá
câu trả lời thật của LLM. Không thêm dependencies, đổi API schema hoặc chạy migration.
