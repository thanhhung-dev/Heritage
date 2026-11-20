# Ma trận tích hợp Frontend / Backend

Đã đối chiếu `api/knowledge_library.py`, `schemas/knowledge_library.py`, `core/r2_library.py` và các router được gắn trong `apps/backend/app.py`. OpenAPI có bearer security cho mọi thao tác thư viện.

| Chức năng UI | Endpoint backend | Có API phù hợp | Trạng thái tích hợp |
|---|---|---|---|
| Danh sách thư mục/file | GET `/api/admin/knowledge/objects` | Có | Đã tích hợp hoàn chỉnh (`/admin/documents`, `/admin/documents/upload`) + unit test |
| Xin URL upload | POST `/api/admin/knowledge/upload-url` | Có | Đã tích hợp hoàn chỉnh (`KnowledgeUploadQueue`) + unit test |
| Xác nhận upload | POST `/api/admin/knowledge/uploads/{uploadId}/complete` | Có | Đã tích hợp hoàn chỉnh (`KnowledgeUploadQueue`) + unit test |
| Metadata storage | GET `/api/admin/knowledge/object` | Có | Đã tích hợp hoàn chỉnh (`/admin/documents/details`, `/admin/documents/metadata`) + unit test |
| Preview văn bản | GET `/api/admin/knowledge/preview` | Có | Đã tích hợp hoàn chỉnh (`/admin/documents/details`, xử lý 404/413/422) + unit test |
| Tải xuống | POST `/api/admin/knowledge/download-url` | Có | Đã tích hợp hoàn chỉnh (`downloadKnowledgeFile`) + unit test |
| Tạo thư mục | POST `/api/admin/knowledge/folders` | Có | Đã tích hợp hoàn chỉnh (`CreateFolderDialog`) + unit test |
| Xóa đúng file | DELETE `/api/admin/knowledge/objects` | Có | Đã tích hợp hoàn chỉnh (`DeleteFileDialog`, exact key body) + unit test |
| Lưu tiêu đề/vùng/loại/URL nguồn | Chưa có API gắn với object/revision thư viện mới | Không | Form chỉ đọc trên `/admin/documents/metadata`; không giả lưu draft |
| Submit/approve/request changes | Chưa có API review tài liệu | Không | Hiển thị chưa khả dụng trên `/admin/documents/review` & bộ lọc; vô hiệu hóa thao tác |
| Job ingestion/retry/chunks/extracted text | Chưa có API job cho object thư viện mới | Không | Hiển thị rõ trên `/admin/documents/ingestion` & `/admin/documents/details`; không giả job/phần trăm |
| Replace file theo revision | Chưa có contract thay thế có phiên bản an toàn | Không | Vô hiệu hóa kèm giải thích, không PUT đè key cũ |
| Tìm toàn bucket/tổng số file | ListObjectsV2 chỉ trả từng cấp/từng trang | Không | Tìm trên bản ghi đã tải; số đếm ghi rõ phạm vi |

Các request JSON dùng `apiFetch` và token từ cơ chế đăng nhập hiện có; chỉ truyền token tới backend. PUT R2 dùng XHR riêng, không có JWT, gửi toàn bộ requiredHeaders và File nguyên bản. Mọi tham số query dùng URLSearchParams; không đổi Unicode hoặc prefix/key có sẵn. Phiên upload bền vững và hoàn tất idempotent thuộc trách nhiệm backend.
