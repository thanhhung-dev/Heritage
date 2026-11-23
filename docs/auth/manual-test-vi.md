# Test tay Login và Register

Ngày cập nhật: 23/11/2026. Nhánh `fix/auth-login-register-validation`; UI tiếng Anh.

## Test trong môi trường đang dùng

1. Chạy frontend rồi mở `/sign-up` trên cổng FE của bạn, thường là [localhost:3000/sign-up](http://localhost:3000/sign-up).
2. Điền email hợp lệ, username từ 3–50 ký tự và mật khẩu 7 ký tự. Bấm **Sign Up**: phải thấy **Password must be at least 8 characters.** ngay dưới ô; Network không có POST register.
3. Thử email sai, username ngắn/dài hoặc chứa khoảng trắng bên trong, password chỉ có dấu cách: phải báo lỗi đúng trường. Dấu cách đầu/cuối email/username được trim; password được giữ nguyên.
4. Đổi mật khẩu đủ 8 ký tự trở lên và đăng ký bằng email thử chưa tồn tại. Nút loading, không gửi hai request khi bấm nhanh hai lần. Thành công chuyển sang `/sign-in?registered=1` với thông báo **Account created successfully**.
5. Đăng ký lại email đó hoặc username đã dùng: thấy lỗi dễ hiểu, không có `[object Object]`, không có hai toast/alert trùng.
6. Ở `/sign-in`, thử sai mật khẩu/email không có: nhận **Incorrect email or password.** Không lưu phiên mới.
7. Đăng nhập đúng: lưu phiên và điều hướng đến trang chính, hoặc đường dẫn `next` nội bộ. Ví dụ `/sign-in?next=%2Ffaq` phải quay về `/faq`; URL bên ngoài bị bỏ qua.
8. Tài khoản mới là **USER**. Không kỳ vọng tự truy cập Admin. Tài khoản inactive hoặc `locked_until` còn hiệu lực bị từ chối; tài khoản khóa đã hết hạn có thể đăng nhập.
9. DevTools → Network → Offline rồi submit: thấy lỗi kết nối và có thể thử lại sau khi Online. Thử trên màn hình 390px: đọc được lỗi và không tràn ngang.
10. Show/Hide password chỉ đổi cách hiển thị, không đổi giá trị. Không có email/password trong URL của form submit.

FE hiện có thể đang gọi BE dev theo `.env.local`. Backend của nhánh này cần được triển khai hoặc FE cần trỏ BE local để kiểm tra nghiệp vụ mới. Không thay role hay xóa dữ liệu thật để thử lỗi.

## Chạy bộ browser test hoàn toàn cục bộ

Dùng các cổng còn trống 18928, 3006, 9225 và Node 22 trở lên. App test dùng router auth thật, database SQLite trong bộ nhớ, key giả chỉ cho test. Các control endpoint không được mount vào ứng dụng production.

Terminal 1, từ root repository:

```powershell
& 'C:\Capstone 1\.venv\Scripts\python.exe' -m uvicorn apps.backend.tests.auth_browser_app:app --host 127.0.0.1 --port 18928 --no-access-log
```

Terminal 2, từ `apps/frontend`, chạy trực tiếp để dùng đúng biến API:

```powershell
$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:18928/api'
node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3006
```

Terminal 3, mở Edge bằng profile riêng:

```powershell
$reviewProfile = Join-Path $env:TEMP ('heritage-auth-' + [guid]::NewGuid().ToString('N'))
$browserProcess = Start-Process -FilePath 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' -WindowStyle Hidden -PassThru -ArgumentList @(
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=9225', ('--user-data-dir="' + $reviewProfile + '"')
)
```

Terminal 4, từ `apps/frontend`:

```powershell
node tests/browser/auth-browser.cjs
```

Harness reset dữ liệu test trước mỗi lượt, chặn request auth sang origin khác, thực hiện các tình huống và lưu ảnh vào `.next/auth-browser-review/`. Đặt `AUTH_BROWSER_ARTIFACTS` nếu muốn thư mục khác. Dừng các terminal server bằng Ctrl+C, đóng đúng `$browserProcess.Id` sau khi dùng.

Để tự bấm thử với môi trường bộ nhớ, mở [sign-up cổng 3006](http://127.0.0.1:3006/sign-up), tạo tài khoản tùy ý rồi đăng nhập. Dữ liệu mất khi dừng API test. Đây không phải tài khoản được tạo trên BE dev.

## Cấu hình cần có khi triển khai thật

- Backend phải có database với bảng account/roles, một role tên USER và private `JWT_SECRET_KEY`. Không dùng JWT key ví dụ công khai; cấu hình thiếu trả 503 rõ ràng.
- Google chỉ hoạt động khi `GOOGLE_CLIENT_ID` của BE khớp `NEXT_PUBLIC_GOOGLE_CLIENT_ID` của FE và origin được cấu hình tại Google. Kiểm thử hiện tại mock xác minh Google, chưa thay thế nghiệm thu OAuth thật.
- GitHub/Facebook đang khóa vì chưa có tích hợp. Quên/reset mật khẩu giữ API hiện có, không nằm trong nghiệm thu gửi email của task này.
