# Báo cáo hoàn thành backend Knowledge Library

Hoàn thành ngày 20/11/2026 trên nhánh `feat/knowledge-r2-library`, phát triển từ `cc03edc`. Đã triển khai backend, kiểm thử và tài liệu tích hợp. Không ghi, đổi tên, di chuyển hoặc xóa object R2 production có sẵn. Module không nhập file cũ vào SQL; upload không kích hoạt RAG, embedding, phân loại, chia đoạn hoặc lập chỉ mục.

## Kết quả từng công việc

Thời gian dưới đây là ước lượng lập kế hoạch theo yêu cầu, không phải số giờ làm việc thực tế.

| Công việc | Ước lượng | Trạng thái | File thay đổi | Kết quả kiểm thử |
|---|---:|---|---|---|
| BE-R2-01 Tích hợp R2 | 3h | Hoàn thành (DONE) | `core/r2_library.py`, `docs/knowledge-r2/.env.example`, script kiểm tra kết nối | ĐẠT: cô lập bucket bằng dữ liệu giả lập; lấy danh sách và HEAD trên bucket thật |
| BE-R2-02 Lấy danh sách | 6h | Hoàn thành (DONE) | Adapter R2, `schemas/knowledge_library.py`, `api/knowledge_library.py` | ĐẠT: gốc/thư mục con/rỗng/phân trang/marker; lấy danh sách thư mục con thật |
| BE-R2-03 URL upload có chữ ký | 6h | Hoàn thành (DONE) | `services/knowledge_policy.py`, `services/knowledge_library.py`, ORM và migration phiên upload | ĐẠT: validation, header/dung lượng/thời hạn được ký, giữ chỗ bền vững và xung đột đồng thời |
| BE-R2-04 Xác nhận hoàn tất | 4h | Hoàn thành (DONE) | Service thư viện và adapter | ĐẠT: kiểm tra toàn bộ UTF-8/JSON; phiên thiếu/sai/hết hạn; ghi đích nguyên tử; complete đồng thời và khôi phục |
| BE-R2-05 Thao tác file | 5h | Hoàn thành (DONE) | Adapter, router và DTO | ĐẠT: metadata thực tế, preview có giới hạn, ký URL tải xuống dạng đính kèm và xử lý nội dung an toàn |
| BE-R2-06 Thư mục/xóa | 6h | Hoàn thành (DONE) | Adapter và router | ĐẠT: tạo marker có điều kiện, xóa đúng file và giữ file bên cạnh; chỉ ghi trên storage giả lập |
| BE-R2-07 Bảo mật | 5h | Hoàn thành (DONE) | `api/knowledge_dependencies.py`, chính sách và DTO | ĐẠT: xác thực cả 8 thao tác; quyền/trạng thái hoạt động/khóa hiện tại; chủ phiên; thời hạn hợp lệ; giới hạn đường dẫn/loại/dung lượng; lỗi an toàn |
| BE-R2-08 Test/tài liệu | 8h | Hoàn thành (DONE) | 5 file test/hỗ trợ; tài liệu API/Frontend/kiến trúc/tiến độ/báo cáo | ĐẠT: 35 test tính năng; các lỗi hồi quy cũ được nêu bên dưới |

Trừ các đường dẫn đã ghi rõ, đường dẫn trong bảng tính từ `apps/backend/`. Phần tích hợp bổ sung gồm gắn router trong `app.py`, import ORM model và loại bảng do migration quản lý khỏi luồng create_all cũ. Không sửa mã frontend, phần khởi tạo SDK R2 hiện có, cấu hình media, phần triển khai xác thực hoặc mã RAG.

## API và kiến trúc đã triển khai

Có 8 thao tác dưới đường dẫn `/api/admin/knowledge`:

- GET `/objects` — lấy một trang danh sách R2 theo dấu phân cách thư mục.
- POST `/upload-url` — tạo phiên bền vững và URL PUT staging chỉ cho tạo mới, có hiệu lực 300 giây.
- POST `/uploads/{uploadId}/complete` — kiểm tra file thật và ghi vào đích với điều kiện chỉ tạo mới.
- GET `/object` — lấy metadata hiện tại bằng HEAD.
- POST `/download-url` — URL GET tải file đính kèm, có hiệu lực 300 giây.
- GET `/preview` — trả văn bản nguyên bản có giới hạn trong JSON, không render HTML.
- POST `/folders` — tạo object đánh dấu thư mục logic 0 byte, kết thúc bằng `/`.
- DELETE `/objects` — HEAD rồi DeleteObject đúng một key, không xóa hàng loạt hoặc đệ quy.

`KnowledgeR2` kế thừa `R2Storage` và dùng lại cấu hình client, timeout và cách xử lý lỗi storage. Bucket do server quyết định luôn là `knowledge-heritage`; nếu cấu hình bucket sai thì từ chối phục vụ. Hành vi `R2_BUCKET` hiện có với `heritage` và `heritage-scene` không đổi. Phạm vi mặc định là gốc bucket thật; không viết cố định tên object hoặc cây thư mục. Marker thư mục và staging riêng tư được lọc khỏi danh sách file; vẫn trả token phân trang kể cả khi trang rỗng sau bước lọc.

Phiên upload được lưu trong `knowledge_library_upload`. Trường giữ chỗ vị trí đích có ràng buộc duy nhất và cho phép null, ngăn nhiều phiên đang hoạt động cùng giữ một tên. Khi complete, backend khóa bản ghi trên PostgreSQL; kiểm tra dung lượng, MIME, metadata phiên và toàn bộ nội dung staging; dùng vùng đệm tối đa theo giới hạn upload, chuyển sang đĩa sau ngưỡng 1 MiB trong bộ nhớ; rồi ghi key đích bằng `IfNoneMatch='*'` nguyên tử. Việc chống ghi đè không chỉ dựa vào HEAD hoặc điều kiện sao chép phía nguồn. Định danh upload và SHA-256 do server tạo hỗ trợ gọi lại khi database gặp lỗi. File đã hoàn tất nhưng bị xóa sẽ không tự được tạo lại.

URL upload/download hết hạn sau 300 giây; phiên upload hết hạn sau 900 giây. Chỉ nhận Markdown, text và JSON mã hóa UTF-8. Giới hạn upload mặc định 10 MiB, tối đa theo cấu hình 32 MiB; giới hạn preview mặc định 128 KiB, tối đa 1 MiB. Kiểm tra JSON có thể dùng bộ nhớ cho nội dung trong giới hạn upload cộng với cấu trúc đã phân tích; văn bản thông thường được kiểm tra theo từng phần. Preview có giới hạn riêng. Key và đường dẫn staging được sinh tuân thủ giới hạn 1024 byte của R2. Key khi đọc giữ nguyên Unicode; tên mới phải ở dạng NFC.

Phân quyền dùng cấu hình ký JWT hiện có, từ chối khóa dự phòng công khai, yêu cầu thời hạn hữu hạn hợp lệ và đúng mục đích access token, rồi kiểm tra tài khoản cùng quyền ADMIN hiện tại trong database. Không đủ quyền/không phải chủ phiên trả 403; thiếu/sai thông tin xác thực hoặc tài khoản ngừng hoạt động/bị khóa trả 401. Chỉ trả metadata tùy chỉnh nằm trong danh sách cho phép. Bộ xử lý lỗi của thư viện không ghi body nhà cung cấp, thông tin xác thực, URL có chữ ký hoặc key vào log.

## Bằng chứng kiểm thử

| Hạng mục | Kết quả | Bằng chứng / giới hạn |
|---|---|---|
| Test đơn vị/API/SDK/migration | **ĐẠT (PASS)** | 30 test trong các module storage, API và contract; kiểm tra HTTP qua ASGI và router thật; kiểm tra chữ ký boto3 và giao thức bằng Stubber, không cần mạng |
| Tích hợp PostgreSQL | **ĐẠT (PASS)** | 5 test trên PostgreSQL thật ở máy local; áp dụng migration trong schema ngẫu nhiên thuộc database tạm `test_knowledge_*`; dùng kết nối riêng để tạo cạnh tranh giữ chỗ/complete; đã dọn schema và database sau test |
| Lần chạy tổng hợp cuối của tính năng | **ĐẠT (PASS)** | **35 test, 15.297 giây, 0 thất bại/lỗi/bỏ qua** trên phần triển khai cuối |
| Kiểm tra chỉ đọc R2 thật | **ĐẠT (PASS)** | Trang gốc có 3 thư mục; chỉ đi theo thư mục đầu tiên được trả về ở mỗi cấp đến độ sâu 6; HEAD thật tìm được object 1424 byte và ETag. Không quét toàn bucket hoặc tính lại tổng số object/dung lượng lịch sử |
| Hồi quy có chọn lọc của mã cũ | **MỘT PHẦN: 65 ĐẠT, 3 lỗi có sẵn** | 68 test thuộc quản trị knowledge cũ, ingestion, khởi động, API di sản, chính sách bootstrap DB, health và migration catalog; chi tiết bên dưới |
| Đồ thị migration Alembic | **ĐẠT (PASS)** | `python -m alembic -c apps/backend/alembic.ini heads` trả một head duy nhất: `20261120_knowledge_library` |
| Biên dịch kiểm tra Python | **ĐẠT (PASS)** | Cả 17 file Python thay đổi đều biên dịch được; đã kiểm tra import app và OpenAPI thật |
| Tính nhất quán thư viện phụ thuộc | **ĐẠT (PASS)** | `python -m pip check` không phát hiện phụ thuộc hỏng; không cần cài hoặc nâng cấp thư viện |
| Kiểm tra khoảng trắng trong diff | **ĐẠT (PASS)** | `git diff --check cc03edc`; đã rà soát phạm vi backend; không commit file môi trường riêng tư hoặc thông tin xác thực |
| Lint/kiểm tra kiểu tĩnh riêng | **CHƯA CHẠY (NOT RUN)** | Chưa tìm thấy lệnh lint/type dành cho backend; ruff/mypy chưa được cài. Kiểm tra cú pháp/schema/thực thi không thay thế phân tích kiểu tĩnh |
| Build gói backend riêng | **CHƯA CHẠY (NOT RUN)** | Không có mục tiêu build backend riêng; đã kiểm tra import/biên dịch |
| Lint/type/build frontend | **CHƯA CHẠY (NOT RUN)** | Task chỉ thuộc backend; không sửa frontend |
| Toàn bộ test repository / hạ tầng RAG thật | **CHƯA CHẠY (NOT RUN)** | Chỉ chạy hồi quy có chọn lọc; không khởi động các dịch vụ truy xuất/suy luận hiện có |
| Upload/xóa R2 thật / CORS trình duyệt | **CHƯA CHẠY (NOT RUN)** | Không được thay đổi dữ liệu production để test; thao tác ghi SDK/HTTP dùng storage giả lập. Đã viết hướng dẫn CORS đúng origin nhưng chưa thay chính sách |
| Migration database ứng dụng chính | **CHƯA CHẠY (NOT RUN)** | Không thay đổi dữ liệu/schema ứng dụng hiện có; chỉ kiểm thử migration trên PostgreSQL tạm |

Cảnh báo lỗi storage được chủ động tạo trong test xử lý lỗi an toàn là kết quả dự kiến, không phải một test thất bại. Lần chạy hồi quy đầu với bảng mã Windows mặc định còn bộc lộ hành vi phụ thuộc encoding của mã cũ; lần chạy dùng để báo cáo đã sử dụng `python -X utf8` như tài liệu hướng dẫn.

Đã tái hiện các lỗi cũ bằng **entrypoint app trước task tại `cc03edc`** và các module cũ không thay đổi:

1. `AdminKnowledgeTests.test_actual_app_registers_admin_router`: router cũ `/api/admin/storage/entries` vốn chưa được gắn vào ứng dụng. Task này gắn router mới `/api/admin/knowledge`, không mở thêm giao diện quản trị local/RAG cũ.
2. `AdminKnowledgeTests.test_existing_file_registration_and_real_index_guard`: bước dọn file SQLite tạm có sẵn phát sinh Windows `NotADirectoryError` cho `test.db`.
3. `R2IngestionTests.test_transcript_config_metadata_is_preserved_and_header_alone_is_rejected`: phép kiểm tra metadata transcript trong ingestion cũ không đạt.

Kiểm tra trên phiên bản trước task tái hiện đúng 2 test thất bại và 1 lỗi thực thi này. Không sửa mã test, pipeline hoặc dịch vụ storage cũ để làm kết quả tính năng mới có vẻ đạt toàn bộ. Log chi tiết trên máy nằm trong `.catalog-test-runtime/knowledge-final-tests.log`, `knowledge-regression-utf8.log` và `knowledge-baseline-utf8.log` của workspace.

## Cấu hình và triển khai còn cần thực hiện

Tái sử dụng các biến phía server `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `DATABASE_URL`, `JWT_SECRET_KEY`. Các cấu hình được bổ sung vào tài liệu gồm `R2_KNOWLEDGE_BUCKET=knowledge-heritage`, `R2_KNOWLEDGE_LIBRARY_PREFIX` tùy chọn, `KNOWLEDGE_MAX_UPLOAD_BYTES` và `KNOWLEDGE_PREVIEW_MAX_BYTES`. Đã có thông tin xác thực để kiểm tra chỉ đọc R2. File `.env` local được kiểm tra chưa có JWT_SECRET_KEY riêng tư; vì vậy thư viện chủ động từ chối truy cập có xác thực bằng khóa dự phòng cũ cho đến khi cấu hình khởi động đúng.

Triển khai migration `20261120_knowledge_library`, có migration cha `20261120_classification`, theo quy trình migration đã rà soát. Migration chỉ thêm bảng phiên, chỉ mục và ràng buộc. Không stamp database thiếu schema cha và không dùng create_all cũ để thay thế. Downgrade được chặn để tránh mất âm thầm bản ghi khôi phục upload; cần xuất/lưu và kết thúc các phiên trước khi xem xét gỡ bảng. Trong task này chưa chạy migration trên database ứng dụng.

Kiểm tra thông tin xác thực được giới hạn theo bucket, cấu hình đúng origin Admin tại cả CORS_ORIGINS của backend và CORS R2, rồi sử dụng tài khoản Admin thật đang hoạt động. Giới hạn tần suất tại gateway là phần cấu hình triển khai vì repository chưa có bộ giới hạn phân tán. Rà soát riêng chính sách vòng đời staging và thời gian lưu database; object staging bỏ dở cùng bản ghi khôi phục hiện được giữ lại, chưa cài tác vụ/chính sách dọn dẹp. Bên tích hợp không được ghi log hoặc lưu lâu dài URL có chữ ký.

Xóa tác động đến key hiện tại sau HEAD. Tài liệu R2 không cam kết DeleteObject có điều kiện, nên phần triển khai không bảo đảm so sánh rồi xóa trước các tác vụ thay file độc lập bên ngoài. Phối hợp các công cụ ghi ngoài khi người dùng xác nhận xóa. Không chạy thử xóa production.

Xem [tài liệu API](api-contract.md) để biết request/response và mã lỗi. Xem [hướng dẫn tích hợp Frontend và test tay](frontend-integration.md) để biết quy trình upload, tiến độ, CORS và kiểm tra trong môi trường riêng. Chưa deploy, push, tạo PR, sửa CORS production hoặc thay đổi object production.
