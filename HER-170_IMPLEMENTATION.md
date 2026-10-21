# HER-170: Forgot Password + Reset Password - Implementation Guide

## ✅ Đã hoàn thành

### Backend (`apps/backend/`)

1. **`core/security.py`**:
   - ✅ `create_password_reset_token(email: str) -> str`: Tạo JWT token với expire 15 phút, claim type="reset"
   - ✅ `verify_password_reset_token(token: str) -> Optional[str]`: Verify token và trả về email nếu hợp lệ

2. **`schemas/auth.py`**:
   - ✅ `ForgotPasswordRequest(email: EmailStr)`
   - ✅ `ResetPasswordRequest(token: str, new_password: str)` với validation min_length=8

3. **`api/auth.py`**:
   - ✅ `POST /api/auth/forgot-password`: Nhận email, tạo token, print link ra console
   - ✅ `POST /api/auth/reset-password`: Verify token, update password, trả về success message

### Frontend (`apps/frontend/`)

1. **`services/authService.ts`**:
   - ✅ `forgotPassword(email: string)`: Gọi API forgot-password
   - ✅ `resetPassword(token: string, newPassword: string)`: Gọi API reset-password

2. **Components**:
   - ✅ `features/auth/ForgotPasswordForm.tsx`: Form nhập email với validation
   - ✅ `features/auth/ResetPasswordForm.tsx`: Form nhập password mới + confirm với validation (12+ ký tự, hoa thường số đặc biệt)

3. **Pages**:
   - ✅ `lib/app/(standalone)/forgot-password/page.tsx`: Trang forgot password
   - ✅ `lib/app/(standalone)/reset-password/page.tsx`: Trang reset password với token từ URL

4. **UI Updates**:
   - ✅ `features/auth/SignInForm.tsx`: Enable nút "Quên mật khẩu?" và link tới `/forgot-password`

## 🧪 Cách test

### Backend Test

1. Start backend server:
```bash
cd "C:\Capstone 1\Heritage"
.venv\Scripts\activate
uvicorn apps.backend.app:app --reload --port 8000
```

2. Chạy test script (ở terminal khác):
```bash
python test_password_reset.py
```

3. Hoặc test thủ công với curl/Postman:

**Forgot Password:**
```bash
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"test@example.com\"}"
```

**Reset Password:**
```bash
curl -X POST http://localhost:8000/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"<token-from-console>\", \"new_password\": \"NewPassword123!\"}"
```

### Frontend Test

1. Start frontend dev server:
```bash
cd "C:\Capstone 1\Heritage\apps\frontend"
npm run dev
```

2. Test flow:
   - Mở http://localhost:3000/sign-in
   - Click "Quên mật khẩu?"
   - Nhập email → Submit
   - Copy link từ backend terminal
   - Paste link vào browser
   - Nhập password mới + confirm
   - Submit → Redirect về sign-in

## 📋 Password Rules

- Tối thiểu 12 ký tự
- Ít nhất 1 chữ hoa (A-Z)
- Ít nhất 1 chữ thường (a-z)
- Ít nhất 1 số (0-9)
- Ít nhất 1 ký tự đặc biệt (!@#$%^&*...)

## 🔒 Security Features

- Token expire sau 15 phút
- Luôn trả 200 OK cho forgot-password (tránh email enumeration)
- Password được hash bằng Argon2
- Token chứa email trong JWT claim

## 📁 Files đã tạo/sửa

### Backend:
- `apps/backend/core/security.py` (thêm 2 functions)
- `apps/backend/schemas/auth.py` (thêm 2 schemas)
- `apps/backend/api/auth.py` (thêm 2 endpoints)

### Frontend:
- `apps/frontend/services/authService.ts` (thêm 2 functions)
- `apps/frontend/features/auth/ForgotPasswordForm.tsx` (mới)
- `apps/frontend/features/auth/ResetPasswordForm.tsx` (mới)
- `apps/frontend/lib/app/(standalone)/forgot-password/page.tsx` (mới)
- `apps/frontend/lib/app/(standalone)/reset-password/page.tsx` (mới)
- `apps/frontend/features/auth/SignInForm.tsx` (enable forgot button)

### Test:
- `test_password_reset.py` (script test API)

## ✨ Features

- ✅ Full validation client + server side
- ✅ Loading states và error handling
- ✅ Success messages với Ant Design message
- ✅ Auto redirect sau reset thành công
- ✅ Token validation trên URL
- ✅ Security best practices
- ✅ Tận dụng UI/CSS modules hiện có
- ✅ Tiếng Việt cho messages
