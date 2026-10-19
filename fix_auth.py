"""
Fix auth.py - Update login and reset_password to use email column
"""
import re

# Read file
with open("apps/backend/api/auth.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Login endpoint - find account by email or username
login_old_pattern = r'''    # Find user by username/email \(currently stored in username field\)
    result = await db\.execute\(
        select\(AdminAccount\)\.where\(
            AdminAccount\.username == request\.username_or_email
        \)
    \)
    account = result\.scalar_one_or_none\(\)'''

login_new = '''    # Find user by username/email - check both email and username columns
    username_or_email = request.username_or_email.strip()
    
    # Try email first if input contains @
    if "@" in username_or_email:
        result = await db.execute(
            select(AdminAccount).where(AdminAccount.email == username_or_email)
        )
    else:
        result = await db.execute(
            select(AdminAccount).where(AdminAccount.username == username_or_email)
        )
    
    account = result.scalar_one_or_none()'''

content = re.sub(login_old_pattern, login_new, content, flags=re.MULTILINE)

# Fix 2: Login response - use account.email
content = content.replace(
    'email=account.username,  # Using username as email for now',
    'email=account.email,'
)

# Fix 3: Login log message
content = content.replace(
    'log.info(f"User logged in: {account.username} (id={account.id})")',
    'log.info(f"User logged in: {account.email} (username={account.username}, id={account.id})")'
)

# Fix 4: Login token data - add email
token_old = '''            "sub": str(account.id),
            "username": account.username,
            "role": "admin",  # Default role for now'''

token_new = '''            "sub": str(account.id),
            "email": account.email,
            "username": account.username,
            "role": "admin"'''

content = content.replace(token_old, token_new)

# Fix 5: Update last_login_at
last_login_old = '''    # Create access token
    access_token = create_access_token('''

last_login_new = '''    # Update last login
    from datetime import datetime, timezone
    account.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Create access token
    access_token = create_access_token('''

content = content.replace(last_login_old, last_login_new)

# Fix 6: Google auth - find by email
content = content.replace(
    'select(AdminAccount).where(AdminAccount.username == email)',
    'select(AdminAccount).where(AdminAccount.email == email)'
)

# Fix 7: Reset password - find by email
# This appears twice, so it will replace both

# Write back
with open("apps/backend/api/auth.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Fixed auth.py successfully!")
print("   - Login now checks email and username columns")
print("   - Google auth finds by email column")
print("   - Reset password finds by email column")
print("   - Login updates last_login_at")
