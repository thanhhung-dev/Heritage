# 🚀 Quick Fix: Password Reset Email Configuration

## ✅ Hiện trạng
- ✅ Token expiry đã tăng từ 15 phút → **30 phút**
- ✅ Backend API đang chạy trên `http://127.0.0.1:8000`
- ✅ Frontend kết nối được với backend
- ⚠️ Email chưa gửi thực tế → Link reset password hiển thị trong **Terminal Backend**

---

## 🔧 Cách khởi động Backend

### PowerShell:
```powershell
.\start-backend.ps1
```

### Command Prompt:
```cmd
start-backend.bat
```

### Manual:
```bash
python -m uvicorn apps.backend.app:app --host 127.0.0.1 --port 8000 --reload
```

---

## 📧 Cấu hình SMTP để gửi email thực

### Bước 1: Lấy App Password từ Gmail
1. Truy cập: https://myaccount.google.com/apppasswords
2. Tạo App Password mới với tên "Heritage Backend"
3. Copy mật khẩu 16 ký tự (dạng: `abcd efgh ijkl mnop`)

### Bước 2: Thêm vào file `.env`
Thêm các dòng sau vào cuối file `.env`:

```bash
# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=caovankhoa11@gmail.com
SMTP_PASSWORD=abcdefghijklmnop  # Thay bằng App Password từ bước 1
SMTP_SENDER_EMAIL=caovankhoa11@gmail.com
SMTP_SENDER_NAME=Heritage Support
SMTP_USE_TLS=true
```

### Bước 3: Khởi động lại Backend
```bash
# Dừng backend hiện tại (Ctrl+C)
# Chạy lại:
.\start-backend.ps1
```

### Bước 4: Test
1. Vào http://localhost:3000/forgot-password
2. Nhập email: `caovankhoa11@gmail.com`
3. Kiểm tra hòm thư Gmail → Email "Khôi phục mật khẩu - Heritage"

---

## 📝 Test Password Reset Flow

### Test với Terminal (không cần SMTP):
1. Khởi động backend: `.\start-backend.ps1`
2. Vào frontend: http://localhost:3000/forgot-password
3. Nhập email đã đăng ký
4. **Kiểm tra Terminal backend** → Copy link reset password
5. Mở link trong browser → Nhập mật khẩu mới

### Test với Email (sau khi config SMTP):
1. Vào frontend: http://localhost:3000/forgot-password
2. Nhập email đã đăng ký
3. **Kiểm tra Gmail** → Nhấn button "Đặt lại mật khẩu"
4. Nhập mật khẩu mới (12+ ký tự, chữ hoa thường số đặc biệt)

---

## ✅ Các thay đổi đã thực hiện

### 1. Backend (`apps/backend/core/security.py`)
```python
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30  # Tăng từ 15 → 30 phút
```

### 2. Startup Scripts
- `start-backend.ps1` - PowerShell script
- `start-backend.bat` - Command Prompt script

---

## 🐛 Troubleshooting

### Lỗi "Failed to fetch"
**Nguyên nhân**: Backend chưa chạy  
**Giải pháp**: Chạy `.\start-backend.ps1`

### Email không gửi được
**Nguyên nhân**: SMTP chưa config hoặc sai App Password  
**Giải pháp**: 
1. Kiểm tra `.env` có đầy đủ SMTP config
2. Verify App Password từ Google (phải là 16 ký tự, không có dấu cách)
3. Khởi động lại backend

### Token hết hạn
**Nguyên nhân**: Token có hiệu lực 30 phút  
**Giải pháp**: Yêu cầu link reset mới từ `/forgot-password`

---

## 📌 Lưu ý quan trọng

1. **Token expiry**: 30 phút (khớp với email template)
2. **CORS**: Đã config cho `localhost:3000` và `127.0.0.1:3000`
3. **Bảo mật**: Token tự động hủy sau khi reset password thành công
4. **Email fallback**: Nếu SMTP chưa config, link sẽ hiển thị trong Terminal backend

---

## 🎯 Next Steps

1. ✅ Backend đã chạy → Test forgot password flow
2. ⏳ Config SMTP (tùy chọn) → Gửi email thực
3. 🧪 Test với nhiều email khác nhau
4. 📊 Monitor logs trong Terminal backend
