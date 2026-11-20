# Hướng dẫn tích hợp Frontend và test tay

Thay đổi này cung cấp các API backend cho Knowledge Library. File có sẵn trên R2 sẽ xuất hiện khi lấy danh sách; không cần nhập lại dữ liệu, sao chép, đổi tên hay tải lên lại. Đăng nhập bằng API Admin hiện có và dùng access token dạng Bearer. Không gửi token Admin đến R2.

## Quy trình tải file lên

1. Admin mở Knowledge Library. Gọi `GET /api/admin/knowledge/objects` và không truyền prefix để bắt đầu tại thư mục gốc đã cấu hình trên server.
2. Hiển thị `folders` và `files`. Điều hướng bằng `prefix` được trả về, giữ nguyên từng `key` và dùng URLSearchParams để tạo query string. Lấy trang tiếp theo bằng `nextContinuationToken` đến khi giá trị này là null, kể cả khi trang hiện tại rỗng sau bước lọc. Khi đổi thư mục, bắt đầu lại phân trang.
3. Admin chọn thư mục đích và một File trên máy. Xác định MIME theo danh sách phần mở rộng được API cho phép; không phụ thuộc vào `file.type` vì trình duyệt có thể trả chuỗi rỗng.
4. Gọi POST `/api/admin/knowledge/upload-url` với `{folder, filename, contentType, size: file.size}`. Mã 409 nghĩa là tên file đã tồn tại hoặc đang được một phiên upload khác giữ chỗ; yêu cầu Admin chọn tên khác. Backend không tự đổi tên file.
5. Gửi PUT với nội dung File nguyên bản đến `uploadUrl`, kèm đầy đủ các header trong `requiredHeaders`. Không dùng multipart/FormData, không thêm Authorization và không tự đặt Content-Length bằng JavaScript trên trình duyệt. Trình duyệt tự tính header đã ký này từ đúng nội dung File.
6. Sau khi PUT thành công, gọi POST `/api/admin/knowledge/uploads/{uploadId}/complete`, kèm Bearer token Admin và không gửi body. Chỉ PUT thành công trên R2 chưa có nghĩa file đã được lưu hoàn chỉnh vào thư viện.
7. Backend kiểm tra file ở vùng tạm (staging) và ghi vào vị trí đích bằng thao tác nguyên tử. Hiển thị trạng thái đã lưu khi complete trả 200. Trạng thái này không có nghĩa file đã được lập chỉ mục, tạo embedding hoặc đưa vào chatbot.
8. Tải lại danh sách thư mục đang chọn. Giữ prefix hiện tại, xóa trạng thái phân trang cũ và hiển thị đúng vị trí đích do complete trả về.

Dùng `XMLHttpRequest.upload.onprogress` để hiển thị tiến độ PUT trực tiếp (`loaded/total`). Khi tiến độ đạt 100%, việc truyền dữ liệu đã xong; tiếp tục hiển thị trạng thái “Đang xác minh file…” trong lúc gọi complete. Fetch cũng tải được File nhưng không có sự kiện theo dõi tiến độ upload tương đương trên các trình duyệt.

Nếu mất phản hồi PUT, gửi lại đến staging key không cho ghi đè có thể nhận 412 vì lần PUT đầu đã thành công. Gọi complete để xác định kết quả; không bỏ If-None-Match hoặc ghi đè staging. Nếu complete gặp lỗi mạng/503, gọi lại bằng cùng upload ID. Phiên đã hoàn tất sẽ trả thông tin file thật; file đích đã bị xóa sẽ không được tạo lại. Phiên hết hạn mà chưa ghi file đích trả 410 và cần tạo phiên mới. URL có chữ ký hết hạn sau 5 phút, phiên upload hết hạn sau 15 phút. Chỉ giữ URL trong bộ nhớ và loại bỏ URL khỏi dữ liệu phân tích, log và báo cáo lỗi.

## Cấu hình CORS trên trình duyệt

Cần cấu hình hai chính sách: `CORS_ORIGINS` của backend cho các yêu cầu API có xác thực, và CORS của bucket cho PUT/GET trực tiếp đến R2. Bucket vẫn ở chế độ riêng tư. Người quản trị cần kiểm tra và cấu hình đúng origin triển khai trên Cloudflare; phần triển khai này chưa thay đổi chính sách production. Thay domain minh họa bên dưới bằng origin Admin thực tế, gồm giao thức và cổng nếu có. Chỉ thêm localhost vào chính sách dành cho môi trường phát triển đã được rà soát.

Mẫu chính sách CORS trong Cloudflare Dashboard:

```json
[
  {
    "AllowedOrigins": ["https://admin.example.com"],
    "AllowedMethods": ["PUT", "GET", "HEAD"],
    "AllowedHeaders": ["Content-Type", "Content-Length", "If-None-Match", "x-amz-meta-upload-id"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 300
  }
]
```

Không thêm origin/header dạng wildcard hoặc quyền DELETE cho luồng này. Yêu cầu xóa đi qua backend có xác thực. `OPTIONS` được xử lý như CORS preflight và không phải một mục trong AllowedMethods. Nếu cấu hình CORS bằng S3 API, bọc mảng quy tắc trong `{"CORSRules":[...]}`; rà soát trước khi thay chính sách hiện có. URL được tạo phải sử dụng endpoint S3 của R2, không thay bằng hostname CDN công khai hoặc domain tùy chỉnh.

Khi kiểm tra CORS bằng công cụ dòng lệnh, cần gửi header `Origin`. Kiểm tra preflight trên trình duyệt từ đúng origin Admin và xác nhận ba header upload bắt buộc được chấp nhận. URL có chữ ký hết hạn có thể hiện thành lỗi CORS/mạng trong JavaScript vì R2 không trả header CORS cho phản hồi hết hạn. Khi đó, tạo phiên mới hoặc gọi lại complete nếu file có thể đã được tải lên. Tham khảo [tài liệu CORS của Cloudflare](https://developers.cloudflare.com/r2/buckets/cors/) và [tài liệu URL có chữ ký](https://developers.cloudflare.com/r2/api/s3/presigned-urls/).

## Xem thông tin, xem trước, tải xuống và xóa file

Gọi GET `/object?key=...` để lấy dung lượng, MIME, thời gian, ETag và metadata được phép hiển thị. GET `/preview?key=...` trả JSON chứa văn bản UTF-8 nguyên bản; hiển thị bằng text node hoặc `<pre>`. Không để nội dung Markdown/HTML được thực thi. Nếu nhận 413, cung cấp lựa chọn tải xuống. Gọi POST `/download-url` với `{key}` rồi mở URL tải xuống ngắn hạn được trả về. Không cần URL riêng tư cố định.

Để tạo thư mục, gọi POST `/folders` với `{parentPrefix, folderName}` rồi tải lại danh sách. Khi xóa, hiển thị xác nhận có tên file/key chính xác, sau đó gửi một DELETE `/objects` với body `{key}`. Tải lại danh sách sau mã 204. Không gửi prefix thư mục, ký tự đại diện, mảng hoặc `recursive`; các cách này không thuộc luồng tích hợp. Phối hợp với các công cụ ghi dữ liệu bên ngoài vì thao tác xóa tác động đến object hiện tại tại key đã chọn, không bảo đảm so sánh ETag và xóa nguyên tử.

<a id="deployment-and-manual-test-steps"></a>

## Triển khai và test tay

1. Cấu hình các biến phía server trong [.env.example](.env.example). Tái sử dụng thông tin xác thực R2 và quy ước database hiện có. Đặt `JWT_SECRET_KEY` riêng tư, không dùng khóa dự phòng công khai trong repository. API đăng nhập và module này phải dùng cùng cấu hình ký token ngay từ lúc khởi động tiến trình.
2. Kiểm tra lịch sử Alembic trước khi áp dụng `20261120_knowledge_library` (migration cha: `20261120_classification`) theo quy trình triển khai của dự án. Migration chỉ tạo `knowledge_library_upload`, không ghi lại dữ liệu cũ hoặc object R2. Không dùng create_all hoặc stamp database có schema không tương thích. Các test PostgreSQL của task chỉ áp dụng migration trên tài nguyên test tạm thời.
3. Tạo hoặc dùng tài khoản Admin đang hoạt động theo luồng tài khoản hiện có, kiểm tra bản ghi `roles` là ADMIN rồi đăng nhập. Mở `/docs` của backend, bấm **Authorize** và nhập Bearer token. Kiểm tra đủ 8 thao tác của thư viện.
4. Kiểm tra chỉ đọc an toàn trên production: lấy danh sách gốc; mở một prefix thư mục được trả về; phân trang với limit nhỏ; xem thông tin một file có sẵn; xem trước một file văn bản nhỏ; tạo liên kết tải xuống ngắn hạn. Không giả định tên thư mục mẫu tồn tại. Kiểm tra không có token trả 401 và tài khoản thường trả 403.
5. **Chỉ kiểm tra ghi/xóa trong môi trường test riêng**, dùng bucket/tài khoản chứa dữ liệu giả lập và tên bucket bắt buộc `knowledge-heritage`. Đặt phạm vi thư viện riêng, ví dụ `qa-library/`, rồi tạo file test trong đó. Không chọn file production có sẵn để thử các thao tác này.
6. Tạo thư mục QA, xin upload URL cho một file UTF-8 `.md` nhỏ, PUT đúng nội dung rồi gọi complete. Kiểm tra danh sách, metadata và preview khớp nội dung đã gửi; gọi lại complete và xác nhận kết quả giống nhau. Kiểm tra file không tự được đưa vào chatbot/RAG.
7. Xin phiên upload khác với cùng tên file và kiểm tra mã 409. Thử `.html`, MIME sai, dung lượng bằng 0/quá giới hạn, đường dẫn đi lên thư mục cha và trường yêu cầu xóa đệ quy; phải nhận 422. Trên tài nguyên test riêng, kiểm tra file sai dung lượng/định danh không thể complete và phiên hết hạn trả 410.
8. Chỉ xóa file test bằng đúng key được trả về; kiểm tra mã 204 rồi 404 khi xem metadata. Xác nhận file test bên cạnh và object đánh dấu thư mục vẫn còn. API không cung cấp thao tác xóa thư mục đệ quy.

## Lệnh kiểm thử tự động

Chạy từ thư mục gốc repository, dùng virtualenv backend và các thư viện test hiện có:

```text
python -X utf8 -m unittest apps.backend.tests.test_knowledge_library_storage apps.backend.tests.test_knowledge_library_api apps.backend.tests.test_knowledge_library_contract -v
python -X utf8 -m unittest apps.backend.tests.test_knowledge_library_postgres -v
python -X utf8 scripts/verify-knowledge-r2.py
```

Để chạy test PostgreSQL, đặt rõ `KNOWLEDGE_TEST_DATABASE_URL` trỏ đến database `postgresql+psycopg://.../test_*` trên localhost dành riêng cho test tự động. Nếu thiếu biến này, các test PostgreSQL sẽ được bỏ qua. Test áp dụng migration trong schema có tên ngẫu nhiên do test tự tạo và chỉ dọn các schema đó. Mọi thao tác ghi/xóa R2 trong test đều chạy trên client giả lập trong bộ nhớ. Script kiểm tra kết nối R2 thật chỉ lấy danh sách và HEAD, không in tên file, thông tin xác thực hoặc URL có chữ ký.

Object staging bị bỏ dở và bản ghi phiên cũ được giữ lại để khôi phục. Người vận hành nên rà soát chính sách vòng đời chỉ áp dụng cho prefix dành riêng `__knowledge_library_uploads__/` dưới thư mục gốc đã cấu hình, với thời gian lưu dài hơn thời hạn phiên một khoảng phù hợp; task chưa cài chính sách hay tác vụ dọn dẹp. Cân nhắc nhu cầu khôi phục, kiểm toán và lưu giữ trước khi xóa bản ghi database. Cấu hình giới hạn tần suất upload/ghi theo từng Admin tại gateway triển khai vì repository chưa có bộ giới hạn phân tán.
