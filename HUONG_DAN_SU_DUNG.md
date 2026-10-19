# 🎉 HOÀN TẤT FIX LỖI PASSWORD RESET

## ✅ Đã Fix Xong

### 1. Lỗi "Failed to fetch" khi gửi link khôi phục mật khẩu
**Nguyên nhân**: Backend không chạy  
**Giải pháp**: Tạo script khởi động tự động

### 2. Token expiry không khớp giữa backend và email
**Trước**: Backend 15 phút ≠ Email 30 phút ❌  
**Sau**: Backend 30 phút = Email 30 phút ✅

---

## 🚀 CÁCH SỬ DỤNG (3 BƯỚC)

### Bước 1: Khởi động Backend
Mở PowerShell trong thư mục `Heritage`:
```powershell
.\start-backend.ps1
```

Hoặc Command Prompt:
```cmd
start-backend.bat
```

### Bước 2: Test Forgot Password
1. Mở trình duyệt: `http://localhost:3000/forgot-password`
2. Nhập email đã đăng ký: `caovankhoa11@gmail.com`
3. **Kiểm tra Terminal backend** → Copy link reset password

### Bước 3: Reset Password
1. Paste link vào trình duyệt
2. Nhập mật khẩu mới (tối thiểu 12 ký tự, có chữ HOA, chữ thường, số, ký tự đặc biệt)
3. Xong! ✅

---

## 📧 GỬI EMAIL THỰC (Tùy chọn)

Nếu muốn gửi email thực thay vì xem link trong Terminal:

### 1. Lấy App Password từ Google
- Truy cập: https://myaccount.google.com/apppasswords
- Tạo App Password mới với tên "Heritage Backend"
- Copy mật khẩu 16 ký tự

### 2. Thêm vào file `.env`
Mở file `.env` trong thư mục gốc, thêm các dòng sau:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=caovankhoa11@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # Thay bằng App Password từ bước 1 (bỏ khoảng trắng)
SMTP_SENDER_EMAIL=caovankhoa11@gmail.com
SMTP_SENDER_NAME=Heritage Support
SMTP_USE_TLS=true
```

### 3. Restart Backend
```powershell
# Dừng backend hiện tại (Ctrl+C)
# Chạy lại
.\start-backend.ps1
```

Giờ khi test forgot password, email sẽ gửi đến Gmail thay vì hiển thị trong Terminal.

---

## 📁 CÁC FILE ĐÃ THAY ĐỔI

### Backend Code
```
apps/backend/core/security.py
  Dòng 19: PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30  # Đã tăng từ 15 → 30 phút
```

### Scripts mới (Khởi động backend dễ dàng)
```
start-backend.ps1       - Script PowerShell
start-backend.bat       - Script Command Prompt
```

### Documentation
```
QUICKSTART_PASSWORD_RESET.md  - Hướng dẫn nhanh (English)
PASSWORD_RESET_FIX.md         - Hướng dẫn chi tiết SMTP
PASSWORD_RESET_SUMMARY.md     - Tóm tắt kỹ thuật
FIX_SUMMARY.txt               - Tổng hợp fix
HUONG_DAN_SU_DUNG.md          - File này (Tiếng Việt)
```

---

## 🔒 BẢO MẬT

- ✅ Token có hiệu lực **30 phút** (khớp với thông báo trong email)
- ✅ Token tự động vô hiệu sau khi đổi mật khẩu thành công
- ✅ Password phải đủ mạnh: 12+ ký tự, HOA thường số đặc biệt
- ✅ Password được hash bằng Argon2id
- ✅ Bảo vệ chống email enumeration (luôn trả 200 OK)

---

## 🐛 XỬ LÝ LỖI

### "Failed to fetch" khi ấn nút Submit
**Nguyên nhân**: Backend chưa chạy  
**Giải pháp**: Chạy `.\start-backend.ps1`

### "Token không hợp lệ hoặc đã hết hạn"
**Nguyên nhân**: Token chỉ có hiệu lực 30 phút  
**Giải pháp**: Vào lại `/forgot-password` để yêu cầu link mới

### Email không gửi được
**Nguyên nhân**: SMTP chưa được cấu hình trong `.env`  
**Giải pháp**: Xem link reset trong Terminal backend hoặc config SMTP theo hướng dẫn trên

---

## 📊 KIỂM TRA BACKEND ĐANG CHẠY

Mở PowerShell:
```powershell
netstat -ano | Select-String "8000"
```

Nếu thấy dòng `LISTENING` là backend đang chạy OK.

---

## 🎯 FLOW HOÀN CHỈNH

### Không cần SMTP (Development)
```
User → /forgot-password 
     → Nhập email 
     → Backend tạo token 
     → Link hiển thị trong Terminal 
     → Copy link → Mở trình duyệt 
     → /reset-password?token=xxx 
     → Nhập mật khẩu mới 
     → Success! ✅
```

### Có SMTP (Production)
```
User → /forgot-password 
     → Nhập email 
     → Backend gửi email đến Gmail 
     → Mở email "Khôi phục mật khẩu - Heritage" 
     → Click nút "Đặt lại mật khẩu" 
     → Nhập mật khẩu mới 
     → Success! ✅
```

---

## 💡 LƯU Ý QUAN TRỌNG

1. **Token expiry**: 30 phút (đồng bộ với email)
2. **CORS**: Đã cấu hình cho `localhost:3000` và `127.0.0.1:3000`
3. **Security**: Token tự động hủy sau khi dùng
4. **Backend logs**: Luôn xem Terminal backend để debug

---

## 📞 HỖ TRỢ

Nếu gặp vấn đề:
1. Kiểm tra backend có chạy không (port 8000)
2. Xem logs trong Terminal backend
3. Verify email có trong database không
4. Kiểm tra SMTP config nếu muốn gửi email thực

---

**Trạng thái**: ✅ Đã hoàn thành và sẵn sàng sử dụng  
**Ngày cập nhật**: 19/10/2026  
**By**: Kiro AI

Xem hướng dẫn tiếng Anh: `QUICKSTART_PASSWORD_RESET.md`
