# Ma trận tích hợp Frontend / Backend

Đã đối chiếu `api/knowledge_library.py`, `schemas/knowledge_library.py`, `core/r2_library.py` và các router được gắn trong `apps/backend/app.py`. OpenAPI có bearer security cho mọi thao tác thư viện.

| Chức năng UI | Endpoint backend | Có API phù hợp | Trạng thái tích hợp |
|---|---|---|---|
| Danh sách thư mục/file | GET `/api/admin/knowledge/objects` | Có | Service TypeScript đã có; UI đang triển khai |
| Xin URL upload | POST `/api/admin/knowledge/upload-url` | Có | Service TypeScript đã có; controller đang triển khai |
| Xác nhận upload | POST `/api/admin/knowledge/uploads/{uploadId}/complete` | Có | Service TypeScript đã có; controller đang triển khai |
| Metadata storage | GET `/api/admin/knowledge/object` | Có | Service TypeScript đã có; UI đang triển khai |
| Preview văn bản | GET `/api/admin/knowledge/preview` | Có | Service TypeScript đã có; UI đang triển khai |
| Tải xuống | POST `/api/admin/knowledge/download-url` | Có | Service TypeScript đã có; UI đang triển khai |
| Tạo thư mục | POST `/api/admin/knowledge/folders` | Có | Service TypeScript đã có; UI đang triển khai |
| Xóa đúng file | DELETE `/api/admin/knowledge/objects` | Có | Service TypeScript đã có; UI đang triển khai |
| Lưu tiêu đề/vùng/loại/URL nguồn | Chưa có API gắn với object/revision thư viện mới | Không | Form chỉ đọc; không giả lưu draft |
| Submit/approve/request changes | Chưa có API review tài liệu | Không | Hiển thị chưa khả dụng, vô hiệu hóa thao tác |
| Job ingestion/retry/chunks/extracted text | Chưa có API job cho object thư viện mới | Không | Không giả job/phần trăm, không tự chạy ingestion |
| Replace file theo revision | Chưa có contract thay thế có phiên bản an toàn | Không | Vô hiệu hóa, không PUT đè key cũ |
| Tìm toàn bucket/tổng số file | ListObjectsV2 chỉ trả từng cấp/từng trang | Không | Tìm trên bản ghi đã tải; số đếm ghi rõ phạm vi |

Các request JSON dùng `apiFetch` và token từ cơ chế đăng nhập hiện có; chỉ truyền token tới backend. PUT R2 dùng XHR riêng, không có JWT, gửi toàn bộ requiredHeaders và File nguyên bản. Mọi tham số query dùng URLSearchParams; không đổi Unicode hoặc prefix/key có sẵn. Phiên upload bền vững và hoàn tất idempotent thuộc trách nhiệm backend.
