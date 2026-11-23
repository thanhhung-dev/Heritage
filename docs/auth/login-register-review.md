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

## Thay đổi đã hoàn tất

FE dùng chung policy đăng ký 8–1024 ký tự, username 3–50 ký tự có chữ/số và chỉ cho phép chữ, số, `_`, `-`; chuẩn hóa email/username, không trim mật khẩu. Login chỉ yêu cầu mật khẩu không rỗng, không áp dụng lại chính sách tạo mật khẩu với tài khoản cũ.

Parser auth đọc lỗi chuỗi, object có message và danh sách FastAPI 422; không hiển thị input/password trong lỗi. Form có lỗi tại trường, banner dễ đọc, focus về trường lỗi khi request kết thúc, khóa gửi lặp và không tạo toast trùng. Đăng ký thành công chuyển đến Sign in có thông báo rõ; login lưu phiên đã xác thực response rồi chuyển đến đường dẫn `next` nội bộ hợp lệ. Form dùng POST để không đưa thông tin đăng nhập vào URL nếu submit trước khi hydrate. Lỗi ghi storage không để lại nửa phiên mới.

BE tra role USER theo tên, không dùng ID 1. Với PostgreSQL có sequence dùng allocator của DB; bảng legacy không có sequence dùng khóa transaction trước `MAX(id)+1`. Khóa chỉ giữ trong đoạn ghi sau khi Argon2 chạy ở worker; không sửa schema hoặc sequence của môi trường. Duplicate thực sự được bắt sau rollback và trả lỗi nghiệp vụ. Cơ chế khóa đã đối chiếu [PostgreSQL 16](https://www.postgresql.org/docs/16/explicit-locking.html).

Login kiểm tra active/locked_until, không ném 500 khi hash hỏng; `/me` đọc tài khoản và role hiện tại thay vì chỉ trả claims cũ. JWT không được ký hoặc xác minh bằng key mặc định công khai. Root `.env` được nạp trước khi module security đọc cấu hình. Các status 400/401/403/422/503 được mô tả trong OpenAPI.

Đường tạo tài khoản Google dùng chung USER/allocator/lock checks, kiểm tra audience đúng client ID và không coi chuỗi `"false"` là email đã xác minh. Đã đối chiếu [hướng dẫn Google](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token). UI khóa GitHub/Facebook chưa tích hợp và không giữ loading vô hạn sau bước mở One Tap. Chưa nghiệm thu OAuth bằng tài khoản Google thật.

## Kiểm thử thực tế

| Phạm vi | Kết quả |
|---|---|
| FE auth API/policy/storage | 7/7 PASS |
| FE Knowledge regression | 23/23 PASS |
| BE auth HTTP, mock Google và cấu hình JWT | 13/13 PASS |
| BE Knowledge storage/API/contract regression | 31/31 PASS |
| PostgreSQL thật: bảng legacy, sequence, đăng ký trùng đồng thời | 3/3 PASS; database `test_auth_*` riêng đã dọn |
| Bootstrap cấu hình trước import security, không khởi động lifespan | 1/1 PASS |
| TypeScript và lint auth | PASS |
| Next production build trên bản sao tách biệt, không sao chép `.env*` | PASS, tạo 24 trang static; còn 2 warning ảnh tour có sẵn và khuyến nghị optional sharp |
| Edge desktop 1440×1000 và mobile 390×844, dùng API auth thật trên SQLite trong bộ nhớ | PASS |

Tổng: **30 kiểm thử FE + 48 kiểm thử BE đạt**, bao gồm các kiểm thử hồi quy. Không chạy các suite legacy cần ghi vào DB ứng dụng/LLM. Browser đã kiểm tra: mật khẩu 7 ký tự không gửi API; lỗi server gắn đúng trường; 503; chống submit kép; đăng ký thành công; sai thông tin; mất mạng; login lưu USER session và quay về đúng trang; email trùng; response 2xx sai contract không tạo session; mobile không tràn ngang; không JavaScript exception.

Có 7 ảnh tại `.catalog-test-runtime/auth-review/screenshots/`. Những lần chạy browser đầu lỗi do chờ hydration và frontend còn dùng origin API cũ đã được khắc phục. Harness chặn mọi request auth sang origin ngoài API test loopback. Không xác nhận bản BE mới đã có trên dev.

Các lệnh chính, FE từ `apps/frontend`, BE từ root:

```powershell
.\node_modules\.bin\tsx.cmd --test tests/auth-api.test.ts tests/auth-storage.test.ts tests/knowledge-api.test.ts tests/knowledge-folders.test.ts tests/knowledge-operations.test.ts tests/knowledge-upload-transport.test.ts tests/knowledge-upload-queue.test.ts
python -X utf8 -m unittest apps.backend.tests.test_auth_flow apps.backend.tests.test_knowledge_library_api apps.backend.tests.test_knowledge_library_contract apps.backend.tests.test_knowledge_library_storage -q
python -X utf8 -m unittest apps.backend.tests.test_auth_bootstrap -v
```

Test PostgreSQL yêu cầu `AUTH_TEST_DATABASE_URL` dùng `postgresql+psycopg`, host loopback và database bắt đầu `test_`; khi thiếu sẽ SKIP, không tự dùng database ứng dụng.

## Commit và giới hạn

- `768fe3c`: ghi nhận audit ban đầu.
- `8c0ab96`, `d63df25`: parser/policy, validation và thông báo UI.
- `d4137fd`: nghiệp vụ đăng ký USER và login/current account.
- `c464b9f`: kiểm thử PostgreSQL đồng thời.
- `088d4e3`: kiểm tra Google và tái sử dụng tạo tài khoản an toàn.
- `f322200`: rollback phiên khi storage lỗi.
- `4fd9b6e`: chặn credentials trong fallback URL.
- `3d1b18a`: trạng thái provider và giao diện thông báo.
- `4d1134b`, `adadd00`: focus sau request và browser acceptance.
- `864fab0`: không dùng JWT key mặc định, cập nhật contract lỗi.

Chưa deploy/push/migrate. Nếu FE vẫn trỏ `https://dev-api.worldheritagea.tech/api`, phần sửa BE chỉ có hiệu lực sau khi bản mới được triển khai. Cần private `JWT_SECRET_KEY`; Google cần `GOOGLE_CLIENT_ID` ở BE khớp `NEXT_PUBLIC_GOOGLE_CLIENT_ID` ở FE. Không cung cấp tài khoản Admin mặc định hoặc tự nâng quyền người đăng ký.

Hướng dẫn test tay và chạy lại browser: [manual-test-vi.md](manual-test-vi.md).
