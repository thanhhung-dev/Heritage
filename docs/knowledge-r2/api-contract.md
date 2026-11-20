# Tài liệu API quản trị Knowledge Library

Đường dẫn gốc: `/api/admin/knowledge`. Cả 8 thao tác đều yêu cầu `Authorization: Bearer <access-token>` lấy từ API đăng nhập hiện có và tài khoản ADMIN đang hoạt động, không bị khóa. Token đặt lại mật khẩu không được dùng cho các thao tác này. Phiên upload thuộc về Admin đã tạo phiên. API không nhận tên bucket từ client; body có trường không được khai báo sẽ bị từ chối với mã 422.

Phản hồi thành công có `Cache-Control: no-store` và `X-Content-Type-Options: nosniff`. Nội dung văn bản được trả trong JSON dưới dạng dữ liệu, không phải HTML để thực thi. `/docs` và `/openapi.json` mô tả schema, xác thực Bearer và lỗi của từng thao tác.

## Duyệt thư mục

`GET /objects?prefix=documents/&limit=100&continuationToken=...`

- `prefix`: prefix chính xác, kết thúc bằng dấu `/`; bỏ qua để dùng thư mục gốc đã cấu hình, mặc định là gốc bucket. Truyền rõ `prefix=` nghĩa là gốc bucket và bị từ chối nếu server đã giới hạn phạm vi hẹp hơn.
- `limit`: từ 1 đến 1000, mặc định 100; tính theo các mục R2 trước khi lọc, bao gồm prefix và object đánh dấu thư mục.
- `continuationToken`: token phân trang tùy chọn lấy từ phản hồi trước; mã hóa URL và giữ nguyên prefix. Không phân tích hoặc tự tăng giá trị token.

```json
{
  "bucket": "knowledge-heritage",
  "prefix": "documents/",
  "folders": [{"name": "history", "prefix": "documents/history/"}],
  "files": [{"name": "overview.md", "key": "documents/overview.md", "size": 123, "lastModified": "2026-11-20T08:00:00Z"}],
  "nextContinuationToken": null
}
```

Dữ liệu trên chỉ là ví dụ giả lập. Mỗi trang tương ứng một lần gọi `ListObjectsV2(Prefix, Delimiter='/')`. Common prefix được hiển thị như thư mục logic; file chỉ xuất hiện ở cấp thư mục hiện tại; object đánh dấu thư mục không nằm trong danh sách file. Prefix rỗng hoặc không tồn tại trả các mảng rỗng. Vùng staging riêng tư được ẩn. Một trang sau khi lọc có thể rỗng nhưng vẫn có token tiếp theo; cần tiếp tục đến khi token là null. Duyệt thư mục không đăng ký/nhập object vào database và không tải nội dung file.

## Xin URL tải file lên

`POST /upload-url` → **201**

```json
{"folder":"documents/history/","filename":"notes.md","contentType":"text/markdown","size":123}
```

```json
{
  "uploadId": "00000000-0000-0000-0000-000000000001",
  "objectKey": "documents/history/notes.md",
  "uploadUrl": "<ephemeral-presigned-staging-url>",
  "method": "PUT",
  "expiresIn": 300,
  "sessionExpiresAt": "2026-11-20T08:15:00Z",
  "requiredHeaders": {"Content-Type":"text/markdown","If-None-Match":"*","x-amz-meta-upload-id":"00000000-0000-0000-0000-000000000001"}
}
```

Gửi đúng số byte đã khai báo đến `uploadUrl`, không bọc nội dung bằng FormData. URL có hiệu lực 300 giây; phiên xác nhận upload được lưu bền vững và tồn tại 900 giây. `Content-Length` được ký và phải khớp `size`; trình duyệt tự đặt từ File/Blob. Client phải gửi nguyên các header bắt buộc được trả về.

Các loại file được hỗ trợ: `.md`/`text/markdown`, `.txt`/`text/plain`, `.json`/`application/json`. Dung lượng phải lớn hơn 0 và không vượt `KNOWLEDGE_MAX_UPLOAD_BYTES` (mặc định 10 MiB, giới hạn cấu hình tối đa 32 MiB). Toàn bộ nội dung UTF-8 và cấu trúc JSON được kiểm tra khi complete. Upload không kích hoạt lập chỉ mục, OCR hoặc phân loại.

Tên mới phải ở dạng Unicode NFC, dài tối đa 255 byte UTF-8, không chứa dấu phân cách đường dẫn, ký tự điều khiển/định dạng, ký tự đặc biệt của URL/đường dẫn hoặc khoảng trắng đầu/cuối. Key/prefix dài tối đa 1024 byte UTF-8; từ chối đường dẫn tuyệt đối, đường dẫn đi lên thư mục cha, dấu phân cách lặp, dấu gạch chéo ngược, đường dẫn mã hóa phần trăm và tiền tố URI/ổ đĩa. Key Unicode hiện có được giữ nguyên, không tự chuẩn hóa. Upload ngoài phạm vi cấu hình hoặc vào prefix staging dành riêng sẽ bị từ chối.

Chính sách mặc định khi trùng tên là **từ chối**, không đổi tên hoặc ghi đè: file đích đã tồn tại hoặc có phiên đang giữ chỗ trả 409. PUT có điều kiện tại vị trí đích còn chặn được tác vụ ghi đồng thời xuất hiện sau HEAD sơ bộ. Phiên giữ chỗ tồn tại qua lần khởi động lại tiến trình và giữa nhiều instance backend. Lỗi ký URL/giao dịch có thể cần thử lại hoặc chờ phiên hết hạn; không coi timeout là bằng chứng chắc chắn thao tác đã thất bại.

## Xác nhận hoàn tất upload

`POST /uploads/{uploadId}/complete` → **200**, không gửi body.

```json
{
  "uploadId":"00000000-0000-0000-0000-000000000001",
  "status":"stored",
  "object":{"bucket":"knowledge-heritage","key":"documents/history/notes.md","name":"notes.md","size":123,"contentType":"text/markdown","lastModified":"2026-11-20T08:00:05Z","etag":"\"example-etag\"","metadata":{}}
}
```

Backend khóa bản ghi phiên trong database, HEAD object staging, kiểm tra định danh/MIME/dung lượng đã ký, đọc toàn bộ object theo điều kiện ETag vào vùng đệm đĩa có giới hạn, kiểm tra nội dung thực tế rồi ghi đích với `If-None-Match: *`. Sau đó backend kiểm tra HEAD của file đích và lưu trạng thái hoàn tất. Key, ETag hoặc dung lượng do client tự gửi lại không quyết định object được xác nhận.

Gọi complete nhiều lần sẽ trả cùng object đã lưu sau một lần HEAD thực tế. Nếu file đích đã bị xóa, trả 404 và không tạo lại. Nếu file đã thay đổi, trả 409. Nếu R2 ghi đích thành công nhưng database chưa commit được, định danh upload trên file đích cho phép khôi phục khi gọi lại, kể cả sau khi phiên hết hạn. Phiên hết hạn nhưng chưa ghi đích trả **410**; thiếu staging/phiên trả 404; không phải chủ phiên trả 403; sai dung lượng/MIME/định danh/nội dung trả 422. Tác vụ ghi khác chiếm vị trí đích trả 409. Nội dung không đạt kiểm tra sẽ không được ghi vào vị trí đích.

## Xem thông tin file

`GET /object?key=documents/history/notes.md` → **200**, trả trực tiếp cấu trúc `object` ở trên, không có lớp bọc bên ngoài. Dữ liệu được đọc bằng `HeadObject` thực tế. Chỉ metadata người dùng có tên `language` và `source-type` được hiển thị. Không trả metadata tùy ý, thông tin nội bộ của phiên upload, header phản hồi storage hoặc chi tiết nội bộ nhà cung cấp. Key đánh dấu thư mục không được chấp nhận như file.

## Tạo URL tải xuống ngắn hạn

`POST /download-url` với `{"key":"documents/history/notes.md"}` → **200**

```json
{"key":"documents/history/notes.md","downloadUrl":"<ephemeral-presigned-get-url>","expiresIn":300}
```

HEAD phải thành công trước khi ký URL. GET dùng chế độ tải file đính kèm, tên file được mã hóa an toàn và `application/octet-stream`. Ai có URL tạm thời này đều có thể sử dụng trong thời hạn cho phép; không ghi log hoặc lưu lâu dài. Object vẫn riêng tư, không tạo URL công khai. Liên kết có thể trả nội dung mới nếu một công cụ độc lập thay object tại cùng key trước khi liên kết được sử dụng.

## Xem trước văn bản an toàn

`GET /preview?key=documents/history/notes.md` → **200**

```json
{"key":"documents/history/notes.md","content":"# Example\nPlain source text","contentType":"text/plain; charset=utf-8","size":123,"etag":"\"example-etag\""}
```

Phản hồi HTTP là `application/json`; trường `contentType` mô tả văn bản bên trong. Hiển thị `content` qua text node hoặc khối mã đã escape. Không đưa vào `innerHTML` hoặc trình render Markdown chưa làm sạch nội dung. Backend đọc tối đa số byte preview đã cấu hình cộng 1 bằng Range và If-Match, rồi đóng luồng dữ liệu. Giới hạn mặc định 128 KiB, tối đa 1 MiB. Lỗi: **413** nếu quá lớn, **415** nếu không hỗ trợ phần mở rộng, 422 nếu là nhị phân/UTF-8 hoặc JSON không hợp lệ, 409 nếu file thay đổi hoặc nội dung chưa đầy đủ, 404 nếu không tồn tại. Hỗ trợ file `.txt`/`.md` rỗng đã có sẵn.

## Tạo thư mục logic

`POST /folders` với `{"parentPrefix":"documents/","folderName":"history"}` → **201**

```json
{"name":"history","prefix":"documents/history/"}
```

Tạo object đánh dấu thư mục 0 byte, có key kết thúc bằng `/`, bằng PUT có điều kiện chỉ cho tạo mới. Nếu marker/prefix hoặc file cùng tên đã tồn tại, trả 409. Thư mục hiện có vẫn được nhận diện dù không có marker; thao tác duyệt không tự tạo marker. Prefix cha là đường dẫn logic, không bắt buộc có object đánh dấu thư mục. Không có API đổi tên/di chuyển/xóa thư mục.

## Xóa chính xác một file

`DELETE /objects` với `{"key":"documents/history/notes.md"}` → **204**, không có body phản hồi. HEAD phải tìm thấy đúng object trước khi xóa. Key rỗng/gốc/kết thúc bằng `/`, cờ xóa đệ quy, mảng và trường bucket bổ sung đều không hợp lệ. Thao tác thay đổi storage duy nhất là `DeleteObject(Key=the_exact_key)`; file bên cạnh và object đánh dấu thư mục không bị tác động. File không tồn tại trả 404. Không có thao tác xóa hàng loạt hoặc đệ quy.

Lệnh xóa nhắm đến object hiện tại tại key đó. Bảng điều kiện ghi S3 trong tài liệu R2 không cam kết DeleteObject có điều kiện; API này không cam kết so sánh ETag rồi xóa nguyên tử. Nếu một công cụ độc lập thay object tại cùng key giữa HEAD và lúc xóa, nội dung mới có thể bị xóa. Cần phối hợp với các công cụ ghi bên ngoài khi xác nhận xóa. Không chạy thử xóa dữ liệu production trong quá trình triển khai task.

## Lỗi chung và ví dụ sử dụng

Body lỗi theo quy ước FastAPI `{"detail":"thông báo an toàn"}`; lỗi kiểm tra schema có phần chi tiết dạng mảng. Thiếu/sai/hết hạn access token → 401 (`WWW-Authenticate: Bearer`); không có quyền Admin → 403; dữ liệu không hợp lệ → 422; không tìm thấy object/phiên → 404; xung đột → 409; storage/cấu hình/database không khả dụng → 503. Không trả thông báo nội bộ bất ngờ từ nhà cung cấp hoặc thông tin xác thực. Nếu nhà cung cấp từ chối token phân trang, hiện API trả 503 với thông báo an toàn; lấy lại danh sách từ đầu mà không truyền token đó.

Ví dụ yêu cầu chỉ đọc; các biến shell là giá trị minh họa cần tự cấu hình:

```bash
curl --get "$API_BASE/api/admin/knowledge/objects" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  --data-urlencode 'prefix=documents/' --data-urlencode 'limit=100'
```

Người vận hành production cần áp dụng migration, cấu hình khóa ký JWT riêng tư, tài khoản Admin hợp lệ, quyền R2 giới hạn đúng bucket riêng tư và CORS với origin chính xác. Giới hạn tần suất yêu cầu được cấu hình tại gateway triển khai; repository chưa có bộ giới hạn phân tán. Xem [hướng dẫn tích hợp Frontend và test tay](frontend-integration.md) để biết cách xử lý trên trình duyệt và các bước kiểm tra thủ công.
