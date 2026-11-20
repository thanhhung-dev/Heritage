# Phân tích Figma Document Library

Nguồn: [Heritage trên Figma](https://www.figma.com/design/hyZGcP7zvicYLg3O7X2E2F/Heritage?node-id=0-1). Đã dùng `figma:figma-design-to-code`, đọc `get_design_context` có cấu trúc/component/styles và ảnh render cho từng màn, không suy diễn từ ảnh phẳng. Phản hồi có độ chi tiết đầy đủ, không bị đánh dấu sparse. Không có ánh xạ Code Connect được trả về.

| Màn | Node | Bố cục và tương tác |
|---|---|---|
| Document library | `999:18448` | Sidebar 260px; vùng chính có nền trắng, lề 24px; header tên trang và 2 nút; cây thư mục 220px, khoảng cách nội dung 24px; breadcrumb, tìm tên file, 2 bộ lọc; bảng tên/định dạng-dung lượng/cập nhật/review/ingestion/hành động; phân trang; khung Replace và chú thích |
| Upload modal | `1001:13376` | Overlay rgba(32,31,28,.32), dialog rộng 720px, bo 14px, bóng 0 16px 48px rgba(0,0,0,.15); chọn đích, dropzone, danh sách file, gỡ file, thông báo upload không đưa vào chatbot, footer hủy/upload |
| Upload documents | `1001:10456` | Dùng lại sidebar/cây thư mục; breadcrumb; nút về thư viện; dropzone lớn; bảng hàng đợi có tiến độ từng file và retry/cancel; thẻ chuyển tiếp metadata và thông tin ranh giới storage |
| Edit document metadata | `1001:10725` | 3 thẻ Storage/Review/Ingestion; form tiêu đề, vùng, loại, URL nguồn; thông tin file gốc và quyền chỉnh sửa ở cột phụ; nút Save draft/Submit for review |
| Document details | `999:20173` | Header file, nút xem gốc/tải xuống/thay file; 3 thẻ trạng thái độc lập; cột nội dung văn bản/chunks; cột metadata/file gốc/lỗi ingestion/retry |
| Pending review | `1012:1574` | Bảng tài liệu chờ duyệt, preview trích xuất, thông tin revision, quyết định approve/request changes kèm lý do; không đồng nghĩa với ingestion |
| Ingestion | `999:19206` | Chọn revision đã duyệt; bảng job, tiến độ theo giai đoạn, chi tiết lỗi và retry |
| Ingestion job details | `1001:11315` | Storage/Review/Ingestion riêng; pipeline extract/chunk/BGE-M3/OpenSearch, thời gian và sự kiện theo job |

Các frame desktop có kích thước 1920×1200, trừ job details cao 1269px. Dùng grid/flex responsive thay vì tọa độ tuyệt đối. Modal dùng cơ chế quản lý focus/keyboard của Ant Design; tiến độ và thông báo lỗi phải có nhãn hỗ trợ truy cập.

## Token thiết kế quan sát được

- Nền sidebar `#f8f7f3`, nền ứng dụng `#fbfbf8`, thẻ `#ffffff`.
- Chữ chính `#201f1c`, chữ phụ `#928f86`, chữ trạng thái `#615f57`, avatar `#ebe9e0`.
- Viền đen 10%; bo nút/thẻ 12px, badge 4px; nút cao 32px, khoảng cách nút 8px.
- Font Figma Roboto: tiêu đề 18px/28px, weight 600; nội dung 14px/20px; chú thích và trạng thái 12px/16px. Giới hạn theme trong nhóm trang thư viện, không đổi giao diện các trang Admin khác.
- SVG thật đã được lấy bằng curl từ URL do Figma cung cấp. Bằng chứng gốc và bảng kiểm kích thước nằm ngoài repository tại `.catalog-test-runtime/rag-figma/`; chỉ asset cần cho giao diện cuối mới đưa vào public. Giữ nguyên kích thước gốc của từng SVG, không dùng ảnh Figma làm giao diện.

## Ánh xạ component

Giữ Admin layout/router/auth hiện có. Dùng Ant Design Button/Input/Select/Modal/Table/Progress/App cho hành vi có sẵn, CSS Modules để áp dụng token. Tạo các thành phần dùng chung: shell thư viện, cây thư mục tải theo yêu cầu, breadcrumb, thẻ trạng thái, thông báo chưa hỗ trợ, dropzone và hàng đợi upload; modal/trang upload dùng cùng controller.

## Nội dung Figma phải thay bằng dữ liệu thật

`heritage-documents-demo`, cây Vietnam/Central/Northern/Southern/Drafts, tên người dùng, file PDF/DOCX/CSV, số đếm, trạng thái, phần trăm và job trong thiết kế đều chỉ minh họa. Dữ liệu sản phẩm đến từ backend `knowledge-heritage`. Danh sách hiện không cung cấp review, ingestion, uploader hoặc số bản ghi tổng thể; không tự điền các giá trị đó. MIME upload phải theo backend `.md`, `.txt`, `.json`, không theo gợi ý PDF/DOCX/CSV trong Figma.

Giữ bố cục các phần nâng cao nhưng hiển thị chưa khả dụng và khóa hành động khi thiếu API. Metadata HEAD của object vẫn hoạt động; không đồng nhất nó với metadata biên tập/revision. Xem [ma trận API](api-integration-matrix.md) và [báo cáo thiếu chức năng](feature-gap-report.md).
