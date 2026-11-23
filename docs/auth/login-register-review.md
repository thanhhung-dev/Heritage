# Rà soát đăng ký và đăng nhập

Ngày bắt đầu: 23/11/2026. Nhánh `fix/auth-login-register-validation`.

## Phát hiện từ code và ảnh lỗi

- Form đăng ký chấp nhận mật khẩu 6 ký tự nhưng API yêu cầu 8. Lỗi FastAPI 422 là danh sách object; service ép `detail` thành Error message, gây `[object Object]`.
- Form dùng nhánh lỗi Axios trong khi service dùng fetch, không gắn lỗi server vào trường tương ứng và hiển thị đồng thời toast/alert.
- Đăng ký tự tính `MAX(id)+1` không khóa, có thể trùng ID khi chạy đồng thời. Role USER bị gắn cố định bằng ID 1 thay vì tra bảng roles.
- Email đăng ký chưa được chuẩn hóa giống đăng nhập; username và giới hạn FE/BE khác nhau.
- Login chưa kiểm tra `locked_until`, hash không hợp lệ có thể gây 500; form login áp dụng quy tắc độ dài mật khẩu đăng ký không phù hợp với tài khoản cũ.
- Luồng thành công chưa có thông báo bền vững sau đăng ký và bỏ qua `next` khi quay lại từ trang cần đăng nhập.

## Phạm vi đã được yêu cầu

Sửa contract validation hiện có, parser lỗi auth, form và nghiệp vụ tạo/đăng nhập tài khoản; thêm kiểm thử ở ranh giới HTTP và trình duyệt. Giữ tài khoản mới là USER. Không sửa role/dữ liệu tài khoản thật, không ghi vào BE dev, không tự migrate/deploy. Giữ nguyên thay đổi sẵn có của người dùng ở tài liệu Knowledge Library.

Tiến độ: đang triển khai. Kết quả kiểm thử sẽ được ghi sau khi chạy thực tế.
