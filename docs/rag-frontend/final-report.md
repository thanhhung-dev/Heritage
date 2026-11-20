# Báo cáo Hoàn thiện Frontend Document Library & Tích hợp Knowledge R2

## A. Implemented screens

Các màn hình dưới đây đã được triển khai trong Next.js tại `apps/frontend/`, tham chiếu Figma `hyZGcP7zvicYLg3O7X2E2F`. Các phần thiếu API vẫn ở trạng thái chưa khả dụng; đây không phải xác nhận hoàn tất workflow review/ingestion.

| Màn hình Figma | Node ID | Route ứng dụng | Component chính |
|---|---|---|---|
| Document Library | `999:18448` | `/admin/documents` | `apps/frontend/features/knowledge/DocumentLibrary.tsx`, `FolderBrowser.tsx`, `FileDialogs.tsx` |
| Document Library — Upload Modal | `1001:13376` | `/admin/documents` (Modal) | `apps/frontend/features/knowledge/UploadModal.tsx`, `UploadControls.tsx` |
| Upload Documents | `1001:10456` | `/admin/documents/upload` | `apps/frontend/features/knowledge/UploadDocumentsPage.tsx`, `UploadControls.tsx` |
| Edit Document Metadata | `1001:10725` | `/admin/documents/metadata?key=...` | `apps/frontend/features/knowledge/EditDocumentMetadata.tsx` |
| Document Details | `999:20173` | `/admin/documents/details?key=...` | `apps/frontend/features/knowledge/DocumentDetails.tsx` |
| Pending Review | `1012:1574` | `/admin/documents/review` | `apps/frontend/app/(admin)/admin/documents/review/page.tsx` |
| Ingestion | `999:19206` | `/admin/documents/ingestion` | `apps/frontend/app/(admin)/admin/documents/ingestion/page.tsx` |

## B. Reused components

Dự án tái sử dụng tối đa hệ thống sẵn có của `apps/frontend`:
- **Admin Layout & Sidebar**: `apps/frontend/app/(admin)/admin/layout.tsx` (giữ nguyên cho tất cả route Admin khác, kích hoạt scoped Figma theme và menu cho nhóm `/admin/documents*`).
- **Authentication & Session**: `apps/frontend/lib/auth.ts` (`getAccessToken`, `getUser`, `clearAuth`, `AUTH_CHANGE_EVENT`) và route `/sign-in`.
- **HTTP Client**: `apps/frontend/lib/api.ts` (`apiFetch`, `parseApiResponse`, `ApiError`).
- **UI Primitives**: Ant Design v6 (`Layout`, `Menu`, `Table`, `Tree`, `Modal`, `Button`, `Input`, `Select`, `Progress`, `Dropdown`, `Tooltip`, `Avatar`, `Spin`, `App`).
- **Font Loader**: `apps/frontend/components/FontLoader.tsx`.

## C. Backend integration

Tích hợp đầy đủ 8 endpoint thuộc router `/api/admin/knowledge` trong `apps/frontend/services/knowledge.service.ts`:

| Operation | Method | Endpoint | Trạng thái |
|---|---|---|---|
| List objects & folders | `GET` | `/api/admin/knowledge/objects` | Đã tích hợp (`readKnowledgePage`, `useKnowledgeFolder`, `FolderBrowser`) |
| Request presigned upload URL | `POST` | `/api/admin/knowledge/upload-url` | Đã tích hợp (`KnowledgeUploadQueue.run`) |
| Complete staged upload | `POST` | `/api/admin/knowledge/uploads/{uploadId}/complete` | Đã tích hợp (`KnowledgeUploadQueue.run`, không gửi body, xác thực `status === "stored"`) |
| Read object HEAD metadata | `GET` | `/api/admin/knowledge/object?key=...` | Đã tích hợp (`DocumentDetails`, `EditDocumentMetadata`) |
| Preview UTF-8 text | `GET` | `/api/admin/knowledge/preview?key=...` | Đã tích hợp (`DocumentDetails`, hiển thị trong `<pre>` thuần văn bản, không thực thi HTML/Markdown) |
| Request download URL | `POST` | `/api/admin/knowledge/download-url` | Đã tích hợp (`downloadKnowledgeFile`, mở URL ngắn hạn không đính kèm JWT) |
| Create logical folder | `POST` | `/api/admin/knowledge/folders` | Đã tích hợp (`CreateFolderDialog`) |
| Delete exact object | `DELETE` | `/api/admin/knowledge/objects` | Đã tích hợp (`DeleteFileDialog`, gửi đúng `{"key": "..."}`) |

## D. RAG functionality

Ba trạng thái **Storage State**, **Review State** và **Ingestion State** được tách biệt tuyệt đối trên mọi màn hình:

1. **Working R2 storage features**:
   - Duyệt thư mục theo cấp thực tế từ bucket `knowledge-heritage` (không hardcode dữ liệu mẫu `heritage-documents-demo` hay thư mục giả).
   - Phân trang với `nextContinuationToken`, tự động bỏ qua trang rỗng do lọc marker/staging cho tới khi có dữ liệu hoặc `nextContinuationToken === null`, chống lặp token.
   - Upload trực tiếp lên Cloudflare R2 qua `XMLHttpRequest` (`upload.onprogress`), gửi nguyên bản `File` và toàn bộ `requiredHeaders`, không dùng `FormData`, không gửi JWT tới R2. Tiến độ chuyển byte có thể đạt 100% khi vẫn đang xác minh; chỉ complete thành công mới chuyển sang `Stored in R2`.
   - Khôi phục phiên bền vững khi mất phản hồi PUT (thử `complete` với `uploadId` hiện có trước khi PUT lại, xử lý 404/409/410/412/422/503).
   - Xem metadata HEAD thật, preview UTF-8 an toàn (xử lý 413 oversized, 404, 422), tải xuống qua signed URL, tạo thư mục, xóa chính xác 1 key có hộp thoại xác nhận.
2. **Working review/metadata features**:
   - Hiển thị đầy đủ metadata vật lý từ R2 HEAD (`name`, `key`, `bucket`, `contentType`, `size`, `lastModified`, `etag`, `metadata`).
3. **Working ingestion features**:
   - Hiển thị rõ ranh giới storage: file upload xong chỉ ở trạng thái `Stored in R2`, không tự động kích hoạt chunking/embedding hay đưa vào chatbot.
4. **Missing Backend contracts (đã khóa & giải thích trung thực trên UI)**:
   - Lưu nháp metadata biên tập (tiêu đề, vùng, loại tài liệu, citation URL) gắn với revision tài liệu R2.
   - Luồng duyệt tài liệu (`submit`, `approve`, `request-changes`).
   - API khởi chạy/theo dõi/retry job ingestion, xem extracted text và danh sách chunks cho object trong `knowledge-heritage`.
   - API thay thế file có phiên bản (`Replace file`).

## E. Tests

Kết quả rà soát ngày 21/11/2026 thay thế số liệu 19 test của báo cáo ban đầu:

| Kiểm tra | Kết quả thực tế |
|---|---|
| 5 file `tests/knowledge-*.test.ts`, runner tsx chuẩn | **23/23 PASS**, khoảng 1 giây |
| `tsc --noEmit --incremental --pretty false` | **PASS**, không lỗi kiểu |
| Lint phạm vi Knowledge và Admin layout/review/ingestion | **PASS**, không warning/error trong phạm vi sửa |
| Production build trên bản sao riêng trong `.catalog-test-runtime/knowledge-build-*`, dùng lại dependencies hiện có, không sao chép `.env*` | **PASS**, tạo 24 trang static; còn 2 warning `<img>` sẵn có ở `app/(tour)/content/[slug]/page.tsx` và khuyến nghị optional `sharp` |
| Backend storage + API + contract trong lượt audit | **31/31 PASS** |
| Backend PostgreSQL thực, database `test_*` loopback và schema dùng một lần | **5/5 PASS**, đã dọn tài nguyên test; không migrate database ứng dụng |
| Edge/CDP + API/R2 fixture loopback | **PASS**: XHR, signed headers, đổi đích upload, complete, tạo folder, preview an toàn, xóa đúng key, 6 trang ở desktop/mobile, modal mobile, rỗng/503/401/403; không JavaScript exception |

Lệnh FE chạy từ `apps/frontend`:

```powershell
.\node_modules\.bin\tsx.cmd --test tests/knowledge-api.test.ts tests/knowledge-folders.test.ts tests/knowledge-operations.test.ts tests/knowledge-upload-transport.test.ts tests/knowledge-upload-queue.test.ts
.\node_modules\.bin\tsc.cmd --noEmit --incremental --pretty false
```

Lệnh nhóm BE chạy từ root, bằng Python của virtualenv hiện có:

```powershell
python -X utf8 -m unittest apps.backend.tests.test_knowledge_library_storage apps.backend.tests.test_knowledge_library_api apps.backend.tests.test_knowledge_library_contract -v
```

Runner TS trong sandbox mặc định từng gặp `uv_os_get_passwd ENOMEM`; đã kiểm tra bằng runner transpile tạm và sau đó chạy lại runner tsx chuẩn thành công. Những lần browser harness đầu tiên lỗi do trùng cổng fixture/cách chờ modal đóng đã được sửa; lượt cuối đạt với 19 ảnh trong `.catalog-test-runtime/rag-figma/acceptance/`. Xem [cách chạy lại browser test](../../apps/frontend/tests/browser/README.md).

Không chạy lại toàn bộ regression ngoài phạm vi Knowledge, không ghi/xóa R2 production, không xác nhận CORS hay credentials của môi trường triển khai thật bằng fixture. Hướng dẫn test tay hiện hành: [manual-test-vi.md](manual-test-vi.md).

## F. Git history

- **Nhánh**: `feature/rag-document-library-fe-r2`
- **Chuỗi commit liên tục**:
  1. `d28d0b8` — `docs(rag): map frontend architecture and record continuous commit plan`
  2. `adb4280` — `feat(rag): define typed knowledge storage contracts`
  3. `5e90731` — `feat(rag): reuse authenticated API client for knowledge operations`
  4. `d299f61` — `test(rag): verify exact knowledge HTTP contracts and auth failures`
  5. `020d018` — `docs(rag): record Figma evidence API matrix and truthful feature gaps`
  6. `cde439a` — `feat(rag): validate upload names MIME and default size limits`
  7. `73d155c` — `feat(rag): add credential-free XHR upload with real progress and cleanup`
  8. `8ebf649` — `test(rag): cover direct transfer headers cancellation and staging conflicts`
  9. `742b7ba` — `feat(rag): share bounded upload queue with durable-session recovery`
  10. `c7d9e05` — `test(rag): verify upload lifecycle retries concurrency and cancellation`
  11. `88ef5c0` — `feat(rag-ui): add local Figma SVGs and scoped document-library design tokens`
  12. `de627e9` — `feat(rag-ui): reuse stored admin sessions and display actual account identity`
  13. `250ff35` — `feat(rag-ui): adapt existing admin layout to scoped Figma library styling`
  14. `766d95a` — `feat(rag): handle scoped folder pagination and browser navigation safely`
  15. `9448f5b` — `feat(rag-ui): protect library routes and share transient upload sessions`
  16. `fe9d3f8` — `feat(rag-ui): load folder pages with cancellation stale-response guards and refresh`
  17. `e2d621f` — `feat(rag-ui): integrate R2 folder browser and document library table`
  18. `0fd8cbc` — `feat(rag-ui): implement upload modal and full upload workspace sharing R2 queue`
  19. `9582b73` — `feat(rag-ui): integrate document details R2 metadata safe preview download and deletion`
  20. `b22bcdf` — `feat(rag-ui): connect supported R2 metadata and truthful review ingestion states`
  21. `ae6d25a` — `test(rag): add document library operations and upload progress coverage`
  22. `e07cbc7` — `fix(rag): decouple pure upload progress formatters from CSS module imports for node test runner`
  23. `a1444ba` — `docs(rag): document frontend integration and acceptance results`
  24. `9520104` — `style(rag-ui): align sidebar header account pill and Figma design tokens`
  25. `7c91b3e` — `style(rag-ui): redesign folder tree and document library table to match Figma layout`
  26. `bc38a9c` — `style(rag-ui): redesign upload modal and upload workspace to match Figma specs`
  27. `5b80d8a` — `style(rag-ui): redesign edit metadata and document details screens to match Figma specs`
  28. `cbd5cec` — `style(rag-ui): align pending review and ingestion screens with Figma structure`

### Bổ sung sau khi rà soát lại FE/BE

| Phát hiện và thay đổi | Commit chính | File/phạm vi |
|---|---|---|
| Staging lồng trong prefix cũ có thể bị lộ sau khi đổi scope thư viện | `6e68a4f` | `core/r2_library.py`, `services/knowledge_policy.py`, storage regression test |
| Đuôi file, hủy khi đang tạo phiên, tiến độ byte | `d10a4c0`, `67fd480` | file policy, upload queue, transport/queue tests |
| Xác thực DTO trả về và tách cache/queue theo tài khoản | `e448fe1` | response policy, service, provider/session, API/folder tests |
| Upload modal chỉ chạy các file thuộc folder đang xem; retry/start một hàng không chạy file khác | `0f9926c`, `7c1f941` | upload queue, modal/workspace, regression test |
| Theme tối kế thừa, logo bị cắt, menu sai khoảng cách, tìm kiếm sidebar chưa hoạt động | `5e79a98` | Admin layout, DesignIcon, shared CSS, library |
| Modal centered, folder picker thật, responsive và bo góc | `967f113`, `b5e1d39` | UploadModal, shared CSS |
| Không suy đoán Not run/Not indexed, region từ language/folder hoặc tên workspace | `7c1f941`, `4cfa60a` | library/details/metadata/review/ingestion/account |
| Chuyển key vẫn có thể thấy dữ liệu cũ; dialog giữ lỗi cũ | `d8129cd`, `5998e70` | details/metadata/FileDialogs |
| Đổi đích vẫn ở workspace; đúng nhóm hành động và tỷ lệ cột Figma | `64b36ac`, `9e6e62e` | FolderBrowser, upload page, details/metadata/CSS |
| Browser acceptance tái chạy được, gồm desktop/mobile và XHR thật vào fixture | `9c34243` | `apps/frontend/tests/browser/` |

Xem thay đổi đầy đủ bằng `git log a1444ba..HEAD --oneline` và `git diff a1444ba..HEAD --stat`. Không push hoặc deploy.

## G. Remaining issues & Deployment requirements

1. **Backend Advanced RAG Contracts**: Khi backend bổ sung các endpoint lưu metadata biên tập, duyệt revision và quản lý job ingestion cho bucket `knowledge-heritage`, có thể mở khóa các nút đang đặt ở trạng thái `disabled` trên `EditDocumentMetadata`, `PendingReviewPage`, `IngestionPage` và `DocumentDetails`.
2. **CORS khi triển khai**:
   - Backend FastAPI cần cho phép origin của Admin Frontend kèm header `Authorization`, `Content-Type`, `X-Correlation-ID`.
   - Bucket Cloudflare R2 `knowledge-heritage` cần cấu hình CORS cho phép phương thức `PUT`, `GET`, `HEAD` từ origin của Admin Frontend và cho phép các `AllowedHeaders` mà backend ký (`Content-Type`, `If-None-Match`, `x-amz-meta-*`). Tuyệt đối không dùng wildcard `*` kèm credentials.
3. **Giới hạn so với Figma**: giữ bố cục, token và SVG gốc, nhưng thay dữ liệu demo bằng dữ liệu thật/chưa khả dụng. Không xác nhận pixel-identical. Chưa tạo màn job details có job thật vì thiếu API định danh/trạng thái job. Font Roboto dùng FontLoader hiện có, phụ thuộc khả năng tải Google Fonts của trình duyệt.

## H. Manual acceptance

Các bước kiểm thử nghiệm thu toàn bộ luồng trên giao diện Admin:

1. **Đăng nhập Admin**:
   - Truy cập `/sign-in`, đăng nhập bằng tài khoản có `role = "admin"`.
2. **Duyệt Document Library (`/admin/documents`)**:
   - Mở `/admin/documents`. Kiểm tra sidebar hiển thị theme sáng chuẩn Figma, bucket `knowledge-heritage`, cây thư mục bên trái và bảng tài liệu bên phải.
   - Bấm vào từng thư mục trên cây hoặc breadcrumb để điều hướng; kiểm tra URL cập nhật `?prefix=...` và nút Back/Forward của trình duyệt hoạt động đúng.
   - Nhập từ khóa vào ô tìm kiếm để lọc các file đã tải; nếu thư mục còn trang tiếp theo, bấm **Load more** để tải thêm qua `nextContinuationToken`.
3. **Tạo thư mục mới**:
   - Bấm **Create folder**, nhập tên thư mục NFC Unicode hợp lệ, bấm xác nhận và kiểm tra danh sách tự làm mới.
4. **Upload qua Modal và Trang Upload riêng**:
   - Bấm **Upload documents** để mở Modal (hoặc **Open full upload page** để sang `/admin/documents/upload`).
   - Chọn các file `.md`, `.txt`, `.json` (<= 10 MiB). Kiểm tra file sai định dạng (ví dụ `.pdf`) bị từ chối ngay với thông báo rõ ràng.
   - Bấm **Upload N files** / **Start upload**: quan sát trạng thái chuyển từ `Preparing` → `Uploading` (% tiến độ thực từ XHR) → `Verifying upload` → `Stored in R2` kèm key thực tế.
5. **Xem chi tiết, Preview, Tải xuống và Xóa (`/admin/documents/details?key=...`)**:
   - Từ bảng tài liệu hoặc hàng đợi upload vừa xong, bấm vào tên file hoặc **View** để mở trang chi tiết.
   - Kiểm tra 3 thẻ trạng thái độc lập (`Storage status: Stored in R2`, `Review status: Unavailable`, `Ingestion status: Unavailable`), bảng thuộc tính HEAD và khung preview văn bản UTF-8 an toàn.
   - Bấm **View original / Download** để tải file qua presigned URL ngắn hạn.
   - Bấm **Edit metadata** để kiểm tra màn hình metadata (`/admin/documents/metadata?key=...`).
   - Bấm **Delete file**, kiểm tra hộp thoại hiển thị đúng tên file và exact key, xác nhận xóa và kiểm tra ứng dụng điều hướng về thư mục cha đã làm mới.
