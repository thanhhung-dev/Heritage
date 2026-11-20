# Rà soát kiến trúc Knowledge Library

Backend sử dụng Python 3.11, FastAPI, Pydantic 2, SQLAlchemy 2 bất đồng bộ và PostgreSQL. Alembic quản lý các thay đổi schema đã được rà soát. Router API được gắn trong `apps/backend/app.py`; `/docs` và `/openapi.json` mô tả giao diện HTTP mà API cung cấp.

`core/r2.py:R2Storage` đã đảm nhiệm khởi tạo boto3, ký SigV4, giới hạn thời gian kết nối và trả lỗi storage an toàn. Thư viện mở rộng adapter này, không triển khai thêm một client SDK khác. Giữ nguyên cấu hình media và dịch vụ knowledge/RAG cũ. Dịch vụ cũ chỉ cho duyệt `curated/`, đặt tên đích bằng UUID và kiểm tra OpenSearch; các quy tắc nghiệp vụ đó không phù hợp với thư viện này.

Router mới `/api/admin/knowledge` dùng các hàm ký JWT hiện có, đồng thời kiểm tra tài khoản/quyền hiện tại trong database. Thiếu thông tin xác thực trả 401; tài khoản không phải Admin trả 403. Nếu thiếu khóa ký hoặc dùng khóa dự phòng công khai thì từ chối phục vụ. Mọi lệnh storage đều chọn bucket `knowledge-heritage` do server quyết định. Không API nào nhận tên bucket hoặc URL tùy ý từ client.

## Kế hoạch triển khai

1. Tập trung kiểm tra key/prefix chính xác, Unicode, loại và dung lượng file. Giữ nguyên key có sẵn; không tự chuẩn hóa hoặc đổi tên object đã lưu.
2. Chuyển danh sách R2 theo dấu phân cách và metadata từ HEAD sang DTO ổn định, bao gồm token phân trang không cần client diễn giải.
3. Thêm một bảng phiên upload lưu bền vững bằng migration Alembic chỉ bổ sung schema. Dùng ràng buộc duy nhất để giữ chỗ key đích giữa nhiều tiến trình.
4. Ký PUT chỉ cho tạo mới đến staging key duy nhất. Ràng buộc loại nội dung, dung lượng và định danh upload. Kiểm tra toàn bộ object trong giới hạn cho phép trước khi ghi nguyên tử đến vị trí đích bằng `PutObject(IfNoneMatch='*')`. HEAD sơ bộ chỉ giúp phát hiện sớm xung đột.
5. Dùng khóa bản ghi database để xử lý complete lần lượt. Metadata trên file đích hỗ trợ khôi phục khi storage đã ghi thành công nhưng database chưa commit được. Gọi complete nhiều lần phải kiểm tra object đích thật, không tin dữ liệu client tự khai báo.
6. Bổ sung preview UTF-8 có giới hạn, URL tải xuống ngắn hạn, tạo marker thư mục có điều kiện và xóa chính xác một file. Không xử lý đệ quy hoặc nhập dữ liệu vào RAG.
7. Kiểm thử với storage giả lập và database tạm dành riêng; kiểm tra R2 thật chỉ bằng lấy danh sách/HEAD. Viết tài liệu API, CORS, triển khai và tích hợp/test tay.

## Cấu hình và giới hạn phạm vi

Tái sử dụng `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `DATABASE_URL` và `JWT_SECRET_KEY`. Đặt `R2_KNOWLEDGE_BUCKET=knowledge-heritage` (mặc định); giá trị khác sẽ bị từ chối. Có thể dùng `R2_KNOWLEDGE_LIBRARY_PREFIX` để giới hạn phạm vi thư viện, mặc định là gốc bucket. Các biến cũ `R2_KNOWLEDGE_PREFIX` và `R2_BUCKET` giữ nguyên ý nghĩa ở những module khác.

Các giới hạn mới: `KNOWLEDGE_MAX_UPLOAD_BYTES` (mặc định 10 MiB, tối đa 32 MiB), `KNOWLEDGE_PREVIEW_MAX_BYTES` (mặc định 128 KiB, tối đa 1 MiB). URL upload/download có hiệu lực 300 giây; phiên upload có hiệu lực 15 phút. Hỗ trợ upload `.md`, `.txt`, `.json` mã hóa UTF-8; không hỗ trợ HTML, file thực thi, PDF/OCR hoặc file nhị phân tùy ý.

Backend đã kiểm tra chưa có middleware giới hạn tần suất/cache. Môi trường triển khai cần giới hạn yêu cầu có xác thực theo từng Admin tại gateway; luồng này cũng được giới hạn bằng dung lượng upload, thời hạn URL và cơ chế giữ chỗ key lưu bền vững. Phần triển khai không thay đổi chính sách CORS bucket production.

## Tài liệu tham khảo về tính đúng đắn của storage

Cloudflare mô tả điều kiện `PutObject` chỉ cho tạo mới theo cách nguyên tử trong [các thao tác có điều kiện](https://developers.cloudflare.com/r2/api/s3/conditional-operations/) và [bảo đảm tính nhất quán](https://developers.cloudflare.com/r2/reference/consistency/). `CopySourceIfMatch` chỉ áp dụng cho nguồn, không ngăn ghi đè đích; vì vậy phần triển khai dùng luồng nội dung đã kiểm tra có giới hạn và PUT đích có điều kiện. Staging là vùng riêng tư, không hiển thị trong thư viện. Dọn staging hết hạn là quyết định vòng đời dữ liệu của người vận hành, phải giới hạn đúng prefix; không tự chạy dọn dữ liệu production.
