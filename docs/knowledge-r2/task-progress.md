# Tiến độ công việc Knowledge Library

Thời gian bên dưới là ước lượng lập kế hoạch theo yêu cầu, không phải số giờ thực tế đã làm. Mỗi công việc được chia không quá 8 giờ.

| Mã | Công việc | Ước lượng | Trạng thái |
|---|---|---:|---|
| BE-R2-01 | Tái sử dụng tích hợp R2; cố định bucket knowledge | 3h | Hoàn thành (DONE) |
| BE-R2-02 | Lấy danh sách thư mục/object theo dấu phân cách và phân trang | 6h | Hoàn thành (DONE) |
| BE-R2-03 | Phiên lưu bền vững và upload có chữ ký, có giới hạn | 6h | Hoàn thành (DONE) |
| BE-R2-04 | Xác nhận có kiểm tra, ghi đích nguyên tử và gọi lại an toàn | 4h | Hoàn thành (DONE) |
| BE-R2-05 | Metadata, xem trước văn bản và tải xuống | 5h | Hoàn thành (DONE) |
| BE-R2-06 | Marker thư mục và xóa chính xác một file | 6h | Hoàn thành (DONE) |
| BE-R2-07 | Kiểm tra quyền Admin hiện tại và dữ liệu đầu vào | 5h | Hoàn thành (DONE) |
| BE-R2-08 | Test tự động, tài liệu API và triển khai | 8h | Hoàn thành (DONE) |

Đã rà soát repository. Cây làm việc sạch trước khi bắt đầu task. Công việc nằm trên nhánh riêng `feat/knowledge-r2-library`, phát triển từ `cc03edc`; không bao gồm frontend. Commit từng phần triển khai, kiểm thử và tài liệu nhỏ, có ý nghĩa, đủ để rà soát. Không tự push hoặc deploy.

Kiểm tra cuối: 35/35 test tính năng đạt, gồm 5 test PostgreSQL thật trên tài nguyên tạm dành riêng. Lấy danh sách gốc/thư mục con và HEAD file trên R2 thật đều đạt bằng thao tác chỉ đọc. Bộ hồi quy cũ chạy 68 test, có 65 test đạt; 3 lỗi đã được tái hiện với app trước task và các module cũ không thay đổi. Xem [báo cáo hoàn thành](final-report.md) để biết kết quả chính xác và cấu hình migration/JWT/CORS còn cần triển khai; xem [hướng dẫn test tay](frontend-integration.md#deployment-and-manual-test-steps) để biết cách kiểm tra. Không thay đổi object production hoặc chạy migration trên database ứng dụng.
