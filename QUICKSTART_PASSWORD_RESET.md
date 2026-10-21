# ✅ PASSWORD RESET - FIXED & READY

## 🎯 Tóm tắt nhanh

**Lỗi**: "Failed to fetch" khi gửi link khôi phục mật khẩu  
**Nguyên nhân**: Backend không chạy  
**Đã fix**: ✅ Token expiry 15→30 phút | ✅ Startup scripts | ✅ Documentation

---

## 🚀 Khởi động ngay (3 bước)

### 1️⃣ Start Backend
```powershell
.\start-backend.ps1
```
Hoặc:
```cmd
start-backend.bat
```

### 2️⃣ Test Flow
- Mở browser: `http://localhost:3000/forgot-password`
- Nhập email: `caovankhoa11@gmail.com`
- **Kiểm tra Terminal backend** → Copy link reset password

### 3️⃣ Reset Password
- Mở link từ terminal
- Nhập mật khẩu mới (12+ ký tự, chữ hoa thường số ký tự đặc biệt)
- Done! ✅

---

## 📧 Gửi Email thực (Optional)

Thêm vào file `.env`:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=caovankhoa11@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_SENDER_EMAIL=caovankhoa11@gmail.com
SMTP_SENDER_NAME=Heritage Support
SMTP_USE_TLS=true
```

**Lấy App Password**: https://myaccount.google.com/apppasswords

Sau đó khởi động lại backend → Email sẽ gửi đến Gmail thay vì hiển thị trong Terminal.

---

## ✅ Đã thay đổi gì?

| File | Thay đổi |
|------|----------|
| `apps/backend/core/security.py` | Token expiry: 15→**30 phút** ✅ |
| `start-backend.ps1` | Script khởi động backend (PowerShell) |
| `start-backend.bat` | Script khởi động backend (CMD) |
| `PASSWORD_RESET_FIX.md` | Hướng dẫn chi tiết |
| `PASSWORD_RESET_SUMMARY.md` | Tổng hợp kỹ thuật |
| `test_password_reset_quick.py` | Test script |

---

## 🔒 Bảo mật

- ✅ Token có hiệu lực **30 phút** (khớp với email)
- ✅ Token tự động hủy sau khi reset password
- ✅ Password validation: 12+ chars, uppercase, lowercase, digit, special
- ✅ Argon2id password hashing
- ✅ Email enumeration protection (luôn trả 200 OK)

---

## 🐛 Troubleshooting

**"Failed to fetch"** → Backend chưa chạy → `.\start-backend.ps1`  
**"Token hết hạn"** → Token chỉ có hiệu lực 30 phút → Yêu cầu link mới  
**Email không đến** → SMTP chưa config → Xem link trong Terminal backend

---

## 📚 Chi tiết đầy đủ

- **Setup & SMTP**: Xem `PASSWORD_RESET_FIX.md`
- **Technical Summary**: Xem `PASSWORD_RESET_SUMMARY.md`
- **Test Script**: Run `python test_password_reset_quick.py`

---

**Status**: ✅ Ready for Production  
**Last Updated**: 2026-10-19
