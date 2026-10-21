# 📧 Email Configuration Guide - Hướng dẫn cấu hình Email SMTP

## Tổng quan

Hệ thống Heritage hỗ trợ gửi email thực tế cho chức năng **Forgot Password** qua SMTP. Nếu không cấu hình SMTP, hệ thống sẽ in link reset password ra console.

---

## 🎯 Các nhà cung cấp SMTP được hỗ trợ

### 1. Gmail (Khuyên dùng cho development)
- **SMTP Host**: `smtp.gmail.com`
- **SMTP Port**: `587` (TLS) hoặc `465` (SSL)
- **Yêu cầu**: Google App Password (không dùng mật khẩu thường)

### 2. Mailgun (Khuyên dùng cho production)
- **SMTP Host**: `smtp.mailgun.org`
- **SMTP Port**: `587`
- **Yêu cầu**: Mailgun account với domain đã verify

### 3. SendGrid
- **SMTP Host**: `smtp.sendgrid.net`
- **SMTP Port**: `587`
- **Yêu cầu**: SendGrid API key

### 4. Resend
- **SMTP Host**: `smtp.resend.com`
- **SMTP Port**: `587`
- **Yêu cầu**: Resend API key

---

## 📝 Hướng dẫn cấu hình Gmail

### Bước 1: Bật 2-Step Verification

1. Truy cập: https://myaccount.google.com/security
2. Tìm **2-Step Verification** → Click **Turn on**
3. Follow hướng dẫn để bật xác thực 2 bước

### Bước 2: Tạo App Password

1. Sau khi bật 2-Step Verification, quay lại: https://myaccount.google.com/security
2. Tìm **App passwords** (ở cuối phần 2-Step Verification)
3. Click **App passwords**
4. Chọn:
   - **Select app**: Mail
   - **Select device**: Other (Custom name) → Nhập: `Heritage Backend`
5. Click **Generate**
6. Google sẽ hiển thị **16-digit password** (vd: `abcd efgh ijkl mnop`)
7. **Copy password này** (bỏ khoảng trắng: `abcdefghijklmnop`)

### Bước 3: Cấu hình `.env`

Mở file `.env` ở root project và thêm:

```bash
# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_SENDER_EMAIL=your-email@gmail.com
SMTP_SENDER_NAME=Heritage Support
SMTP_USE_TLS=true

# Frontend base URL
FRONTEND_BASE_URL=http://localhost:3000
```

**Lưu ý**: Thay `your-email@gmail.com` bằng Gmail của bạn và `abcdefghijklmnop` bằng App Password vừa tạo.

### Bước 4: Restart Backend

```bash
# Stop backend hiện tại (Ctrl+C)
cd "C:\Capstone 1\Heritage"
$env:PYTHONPATH="C:\Capstone 1\Heritage"
python -m uvicorn apps.backend.app:app --host 127.0.0.1 --port 8000 --reload
```

Kiểm tra log, bạn sẽ thấy:
```
INFO:     Email service initialized: smtp.gmail.com:587
```

---

## 🧪 Test Email Service

### Test qua API:

```bash
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

Nếu email tồn tại trong database, bạn sẽ nhận được email thật tại hòm thư!

---

## 🚀 Production Setup (Mailgun)

### Bước 1: Tạo tài khoản Mailgun

1. Truy cập: https://www.mailgun.com/
2. Đăng ký Free tier (5,000 emails/month free)
3. Verify domain của bạn (vd: `heritage.vn`)

### Bước 2: Lấy SMTP credentials

1. Login Mailgun Dashboard
2. Vào **Sending** → **Domain settings**
3. Chọn domain đã verify
4. Copy **SMTP credentials**:
   - **SMTP hostname**: `smtp.mailgun.org`
   - **Port**: `587`
   - **Username**: `postmaster@your-domain.com`
   - **Password**: `<your-smtp-password>`

### Bước 3: Cấu hình production `.env`

```bash
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@heritage.vn
SMTP_PASSWORD=<mailgun-smtp-password>
SMTP_SENDER_EMAIL=noreply@heritage.vn
SMTP_SENDER_NAME=Heritage Support
SMTP_USE_TLS=true

FRONTEND_BASE_URL=https://heritage.vn
```

---

## 🔒 Security Best Practices

1. **Không commit `.env` file lên Git** (đã có trong `.gitignore`)
2. **Dùng App Password**, không dùng mật khẩu Gmail thật
3. **Production phải dùng dịch vụ chuyên dụng** (Mailgun/SendGrid), không dùng Gmail
4. **Rotate SMTP password định kỳ** (3-6 tháng/lần)
5. **Monitor email delivery logs** để phát hiện spam/abuse

---

## 🐛 Troubleshooting

### Lỗi: "Email service disabled"

**Nguyên nhân**: `.env` chưa có đủ config SMTP.

**Giải pháp**: Đảm bảo tất cả biến sau có giá trị:
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_SENDER_EMAIL`

### Lỗi: "535-5.7.8 Username and Password not accepted"

**Nguyên nhân**: Gmail chưa bật 2-Step Verification hoặc App Password sai.

**Giải pháp**: 
1. Bật 2-Step Verification
2. Tạo lại App Password
3. Paste đúng 16 ký tự (không có khoảng trắng)

### Lỗi: "Connection timeout"

**Nguyên nhân**: Firewall block port 587/465.

**Giải pháp**:
```bash
# Test SMTP connection
telnet smtp.gmail.com 587
```

Nếu không connect được, check firewall/antivirus.

### Email gửi nhưng vào Spam

**Nguyên nhân**: Domain chưa có SPF/DKIM records.

**Giải pháp** (Production):
1. Verify domain với Mailgun/SendGrid
2. Config SPF/DKIM records theo hướng dẫn của họ

---

## 📊 Email Template Preview

Email được gửi có format đẹp với:
- ✅ HTML responsive design
- ✅ Dark gradient header với logo
- ✅ Button "Đặt lại mật khẩu" dễ nhìn
- ✅ Fallback link nếu button không hoạt động
- ✅ Warning bảo mật (token expire trong 30 phút)
- ✅ Plain text fallback cho email client cũ

---

## 📚 Tài liệu tham khảo

- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [Mailgun SMTP](https://documentation.mailgun.com/en/latest/user_manual.html#sending-via-smtp)
- [SendGrid SMTP](https://docs.sendgrid.com/for-developers/sending-email/integrating-with-the-smtp-api)
- [Python smtplib](https://docs.python.org/3/library/smtplib.html)

---

**Lưu ý**: Nếu chỉ develop local, có thể bỏ qua config SMTP. Hệ thống sẽ tự động print link reset ra Terminal.
