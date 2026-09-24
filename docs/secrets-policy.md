# Environment and secrets policy

Tài liệu này là quy ước bắt buộc cho local, Docker, Jenkins và môi trường triển
khai của HeritageGraph.

## 1. Nguồn cấu hình

| Ngữ cảnh | File mẫu được commit | File thật hoặc nơi lưu | Có được commit không? |
|---|---|---|---|
| Backend local | `.env.example` | `.env` ở project root | Không |
| Frontend local | `apps/frontend/.env.local.example` | `apps/frontend/.env.local` | Không |
| Docker Compose local | `.env.example` | `.env` ở project root | Không |
| Jenkins | Không lưu secret trong repository | Jenkins Credentials | Không |
| Production | Không dùng file secret trong image | Secret manager của nền tảng triển khai | Không |

Chỉ commit file mẫu với giá trị giả, an toàn để công khai. Khi thêm một biến môi
trường mới, cập nhật đúng file mẫu và tài liệu này trong cùng pull request.

## 2. Phân loại biến hiện tại

- `POSTGRES_PASSWORD` và phần mật khẩu trong `DATABASE_URL` là **secret**.
- `DATABASE_URL` được xem là **secret** vì chứa thông tin xác thực.
- `NEXT_PUBLIC_API_URL`, `BACKEND_PORT`, `FRONTEND_PORT`,
  `INFERENCE_BACKEND`, `LLAMA_SERVER_URL`, `LLAMA_SERVER_TIMEOUT` và
  `LLAMA_GPU_LAYERS` là cấu hình, không phải secret.
- Mọi biến bắt đầu bằng `NEXT_PUBLIC_` được đóng gói vào JavaScript phía trình
  duyệt. Không đặt API key, token, password hoặc chuỗi kết nối vào biến loại này.
- Hiện tại ứng dụng không yêu cầu API key. Nếu tích hợp dịch vụ ngoài sau này,
  API key phải đi qua environment/secret store và file mẫu chỉ chứa placeholder.

## 3. Quy tắc sử dụng

1. Không hardcode secret trong source code, Dockerfile, `docker-compose.yml`,
   `Jenkinsfile`, script, test fixture, log, ảnh chụp màn hình hoặc tài liệu.
2. Không truyền secret bằng Docker build argument hoặc bake secret vào image.
   Chỉ inject secret lúc container chạy.
3. Local chỉ lưu secret trong các file `.env*` đã được `.gitignore` bảo vệ.
   Không chia sẻ các file này qua chat hoặc email.
4. Jenkins lưu giá trị trong **Jenkins Credentials** và bind vào environment chỉ
   trong stage cần dùng. Không `echo`, in environment hoặc bật shell tracing khi
   đang xử lý secret.
5. Production dùng secret manager của nền tảng triển khai, phân quyền tối thiểu
   và tách credential theo từng môi trường. Không tái sử dụng mật khẩu local.
6. Password chứa ký tự đặc biệt trong `DATABASE_URL` phải được URL-encode.

## 4. Khởi tạo local

Backend chạy trực tiếp:

```bash
cp .env.example .env
```

Frontend chạy trực tiếp:

```bash
cp apps/frontend/.env.local.example apps/frontend/.env.local
```

Docker Compose:

```bash
cp .env.example .env
```

Sau khi sao chép, thay toàn bộ placeholder trước khi chạy. Có thể kiểm tra file
không bị Git theo dõi bằng `git status --ignored --short`.

## 5. Khi secret bị lộ

1. Thu hồi hoặc đổi secret ngay; không chờ xóa khỏi Git rồi mới rotate.
2. Kiểm tra log và lịch sử sử dụng credential để xác định phạm vi ảnh hưởng.
3. Xóa secret khỏi lịch sử Git nếu đã push và thông báo cho các thành viên phải
   đồng bộ lại repository.
4. Tạo credential mới với quyền tối thiểu và cập nhật secret store tương ứng.

Việc xóa một commit hoặc thêm file vào `.gitignore` không làm secret đã lộ trở
lại an toàn; luôn phải rotate credential.
