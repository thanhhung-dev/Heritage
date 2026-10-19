# Next.js Build Error Fix - Root Layout Issue

## Vấn đề ban đầu
```
Error: not-found.tsx doesn't have a root layout. 
To fix this error, make sure every page has a root layout.
```

## Nguyên nhân
Project có **2 app directories** song song:
- `app/` (legacy, không có root layout)
- `lib/app/` (hiện tại, có root layout đầy đủ)

Next.js 14 mặc định tìm `app/` directory và báo lỗi vì:
- `app/about/[slug]/page.tsx` nằm ngoài route group
- Không có `app/layout.tsx` (root layout)
- `app/(public)/layout.tsx` chỉ áp dụng cho route group `(public)`

## Giải pháp áp dụng

### 1. Di chuyển App Directory Structure
```bash
# Rename legacy app → app.legacy
app/ → app.legacy/

# Move current lib/app → app (root level)
lib/app/ → app/
```

**Sau khi di chuyển**:
```
apps/frontend/
├── app/                          # ✅ Main app directory
│   ├── layout.tsx               # ✅ Root layout
│   ├── metadata.ts              # Global metadata
│   ├── (admin)/                 # Route group
│   │   └── admin/
│   │       ├── layout.tsx
│   │       └── page.tsx
│   ├── (public)/                # Route group
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── explore/
│   │   ├── library/
│   │   └── ...
│   ├── (standalone)/            # Route group
│   │   ├── sign-in/
│   │   ├── sign-up/
│   │   ├── forgot-password/     # ✅ HER-170
│   │   └── reset-password/      # ✅ HER-170
│   └── (tour)/                  # Route group
│       └── content/[slug]/
│           └── layout.tsx
└── app.legacy/                  # ❌ Archived (không còn sử dụng)
    ├── about/[slug]/
    ├── (public)/
    └── not-found.tsx
```

### 2. Fix Import Paths
**Forgot Password Page** (`app/(standalone)/forgot-password/page.tsx`):
```typescript
// ❌ Before
import logo from "@/access/logo.svg";
import caveImage from "@/access/cave-optimized.jpg";

// ✅ After
import logo from "@/access/icons/auth-logo.svg";
import caveImage from "@/access/images/auth-cave.png";
```

**Reset Password Page** (`app/(standalone)/reset-password/page.tsx`):
```typescript
// ❌ Before
import logo from "@/access/logo.svg";
import caveImage from "@/access/cave-optimized.jpg";

// ✅ After
import logo from "@/access/icons/auth-logo.svg";
import caveImage from "@/access/images/auth-cave.png";
```

### 3. Fix TypeScript Errors

#### A. Missing Type Import
**File**: `components/public-shell/PublicShell.tsx`
```typescript
// ✅ Added
import type { PublicAccount } from "@/features/account/types";
```

#### B. Null Safety for Token
**File**: `features/auth/ResetPasswordForm.tsx`
```typescript
async function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  setTouched({ newPassword: true, confirmPassword: true });
  
  // ✅ Added token validation
  if (!token) {
    message.error("Token không hợp lệ. Vui lòng yêu cầu đặt lại mật khẩu mới.");
    return;
  }
  
  // ... rest of validation
  const response = await resetPassword(token, newPassword); // ✅ token is now guaranteed to be string
}
```

## Verification

### Build Output
```bash
npm run build
```

✅ **Success**:
```
✓ Compiled successfully
Route (app)                              Size     First Load JS
├ ○ /forgot-password                     3.98 kB         206 kB
├ ○ /reset-password                      1.79 kB         207 kB
├ ○ /sign-in                             166 B           209 kB
└ ○ /sign-up                             166 B           209 kB
```

### Dev Server
```bash
npm run dev
```

✅ **Success**:
```
- Local:        http://localhost:3000
✓ Ready in 2.6s
✓ Compiled / in 15.9s
```

## Files Changed

### Structural Changes
- ✅ `app/` → `app.legacy/` (renamed)
- ✅ `lib/app/` → `app/` (moved)

### Code Fixes
1. `app/(standalone)/forgot-password/page.tsx` - Fixed asset imports
2. `app/(standalone)/reset-password/page.tsx` - Fixed asset imports  
3. `features/auth/ResetPasswordForm.tsx` - Added token null check
4. `components/public-shell/PublicShell.tsx` - Added PublicAccount import

## Best Practices Applied

1. ✅ **Single App Directory**: Chỉ dùng 1 `app/` directory duy nhất
2. ✅ **Root Layout**: Mọi page đều inherit từ `app/layout.tsx`
3. ✅ **Route Groups**: Organize routes bằng `(group)` folders
4. ✅ **Type Safety**: Validate nullable values trước khi sử dụng
5. ✅ **Import Consistency**: Dùng actual paths thay vì non-existent paths

## Testing Checklist

- [x] `npm run build` passes without errors
- [x] `npm run dev` starts successfully
- [x] TypeScript compilation passes
- [x] All routes render correctly:
  - [x] `/sign-in`
  - [x] `/forgot-password`
  - [x] `/reset-password`
  - [x] `/` (home)
  - [x] `/library`
  - [x] `/map`

## Next Steps

1. **Manual Testing**: Test complete password reset flow:
   ```
   /sign-in → Quên mật khẩu? → /forgot-password → 
   Enter email → Check backend terminal → 
   Copy token → /reset-password?token=... → 
   Enter new password → /sign-in
   ```

2. **Clean up**: Có thể xóa `app.legacy/` sau khi confirm không còn dùng

3. **Deploy**: Build output đã sẵn sàng cho production

---

**Date**: 2026-10-18  
**Ticket**: HER-170 - Forgot/Reset Password  
**Status**: ✅ Build Fixed, Ready for Testing
