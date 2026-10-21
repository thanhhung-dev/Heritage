"""
Fix auth.py part 2 - Fix Google auth account creation
"""

# Read file
with open("apps/backend/api/auth.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix Google auth account creation
google_auth_old = '''        account = AdminAccount(
            username=email,
            password_hash=password_hash,
            is_active=True,
        )'''

google_auth_new = '''        account = AdminAccount(
            email=email,
            username=email.split('@')[0],  # Use email prefix as username
            password_hash=password_hash,
            is_active=True,
        )'''

content = content.replace(google_auth_old, google_auth_new)

# Write back
with open("apps/backend/api/auth.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Fixed Google auth account creation!")
