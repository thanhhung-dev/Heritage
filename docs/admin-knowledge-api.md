# Admin quản lý kho tri thức R2 — API local và thiết kế tổng quan

> Đã triển khai backend CRUD folder/tài liệu và upload/thay file ở `/api/admin`.
> Chưa làm UI, auth cho router này, ingestion job, dashboard, thành viên hay audit.
> Phần “Thiết kế tổng quan” phía dưới giữ lại định hướng cho các giai đoạn sau.

## Hướng dẫn chạy backend hiện tại

### Cài đặt và cấu hình

Chạy từ thư mục gốc dự án:

```bash
uv pip install --python .venv/bin/python -r apps/backend/requirements.txt
```

Giữ nguyên credentials R2 hiện có trong `.env`. Các biến được sử dụng:

```dotenv
APP_ENVIRONMENT=local
R2_ENDPOINT_URL=https://YOUR-ACCOUNT-ID.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=knowledge
R2_KNOWLEDGE_PREFIX=curated/
R2_UPLOAD_MAX_BYTES=26214400
```

Bucket hiện có prefix `curated/` và `processed/`, nên mặc định API chỉ quản lý
`curated/`. Không dùng `knowledge/` trong ví dụ thiết kế bên dưới trừ khi đã đổi
`R2_KNOWLEDGE_PREFIX` tương ứng. Prefix không được rỗng, phải kết thúc bằng `/`.
Không copy cấu hình mẫu đè credentials thật và không commit `.env`.

List/create/rename/delete folder không cần PostgreSQL. Các API documents và
uploads cần PostgreSQL để lưu metadata và phiên upload qua các lần restart:

1. Chuẩn bị PostgreSQL local và đặt `DATABASE_URL=postgresql+psycopg://...` đúng
   host/port/database trong `.env`.
2. Chạy lệnh sau để tạo **chỉ hai bảng mới**, không drop/alter bảng cũ:

```bash
.venv/bin/python -m apps.backend.db.init_knowledge --env-file .env
```

3. Khởi động backend; không dùng `DATABASE_URL=''` từ lệnh chat-only cũ:

```bash
LANGFUSE_ENABLED=false OTEL_TRACING_ENABLED=false GRAPHRAG_ENABLED=false \
  .venv/bin/python -m uvicorn apps.backend.app:app \
  --host 127.0.0.1 --port 8000 --reload
```

Mở <http://127.0.0.1:8000/docs>, tìm nhóm **Admin knowledge (LOCAL ONLY, no auth)**.
Chỉ nhận kết nối loopback với host localhost/127.0.0.1/::1; môi trường
staging/production bị chặn. Origin trình duyệt phải là chính backend hoặc có
trong `CORS_ORIGINS`. Đây chưa phải xác thực: không public/tunnel/reverse-proxy
API này ra Internet và không dùng nó như API nhiều thành viên trước khi có auth.

### Endpoint đã triển khai

| Method | Endpoint (sau `/api/admin`) | Hành vi hiện tại |
| --- | --- | --- |
| GET | `/storage/entries?prefix=curated/&limit=100&cursor=...` | Trả `prefix`, `entries`, `next_cursor`; mỗi entry có `kind`, `name`, `key`; file có thêm dung lượng/ngày cập nhật. Không quét đệ quy. |
| POST | `/storage/folders` | `{ "parent_prefix": "curated/hue/", "name": "thien-mu" }`; tạo marker, trả 201. |
| PATCH | `/storage/folders` | `{ "prefix": "curated/hue/thien-mu/", "name": "linh-mu" }`; chỉ đổi tên folder rỗng. |
| DELETE | `/storage/folders?prefix=curated/hue/linh-mu/` | Chỉ xóa marker folder rỗng; không xóa đệ quy hay folder gốc. |
| GET | `/documents?status=uploaded&limit=50&cursor=...` | Danh sách metadata, trả `items`, `next_cursor`. |
| POST | `/documents` | Đăng ký file đã có trên R2 bằng `object_key`, kèm metadata tùy chọn; không upload lại. |
| GET | `/documents/{id}` | Chi tiết metadata và bản file hiện tại. |
| PATCH | `/documents/{id}` | Sửa `title`, `region`, `source_type`, `source_url`; không nhận key/bucket/status tùy ý. |
| DELETE | `/documents/{id}` | Xóa object hiện tại và đánh dấu metadata đã xóa; chặn tài liệu đã index/đang xử lý. |
| GET | `/documents/{id}/download-url` | URL tải dạng attachment, hiệu lực 600 giây. |
| GET | `/documents/{id}/chunks?limit=50&cursor=...` | Chưa index trả danh sách rỗng; đã index đọc chunk từ OpenSearch, không trả vector. |
| POST | `/uploads` | Tạo phiên và URL PUT hiệu lực 600 giây, trả 201. |
| POST | `/uploads/{upload_id}/complete` | Kiểm tra file, cố định bản file và tạo/cập nhật document; gọi lại không tạo thêm tài liệu. |

`GET /documents` nhận status `uploaded`, `indexed`, `processing`, `failed`.
Upload mới thành công có status `uploaded`; chưa có worker tự thay đổi status.
Đăng ký file cũ kiểm tra tham chiếu ở OpenSearch để xác định đã index hay chưa.

### Ví dụ đọc folder

```bash
curl -fsS 'http://127.0.0.1:8000/api/admin/storage/entries?prefix=curated/&limit=100'
```

Dùng `key` của entry folder làm `prefix` lần tiếp theo. Truyền lại
`next_cursor` nguyên vẹn với cùng prefix để đọc trang kế tiếp. Mỗi loại list có
cursor riêng; không dùng cursor R2 cho documents hoặc chunks.

### Upload file mới

1. Tạo phiên (ví dụ file TXT UTF-8 đúng 18 byte; thay số bằng kích thước file thật):

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/admin/uploads \
  -H 'Content-Type: application/json' \
  -d '{"parent_prefix":"curated/hue/","filename":"lich-su.txt","content_type":"text/plain","size_bytes":18}'
```

2. Lấy `upload_url`, `upload_id` từ response. PUT byte của file lên URL được cấp,
   dùng đúng Content-Type được trả về:

```bash
curl --fail-with-body -X PUT "$UPLOAD_URL" \
  -H 'Content-Type: text/plain' --data-binary @./lich-su.txt
curl -fsS -X POST "http://127.0.0.1:8000/api/admin/uploads/$UPLOAD_ID/complete"
```

3. Response complete chứa `id` của tài liệu. PATCH metadata bằng ID đó:

```bash
curl -fsS -X PATCH "http://127.0.0.1:8000/api/admin/documents/$DOCUMENT_ID" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Lịch sử chùa Thiên Mụ","region":"hue","source_type":"official","source_url":"https://example.org/thien-mu"}'
```

Để thay file, thêm `document_id` vào payload tạo phiên upload rồi thực hiện
PUT/complete như trên. Hai phiên thay cùng một bản tài liệu không được âm thầm
ghi đè nhau: phiên dùng revision cũ trả 409. Bản file trước được giữ trên R2.

### File đã có trên R2

List R2 không tự ghi metadata hay tạo document. Muốn quản lý một file đã có:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/admin/documents \
  -H 'Content-Type: application/json' \
  -d '{"object_key":"curated/hue/thien-mu/lich-su.md","title":"Lịch sử chùa Thiên Mụ","region":"hue"}'
```

Key phải tồn tại và nằm trong prefix cho phép; đăng ký trùng trả 409. Đăng ký và
xóa tài liệu cần OpenSearch sẵn sàng để kiểm tra tham chiếu trong index đang cấu
hình; không kết nối được thì trả 503, không suy ra “không có chunk”. Không kiểm
tra mọi index lịch sử hay hệ thống bên ngoài. Không sửa/xóa nguồn trực tiếp trên
R2 cùng lúc admin đang chạy ingestion hoặc CRUD.

### Giới hạn và bảo toàn dữ liệu

- Hỗ trợ `.txt` → `text/plain`, `.md` → `text/markdown`, `.html` → `text/html`,
  `.pdf` → `application/pdf`; tên file không chứa dấu phân tách đường dẫn.
- Complete đối chiếu dung lượng, content type và 4 KiB đầu (PDF header hoặc
  UTF-8 không chứa NUL). Đây không phải antivirus hay kiểm tra toàn bộ nội dung;
  vẫn cần kiểm tra khi trích text. Giới hạn mặc định 25 MiB được kiểm tra ở API
  và complete, không phải hạn mức storage tuyệt đối cho presigned PUT.
- Upload vào prefix nội bộ cố định `_admin_uploads/`, sau complete copy có điều
  kiện ETag sang key mới trong `curated/`. Dùng lại URL PUT cũ không thể sửa file
  đã hoàn tất. Key R2 cần quyền list/read/write/copy/delete tương ứng.
- Staging và file trước khi thay chưa có job tự dọn. Cần chính sách cleanup
  riêng; không tự xóa object cũ vì có thể còn được index hoặc nguồn khác dùng.
- R2 và PostgreSQL không có transaction chung: lỗi sau khi copy có thể để lại
  object chưa được đăng ký. Complete có thể retry; không hứa atomic hai hệ thống.
- Không rename/move folder có file. Không sửa metadata tài liệu đã index hoặc
  đang xử lý; không xóa nguồn còn được index đang cấu hình tham chiếu.
- Chưa chạy ingestion hay đồng bộ chunk cũ. Thay file giữ nguyên object cũ,
  nhưng bản mới chỉ có trạng thái uploaded; không được coi chatbot đã cập nhật.
- Đối với browser upload, cần CORS R2 cho origin frontend và method PUT cùng
  header Content-Type. Backend không tự thay cấu hình bucket thật.

### Kiểm thử không ghi R2 thật

```bash
uv pip install --python .venv/bin/python aiosqlite==0.22.1 coverage
OPENSEARCH_TEST_URL=http://127.0.0.1:9200 LANGFUSE_ENABLED=false \
  .venv/bin/python -m unittest apps.backend.tests.test_admin_knowledge \
  apps.backend.tests.test_opensearch
```

API tests dùng database SQLite tạm và S3 giả lập, không sử dụng credentials thật.
OpenSearch tests dùng index ngẫu nhiên `heritage-test-*` rồi dọn riêng index đó.

---

## Thiết kế tổng quan (bao gồm chức năng chưa triển khai)

## 1. Mục tiêu và phạm vi

Cho phép các thành viên quản trị tin cậy quản lý tài liệu tri thức trên
Cloudflare R2: duyệt folder, tạo folder, upload file, cập nhật metadata và
chạy ingestion để chatbot sử dụng nội dung mới.

Không có bước phê duyệt hay trạng thái `pending review`. Không có menu
“Chờ duyệt”, “Phiên bản dữ liệu” hoặc “Hỏi thử”. Việc kiểm tra text được thực
hiện ngay trong chi tiết tài liệu trước khi người quản trị chạy ingestion.

### Sidebar

```text
HERITAGE ADMIN

  Dashboard
  Kho tài liệu
  Ingestion

QUẢN TRỊ
  Thành viên
  Nhật ký hoạt động

────────────────────
  Về trang Chat
  Tài khoản / Đăng xuất
```

| Màn hình | Chức năng |
| --- | --- |
| Dashboard | Số tài liệu, dung lượng, trạng thái xử lý và job gần đây; dùng số liệu thật. |
| Kho tài liệu | Cây folder R2, breadcrumb, upload, xem/tải file và chỉnh metadata. |
| Ingestion | Tạo job, theo dõi tiến trình, xem lỗi và chạy lại. |
| Thành viên | Tạo, cập nhật và khóa tài khoản quản trị. |
| Nhật ký hoạt động | Ai thao tác, thao tác gì, đối tượng, thời gian và kết quả. |

## 2. Phân chia trách nhiệm

| Thành phần | Trách nhiệm |
| --- | --- |
| Next.js Admin | Giao diện và upload trực tiếp bằng URL được cấp. |
| FastAPI | Xác thực, phân quyền, metadata, API R2 và điều phối ingestion. |
| R2 | Lưu tài liệu gốc. |
| PostgreSQL | Tài khoản, session, metadata, thông tin upload/job và audit. |
| BGE-M3 | Tạo embedding cho chunk và câu hỏi. |
| OpenSearch | Lưu text chunk, vector, metadata và phục vụ retrieval. |

```text
Admin → FastAPI: yêu cầu upload
      ← URL upload ngắn hạn
Admin → R2: gửi file trực tiếp
Admin → FastAPI: xác nhận upload
FastAPI → R2: kiểm tra object → lưu metadata vào PostgreSQL

Admin → FastAPI: tạo ingestion job
Worker → R2 → trích text → chia chunk → BGE-M3 → OpenSearch
Chatbot → OpenSearch → context → LLM → answer
```

Upload thành công không đồng nghĩa chatbot đã biết tài liệu mới. Ingestion
phải chạy nền, không giữ request upload chờ embedding.

R2 không có thư mục thật: folder là prefix, ví dụ
`knowledge/hue/thien-mu/`. Folder rỗng có thể biểu diễn bằng object marker kết
thúc bằng `/`; ingestion phải bỏ qua marker này. Cây folder nằm trong màn hình
Kho tài liệu, không nằm trong sidebar chính.

## 3. Quy ước API và bảo mật

- Prefix: `/api/admin`. Tất cả endpoint ngoài login yêu cầu xác thực; quyền
  được kiểm tra tại backend, không chỉ bằng ẩn nút giao diện.
- Có thể dùng session cookie `HttpOnly`; cấu hình `Secure` khi triển khai HTTPS,
  `SameSite` phù hợp và bảo vệ CSRF cho request thay đổi dữ liệu. Nếu frontend
  gọi khác origin, cần cấu hình cookie, CORS và credentials tương ứng.
- R2 access key chỉ ở backend, không đặt trong biến `NEXT_PUBLIC_*`.
- Backend tự tạo/kiểm tra object key và chỉ cho phép thao tác trong prefix
  tri thức được cấu hình, ví dụ `knowledge/`.
- List API dùng cursor phân trang; không tải toàn bộ bucket trong một request.
- Giới hạn loại file, dung lượng, thời hạn upload và quyền tải file riêng tư.
  Kiểm tra ở UI chỉ hỗ trợ trải nghiệm, không thay thế xác thực phía server.
- Log/audit không lưu session token, secret hoặc presigned URL.
- Không ghi đè hoặc xóa dữ liệu âm thầm. Tách quyền quản lý tài khoản khỏi quyền
  quản lý tài liệu nếu không muốn mọi thành viên có thể cấp/thu hồi tài khoản.

## 4. Đăng nhập và tài khoản

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| POST | `/api/admin/auth/login` | Đăng nhập và cấp session. |
| POST | `/api/admin/auth/logout` | Đăng xuất và thu hồi session. |
| GET | `/api/admin/auth/me` | Tài khoản và quyền hiện tại. |

Mật khẩu phải được hash, không lưu plaintext. Khóa tài khoản cần vô hiệu hóa
quyền truy cập của session hiện hữu. Login cần giới hạn thử sai và thông báo lỗi
không tiết lộ tài khoản có tồn tại hay không.

## 5. Kho tài liệu và folder

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| GET | `/api/admin/storage/entries?prefix=knowledge/hue/&cursor=...` | Folder/file trực tiếp trong prefix, có phân trang. |
| POST | `/api/admin/storage/folders` | Tạo folder rỗng. |
| GET | `/api/admin/documents?status=indexed&cursor=...` | Danh sách tài liệu theo metadata/trạng thái. |
| GET | `/api/admin/documents/{id}` | Metadata, file hiện tại và trạng thái xử lý. |
| PATCH | `/api/admin/documents/{id}` | Sửa tiêu đề, khu vực, loại tài liệu, URL nguồn… |
| GET | `/api/admin/documents/{id}/download-url` | Cấp link tải/xem file ngắn hạn. |
| GET | `/api/admin/documents/{id}/chunks?cursor=...` | Xem chunk sau xử lý; trước khi xử lý thì chưa có chunk. |

`storage/entries` phản ánh object thực tế trên R2. `documents` phản ánh tài liệu
đã có metadata trong hệ thống. File có sẵn trên R2 nhưng chưa đăng ký có thể
hiển thị “chưa quản lý”, không mặc định đã index. Luồng đăng ký các file có sẵn
cần được bổ sung riêng nếu cần; API upload dưới đây dành cho file tải qua admin.

### Ví dụ tạo folder

```json
{
  "parent_prefix": "knowledge/hue/",
  "name": "thien-mu"
}
```

Backend kiểm tra tên và tạo marker `knowledge/hue/thien-mu/`, không nhận một key
tùy ý rồi ghi thẳng vào R2.

### Metadata tài liệu

- Tiêu đề, khu vực, loại tài liệu, URL nguồn trích dẫn.
- ID tài liệu ổn định; tên file và object key của bản file hiện tại.
- Dung lượng, định dạng, người upload và thời gian cập nhật.
- Trạng thái xử lý, job gần nhất và bản nội dung đã index.

URL nguồn trích dẫn khác URL tải R2: không lưu signed URL hết hạn làm nguồn.
Thay metadata có tham gia embedding hoặc citation có thể cần cập nhật index;
PATCH metadata không được báo rằng OpenSearch đã cập nhật nếu chưa xử lý.

## 6. Upload và thay file

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| POST | `/api/admin/uploads` | Tạo phiên upload và cấp presigned URL. |
| POST | `/api/admin/uploads/{upload_id}/complete` | Kiểm tra object, đăng ký file và metadata kỹ thuật. |

### Yêu cầu tạo upload

```json
{
  "parent_prefix": "knowledge/hue/thien-mu/",
  "filename": "lich-su.pdf",
  "content_type": "application/pdf",
  "size_bytes": 2097152
}
```

### Response đề xuất

```json
{
  "upload_id": "uuid",
  "method": "PUT",
  "upload_url": "https://...",
  "headers": {
    "Content-Type": "application/pdf"
  },
  "expires_at": "2026-10-20T05:00:00Z"
}
```

### Luồng hoàn tất

1. UI gọi `POST /uploads`.
2. UI PUT file lên URL R2, sử dụng các header đã được trả về.
3. UI gọi `POST /uploads/{upload_id}/complete`.
4. Backend kiểm tra phiên upload thuộc người có quyền, object tồn tại, kích
   thước và nội dung phù hợp; không chỉ tin filename/content type phía client.
5. Backend tạo/cập nhật document và trả `document_id` để UI mở trang chi tiết.

Complete cần có tính idempotent: gửi lại không tạo nhiều document cho cùng
upload. Object không hợp lệ không được đưa vào ingestion. Cần chính sách dọn
upload bỏ dở; không mặc định trình duyệt sẽ luôn gọi complete.

Để thay file, gửi thêm `document_id` trong yêu cầu tạo upload. Backend tạo key
mới, giữ bản trước để tránh mất dữ liệu khi upload thất bại. Tài liệu có thể
đang phục vụ nội dung cũ trong khi bản mới chưa index; UI cần thể hiện điều đó.
Bucket phải cấu hình CORS cho origin admin để trình duyệt upload trực tiếp.

## 7. Ingestion chạy nền

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| POST | `/api/admin/ingestion/jobs` | Tạo job xử lý các tài liệu đã upload hợp lệ. |
| GET | `/api/admin/ingestion/jobs?cursor=...` | Danh sách job. |
| GET | `/api/admin/ingestion/jobs/{id}` | Tiến trình, số chunk và lỗi. |
| POST | `/api/admin/ingestion/jobs/{id}/retry` | Tạo lần chạy lại job thất bại, giữ lịch sử lần trước. |

### Tạo job

```json
{
  "document_ids": ["uuid-1", "uuid-2"]
}
```

Trả `202 Accepted` với ID và trạng thái job. UI polling endpoint chi tiết để xem
tiến trình, không giữ request HTTP chờ xử lý xong.

```text
queued → extracting → chunking → embedding → indexing → succeeded
                    Bất kỳ bước nào cũng có thể → failed
```

Yêu cầu xử lý:

- Chống tạo job trùng cho cùng bản tài liệu đang được xử lý.
- Job gắn với bản file/checksum cụ thể; không index nhầm file bị thay giữa chừng.
- Lưu trạng thái bền vững, có cơ chế xử lý job dang dở khi worker restart.
- Lỗi hiển thị an toàn, không trả credentials hay URL có chữ ký cho client.
- Chỉ nhận thành công khi dữ liệu sẵn sàng phục vụ; bulk lỗi có thể thành công
  một phần, không được giả định index là thao tác atomic.

**Khoảng trống cần triển khai:** importer hiện tại chỉ upsert và không tự xóa
chunk cũ. Khi thay tài liệu, phải có chiến lược loại bỏ chunk cũ và tránh phục
vụ dữ liệu nửa cũ/nửa mới. Có thể tiếp tục dùng rebuild index toàn bộ ở phía
backend như [hướng dẫn ingestion](ingestion.md); không cần có menu phiên bản.
Không nên làm nút thay file tự động index cho tới khi giải quyết việc đồng bộ này.

## 8. Dashboard, thành viên và audit

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| GET | `/api/admin/dashboard` | Tổng tài liệu, dung lượng, trạng thái và job gần đây. |
| GET | `/api/admin/members?cursor=...` | Liệt kê tài khoản quản trị. |
| POST | `/api/admin/members` | Tạo tài khoản. |
| PATCH | `/api/admin/members/{id}` | Cập nhật thông tin/quyền hoặc khóa tài khoản. |
| GET | `/api/admin/audit-logs?cursor=...` | Nhật ký; có thể bổ sung lọc theo người, hành động và thời gian. |

Audit ghi hành động thực tế, actor, đối tượng, thời gian và kết quả. Không chỉ
ghi sự kiện bấm nút trên frontend. Dashboard cần nói rõ dung lượng là của các
tài liệu được quản lý hay toàn prefix R2; không trộn hai số liệu.

## 9. Các trạng thái và lỗi API

Không có trạng thái chờ duyệt. Tối thiểu UI cần phân biệt: chưa index, đang xử
lý, đã index, thất bại; khi thay file phải thể hiện bản mới chưa được index.

Các mã lỗi đề xuất:

| HTTP | Ý nghĩa |
| --- | --- |
| 401 | Chưa đăng nhập/session hết hạn. |
| 403 | Không đủ quyền hoặc ngoài phạm vi được phép. |
| 404 | Không tìm thấy đối tượng được yêu cầu. |
| 409 | Xung đột trạng thái, tên trùng hoặc job đang chạy. |
| 413 | File vượt dung lượng cho phép ở bước kiểm tra. |
| 422 | Payload/metadata không hợp lệ. |
| 503 | Phụ thuộc R2, database hoặc dịch vụ xử lý không sẵn sàng. |

## 10. Thứ tự triển khai

1. Đăng nhập, session và phân quyền backend.
2. List folder/file R2 có phân trang, breadcrumb và tạo folder.
3. Upload/complete, chi tiết tài liệu và metadata.
4. Audit các thao tác quản trị đã có.
5. Ingestion job nền, theo dõi lỗi và đồng bộ OpenSearch khi thay tài liệu.
6. Quản lý thành viên và dashboard số liệu thật.

Đổi tên/di chuyển/xóa folder để giai đoạn sau: rename prefix là copy rồi xóa
nhiều object, không nguyên tử. Xóa tài liệu phải xử lý cả tham chiếu metadata
và chunk trong OpenSearch, không chỉ xóa object R2. Các thao tác phá hủy cần xác
nhận, kiểm tra quyền và phương án khôi phục.

Các endpoint auth, ingestion job, dashboard, members và audit trong phần thiết
kế tổng quan chưa được triển khai bởi thay đổi backend R2 này. Xem phần hướng
dẫn đầu tài liệu để biết API nào thực sự có thể gọi.
