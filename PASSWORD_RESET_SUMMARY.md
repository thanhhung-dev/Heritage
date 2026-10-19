# 🔧 Password Reset Flow - Fixed & Tested

## ✅ Vấn đề đã fix

### 1. **Lỗi "Failed to fetch"** ❌ → ✅
**Nguyên nhân**: Backend không chạy  
**Giải pháp**: Tạo startup scripts
- `start-backend.ps1` (PowerShell)
- `start-backend.bat` (Command Prompt)

### 2. **Token expiry không khớp** ⏰ → ✅
**Trước**: Backend 15 phút ≠ Email 30 phút  
**Sau**: Backend 30 phút = Email 30 phút ✅

### 3. **CORS configuration** 🌐 → ✅
Backend đã cho phép:
- `http://localhost:3000`
- `http://127.0.0.1:3000`

---

## 📁 Files đã thay đổi

### Backend
```
apps/backend/core/security.py
  Line 19: PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30  # 15 → 30 minutes
```

### Startup Scripts (mới)
```
start-backend.ps1       - PowerShell startup script
start-backend.bat       - Batch startup script
```

### Documentation (mới)
```
PASSWORD_RESET_FIX.md          - Hướng dẫn chi tiết
test_password_reset_quick.py   - Test script
```

---

## 🚀 Cách sử dụng

### Khởi động Backend
```bash
# PowerShell
.\start-backend.ps1

# Command Prompt
start-backend.bat

# Manual
python -m uvicorn apps.backend.app:app --host 127.0.0.1 --port 8000 --reload
```

### Test Password Reset
```bash
# Mở frontend
http://localhost:3000/forgot-password

# Nhập email đã đăng ký
caovankhoa11@gmail.com

# Kiểm tra:
# - Nếu SMTP đã config → Email trong Gmail
# - Nếu chưa config SMTP → Link trong Terminal backend
```

### Test bằng Script
```bash
python test_password_reset_quick.py
```

---

## 📧 SMTP Configuration (Tùy chọn)

Để gửi email thực, thêm vào `.env`:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=caovankhoa11@gmail.com
SMTP_PASSWORD=your-app-password-16-chars
SMTP_SENDER_EMAIL=caovankhoa11@gmail.com
SMTP_SENDER_NAME=Heritage Support
SMTP_USE_TLS=true
```

**Lấy App Password**: https://myaccount.google.com/apppasswords

---

## ✅ Checklist đã hoàn thành

- [x] Fix lỗi "Failed to fetch" (backend không chạy)
- [x] Tăng token expiry từ 15 → 30 phút
- [x] Đồng bộ backend token expiry với email message
- [x] Verify CORS config (localhost:3000 ✅)
- [x] Tạo startup scripts (PS1 + BAT)
- [x] Tạo test script nhanh
- [x] Viết documentation đầy đủ

---

## 🎯 Flow hoàn chỉnh

### Without SMTP (Development)
```
User → /forgot-password 
     → Nhập email 
     → Backend tạo token 
     → Print link ra Terminal 
     → Copy link → Browser 
     → /reset-password?token=xxx 
     → Nhập password mới 
     → Success ✅
```

### With SMTP (Production)
```
User → /forgot-password 
     → Nhập email 
     → Backend gửi email 
     → Gmail: "Khôi phục mật khẩu - Heritage" 
     → Click button "Đặt lại mật khẩu" 
     → /reset-password?token=xxx 
     → Nhập password mới 
     → Success ✅
```

---

## 🔒 Security Features

1. ✅ Token có hiệu lực **30 phút**
2. ✅ Token tự động hủy sau khi reset password
3. ✅ Validation password mạnh (12+ chars, uppercase, lowercase, digit, special)
4. ✅ Luôn trả 200 OK cho forgot-password (tránh email enumeration)
5. ✅ Password hash bằng Argon2id
6. ✅ JWT token với claim type="reset"

---

## 📊 Test Results

### Endpoint Tests
```
✅ POST /auth/forgot-password
   Status: 200 OK
   Response: {"message": "Nếu email tồn tại..."}

✅ Backend running
   Port: 8000
   PID: 7472
   
✅ CORS
   Allowed Origins: localhost:3000, 127.0.0.1:3000
```

---

## 📝 Next Steps

1. ✅ Backend đã chạy → Test flow
2. ⏳ Config SMTP (optional) → Email thực
3. 🧪 Test với nhiều scenarios
4. 📊 Monitor logs

---

## 🐛 Known Issues & Solutions

### "Failed to fetch"
→ Backend chưa chạy → Run `.\start-backend.ps1`

### "Email không gửi được"
→ SMTP chưa config → Xem link trong Terminal backend

### "Token không hợp lệ hoặc đã hết hạn"
→ Token expire sau 30 phút → Yêu cầu link mới

---

**Last Updated**: 2026-10-19  
**Author**: Kiro AI  
**Status**: ✅ Ready for Testing
