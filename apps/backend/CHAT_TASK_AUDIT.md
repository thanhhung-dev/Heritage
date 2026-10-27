# Chat Backend — kiểm tra và hoàn thiện task

Ngày kiểm tra: **2026-10-28**, nhánh `feat/HER-chat-backend-conversation-management`.

## Kết luận

Các phần thiếu trong contract, context và khôi phục lịch sử đã được triển khai
và kiểm thử. Phần API/code của tám mục trong checklist đã có đầy đủ luồng xử lý.
Môi trường localhost hiện trả phản hồi **mô phỏng Development**: chưa có package
`sentence_transformers` trong virtualenv kiểm thử, LLM local chưa sẵn sàng và
không có Google API key. Vì vậy, kiểm thử này không xác nhận chất lượng câu trả
lời của model thật.

## Đối chiếu checklist

| Mục | Kết quả và bằng chứng |
| --- | --- |
| Finalize request/response cho hai giao diện | Backend hỗ trợ chat page và embedded chat qua `POST /api/chat/message`; compatibility `POST /api/chat` giữ HTTP 200 và `sources`. DTO tập trung trong `schemas/chat.py`, cùng trường outcome và kiểm tra đầu vào. |
| Nối AI pipeline; trả answer/citations/clarification/abstention | Tiếp tục dùng retrieval, source gate và llama.cpp hiện có. `needs_user_choice`, `suggestions`, corrections, `abstained` và `abstention_reason` được truyền tới response; không bị mất ở bước chuyển sang persisted response. Clarification được trả khi pipeline yêu cầu làm rõ; không phải bằng chứng model thật đã được đánh giá trên mọi câu mơ hồ. |
| Heritage/scene và bounded conversation context | Context UI tối đa 2.000 ký tự mỗi trường. History tối đa 6 messages / 6.000 ký tự, mỗi message tối đa 2.000. History của cuộc trò chuyện đã lưu lấy từ DB sau ownership check; guest có thể gửi context client. History chỉ giúp hiểu câu hỏi, không trở thành citation evidence. |
| Account-owned conversation và persistence | Lưu atomically conversation, hai tin nhắn, citations và response metadata. Migration `20261028_chat_outcomes` đã áp dụng trên Postgres local. Thứ tự citations được giữ khi khôi phục lịch sử. |
| Conversation listing và message history | GET list theo chủ sở hữu, newest-first; GET messages oldest-first, pagination có giới hạn; khôi phục cả metadata clarification/abstention/corrections. |
| Ownership và guest behavior | JWT không hợp lệ trả 401; khác chủ/guest truy cập saved ID trả 403. Guest gửi mới với `conversation_id=null`; UUID không phải credential. Context client không cấp quyền đọc lịch sử và không được ghi thành các tin nhắn lịch sử giả. |
| Timeout, service failure, persistence error | Hai API có deadline AI 30 giây. Rollback khi lỗi; không lưu câu trả lời trống hoặc bị truncate. Giữ error detail an toàn. Local fallback có nhãn rõ và bị tắt ngoài `local`. |
| Account isolation, restoration, integration tests | Tests đi qua router, JWT thật, RAG assembly, LLM HTTP adapter và SQLAlchemy persistence. Đã kiểm tra thêm qua HTTP localhost với Postgres thật và hai tài khoản tạm. |

## Các phần đã bổ sung

- Chuẩn hóa các outcome fields giữa hai response và history DTO.
- Thêm `chat_message.response_metadata`; giữ source evidence gate, đồng thời
  cho phép clarification được đánh dấu rõ mà không cần bịa citations.
- Đưa history vào request llama.cpp/Gemini, giới hạn dữ liệu đọc và kích thước
  prompt context. Không cho client thay thế history của hội thoại đã lưu.
- Dùng câu hỏi user trước để bổ nghĩa các câu follow-up tham chiếu; câu hỏi đổi
  chủ đề rõ ràng giữ truy vấn retrieval riêng.
- Tự bổ nghĩa bằng title/region của published heritage khi đã có `heritage_id`.
  Widget cần gửi `scene_context` hiện tại mỗi lượt.
- Kiểm tra model output rỗng/truncated, giữ transaction atomic và thứ tự citations.
- Đọc `.env` trước khi import auth để JWT dùng cấu hình đã cung cấp.
- Bổ sung launcher còn thiếu và sửa wrappers Windows để tìm được virtualenv.
- Sửa fixture SQLite của admin tests để không giữ pooled file handles giữa các
  event loops trên Windows.

## Kết quả kiểm thử

- **89 tests thuộc Chat / LLM adapter / prompt pass**, không có lỗi trong các
  module này. Các kiểm thử tập trung cũng chạy thành công những subtests về
  invalid auth/context, isolation và các trạng thái model output.
- Toàn bộ Backend với OpenSearch thật: **213 passed, 55 subtests passed,
  8 failed, 0 skipped** (58,76 giây).
- Tám lỗi còn lại thuộc `test_profile_consent.py`, do danh tính Profile UUID cũ
  không khớp account integer và Profile GET đọc bảng `profiles` chưa tồn tại.
  Đây là phần migration Profile đã được nêu trong báo cáo trước, không được
  tự chuyển đổi hoặc xóa dữ liệu trong task Chat này.

### HTTP localhost + Postgres thật

Đã chạy API bằng chính launcher Windows mới trên cổng kiểm thử `8012`:

- Register/login hai tài khoản tạm qua API; token được kiểm chứng bởi Backend.
- Chat A trả 201; A đọc lại lịch sử và tiếp tục cùng conversation ID.
- B đọc/xóa conversation A trả 403; list A không có conversation B.
- Guest context trả 201; guest không được tiếp tục bằng saved UUID; JWT sai trả 401.
- Compatibility chat trả 200 với outcome fields.
- Chủ sở hữu xóa conversation trả 204, đọc lại trả 404; conversation B vẫn đọc được.
- Phản hồi live có `answer_type=development_mock`; `/api/health` trả 503 với
  `model_ready=false` như đúng tình trạng dịch vụ AI.

Các account/conversation chỉ được tạo cho lần kiểm thử đã được xóa theo đúng ID
và owner; server tạm được dừng sau kiểm tra.

## Xác nhận QA hoàn tất cho Task 2

Ngày xác nhận: **2026-10-28**. Người kiểm thử thủ công: **Cao Văn Khoa**.
Phạm vi xác nhận là **Complete the Chat Backend and Account-Based Conversation
Management**. Cao Văn Khoa xác nhận đã hoàn thành manual QA và automated QA;
các trường hợp ownership isolation, Guest, cascade delete và fallback đều pass.
Đây là xác nhận của người kiểm thử trong phiên làm việc, không thay thế bằng
chứng đánh giá chất lượng model thật.

| Nhóm chức năng | Kết quả QA được xác nhận |
| --- | --- |
| Contract và gửi chat | Request hợp lệ được xử lý; response có answer, citations và outcome fields; request sai bị từ chối. |
| Context | Hỗ trợ heritage/scene, giới hạn conversation context và lấy history đã lưu sau ownership check. |
| Persistence và history | Lưu user/assistant/citations, list hội thoại theo account và khôi phục lịch sử để tiếp tục. |
| Account isolation | User B không thể đọc, gửi thêm hoặc xóa hội thoại User A. |
| Guest và authentication | Guest tạo hội thoại với account null; saved UUID không cấp quyền truy cập; JWT sai bị từ chối. |
| Xóa hội thoại | Chủ sở hữu xóa thành công; messages/citations bị cascade; dữ liệu account khác được giữ. |
| Resilience | Timeout, lỗi inference/persistence và local fallback có test kiểm chứng; không commit dữ liệu dở dang. |

### Bằng chứng automated và HTTP đã ghi nhận

- Bộ bốn file Chat API/conversation/integration/fallback đã chạy thành công:
  **76 passed, 31 subtests passed**.
- Sau sửa auth, lệnh lọc `auth or register` trong `apps/backend/tests/` có
  **20 passed, 9 subtests passed**, gồm 10 tests auth regression mới.
- Bộ conversation và integration sau sửa auth có **50 passed,
  19 subtests passed**. Các nhóm này có test trùng với các lượt chạy trên;
  không cộng số lượng thành tổng tests riêng biệt.
- Kiểm tra HTTP thực tế trên cổng `8000` với Postgres local sau khi restart
  server: register **201**, duplicate email/username **400**, invalid input
  **422**, login/me **200**, account-owned chat **201**, list **200**, delete
  conversation kiểm thử **204**. Dữ liệu kiểm thử tạm đã được dọn theo đúng ID.
- Lỗi register `NoReferencedTableError` do server cũ giữ ORM mapping trước bản
  sửa đã được xử lý; mapping trực tiếp `AccountRole.id` và regression tests
  được ghi nhận tại commit `a7ac404`.

Các kết quả full Backend/Profile ở mục trước là báo cáo của lượt chạy trước,
không phải tuyên bố toàn bộ Backend đều pass trong lần chốt Task 2 này. Local
AI đã kiểm tra dùng development fallback; model/corpus thật cần đánh giá riêng.
Không chạy lại full suite, migration hoặc thay đổi cấu hình khi ghi nhận sign-off.

## Chạy localhost

Từ thư mục `Heritage`, giữ Postgres local hoạt động và chạy:

```powershell
.\start-backend.ps1 -Port 8000
```

Hoặc:

```bat
start-backend.bat --port 8000
```

- Swagger: `http://127.0.0.1:8000/docs`.
- API mới: `POST http://127.0.0.1:8000/api/chat/message`.
- FE hiện cấu hình `NEXT_PUBLIC_API_URL=http://localhost:8000/api`.
- Cấu hình request/response, mẫu context và pagination: [CHAT_API.md](CHAT_API.md).
- Chạy lại Search integration tests: [hướng dẫn OpenSearch](../../docs/opensearch-local-tests.md).

Muốn có câu trả lời AI thật, cần cài đủ dependency/model BGE, có dữ liệu passage
đã index và khởi động llama.cpp theo cấu hình `LLAMA_SERVER_URL`. Với local
fallback, `GOOGLE_API_KEY` có thể dùng để thử Gemini; key thật không đưa vào Git.
Các automated tests dùng HTTP/retrieval stubs để kiểm tra contract và isolation,
không thay thế việc đánh giá chất lượng model/corpus thật.
