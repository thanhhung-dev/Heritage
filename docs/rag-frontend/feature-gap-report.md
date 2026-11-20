# Chức năng nâng cao chưa có API phù hợp

Đã rà soát router gắn trong app, model, service và các API quản trị cũ. R2 storage có đủ 8 thao tác. `api/admin_knowledge.py` cũ có model metadata và chunks nhưng chỉ local/loopback, không xác thực, chưa được gắn vào app và dùng quy tắc RAG/key khác. Không dùng nó làm API production. Catalog di sản là miền dữ liệu khác, không phải review tài liệu.

| Thiếu | Contract tối thiểu cần backend cung cấp | Hành vi UI trong task |
|---|---|---|
| Metadata biên tập | Định danh object/revision ổn định; GET/PATCH tiêu đề, vùng, loại, URL nguồn; phiên bản kỳ vọng; quyền sở hữu; trạng thái draft thật | Hiển thị form theo Figma ở chế độ không chỉnh sửa, giải thích chưa hỗ trợ; Save draft/Submit bị khóa |
| Review | Trạng thái từ backend và transition submit/approve/request-changes; quyền, lý do, revision, actor/thời gian | Không suy đoán Draft/Approved từ upload; bộ lọc và hành động khóa với giải thích |
| Ingestion | Job gắn revision đã duyệt, trạng thái/giai đoạn/lỗi, API chạy/retry, chunks và văn bản trích xuất thật | Chỉ preview nội dung gốc R2; phần extracted text/chunks/job hiển thị chưa có dữ liệu/API; không tạo job giả |
| Thay file | Luồng thay thế có version/revision, expected version, điều kiện ghi và quy tắc review/ingestion lại | Replace bị khóa, giải thích API upload hiện tại từ chối trùng tên |
| Tìm toàn bộ và đếm tổng | API tìm kiếm/đếm có phạm vi/quyền rõ ràng hoặc chỉ mục thư viện riêng | Tìm trên file đã tải; không quét đệ quy toàn bucket |
| Làm mới URL staging | Endpoint ký lại cho cùng phiên hoặc hủy phiên/giải phóng giữ chỗ an toàn | Nếu URL PUT hết hạn nhưng phiên chưa hết hạn và chưa có staging: giải thích chờ phiên hết hạn; không bỏ điều kiện chống ghi đè |
| Khả năng/giới hạn động | Endpoint trả allowlist MIME và giới hạn upload/preview hiện tại | Dùng allowlist `.md/.txt/.json` và giới hạn mặc định 10 MiB đã tài liệu hóa; backend vẫn xác thực và có thể trả 422 nếu cấu hình khác |

Storage, Review và Ingestion phải luôn là ba thông tin độc lập. Object hiện hữu có thể xác nhận được lưu trên R2; việc đã được duyệt, lập chỉ mục hoặc sẵn sàng cho chatbot không thể suy ra từ HEAD/listing.
