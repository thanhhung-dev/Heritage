# Rà soát kiến trúc Document Library

Nhánh triển khai: `feature/rag-document-library-fe-r2`, bắt đầu từ `99efb23`; cây làm việc sạch trước task. Người dùng đã cho phép triển khai, kiểm thử và commit local liên tục. Nhịp commit theo yêu cầu mới là x3, mỗi commit là một phần có ý nghĩa; không push/deploy.

## Thành phần đang có

- Frontend: Next.js 14.2 App Router, React 18, TypeScript strict, npm; `apps/frontend/package.json` có `dev`, `build`, `lint`, `test` (node:test/tsx). CSS Modules là quy ước của repository. Ant Design 6 đã có sẵn; không thêm framework hoặc thư viện trạng thái mới.
- Layout Admin: `apps/frontend/app/(admin)/admin/layout.tsx`, sidebar 264px có thu gọn; đang dùng theme tối, header tổng quan và tên tài khoản giả lập. `/admin/documents` đã có liên kết trong menu nhưng chưa có trang thực thi. Giữ layout và các route Admin hiện có; bổ sung biến thể sáng chỉ cho nhóm route Document Library theo Figma.
- UI: Ant Design Button, Input, Modal, Select, Table, App/toast, ConfigProvider; các component `components/Button` và `components/Pagination` thiên về giao diện public, chưa đáp ứng hành động disabled/loading của Admin. Dùng Ant Design và CSS Modules để chỉnh token trong phạm vi thư viện.
- API dùng lại: `apps/frontend/lib/api.ts` có `apiFetch`, `buildApiUrl`, `parseApiResponse`, `ApiError`; `apps/frontend/config/api.ts` định nghĩa base URL. Không dùng cơ chế fallback sang backend khác cho thao tác có xác thực/ghi dữ liệu.
- Phiên đăng nhập: `apps/frontend/lib/auth.ts` lưu `heritage_access_token`, `heritage_user`, phát sự kiện `AUTH_CHANGE_EVENT`; trang `/sign-in` và `services/authService.ts` đã có. Dùng token chỉ với backend, kiểm tra phiên Admin và xử lý 401/403. Backend luôn là nơi quyết định quyền thật.
- Backend: FastAPI/Pydantic/SQLAlchemy; `api/knowledge_library.py`, `schemas/knowledge_library.py`, `services/knowledge_library.py`, `core/r2_library.py` đã có đủ 8 API storage và đã gắn trong `apps/backend/app.py`. Tái sử dụng, không xây engine RAG mới.

## Kế hoạch thực hiện

1. Đọc 5 màn hình Figma chính và các màn Pending review/Ingestion có liên quan; lưu bằng chứng thiết kế ngoài repository, ghi nhận component/token/asset thật.
2. Xây service TypeScript có DTO và dùng API client hiện có; xử lý prefix chính xác, token phân trang, lỗi và AbortSignal.
3. Tạo `/admin/documents`, `/admin/documents/upload`, `/admin/documents/details?key=...`, `/admin/documents/metadata?key=...`; dùng chung shell, điều hướng, danh sách thư mục tải theo nhu cầu và breadcrumb.
4. Dùng chung hàng đợi upload cho modal và trang riêng: kiểm tra phần mở rộng/MIME, XHR tiến độ thật, ký URL, PUT File, complete; giới hạn đồng thời, xử lý retry/cancel và không lộ JWT cho R2.
5. Nối HEAD/preview/download/create-folder/delete thật; có xác nhận xóa đúng key và làm mới danh sách. Tìm kiếm chỉ trên các bản ghi đã tải, không giả tìm toàn bucket.
6. Metadata biên tập/review/ingestion/replacement chưa có API phù hợp cho thư viện mới: giữ bố cục Figma, giải thích trạng thái không khả dụng và vô hiệu hóa thao tác tương ứng, không giả trạng thái hoặc thành công.
7. Kiểm thử HTTP/service/upload, trình duyệt desktop/mobile với dữ liệu giả lập ở ranh giới HTTP; chạy typecheck/lint/build và bộ test backend hiện có. R2 thật chỉ kiểm tra đọc. Viết tài liệu và hướng dẫn test tay bằng tiếng Việt; giao diện theo tiếng Anh của Figma.

## Giới hạn tích hợp đã xác nhận

`api/admin_knowledge.py` cũ chỉ dành cho loopback/local, không có xác thực và chưa được gắn vào app. Không mở router đó để lấy metadata/chunks và không dùng endpoint nội bộ cũ từ frontend production. `admin_catalog.py` quản lý nội dung di sản, không phải metadata/review tài liệu R2. Không suy diễn trạng thái review/ingestion từ việc object tồn tại. Phạm vi bucket luôn do backend quyết định là `knowledge-heritage`; không đổi `heritage` hoặc `heritage-scene`.
