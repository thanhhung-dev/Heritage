"""Full password reset flow test with token extraction"""
import asyncio
import sys
import httpx
import time
import re

# Fix for Windows ProactorEventLoop incompatibility with psycopg
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def test_full_password_reset():
    base_url = "http://localhost:8000"
    test_email = f"fullresettest{int(time.time())}@example.com"
    initial_password = "TestPassword123!"
    new_password = "NewSecurePassword456@"

    print("=" * 80)
    print("FULL PASSWORD RESET FLOW TEST")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Create test account
        print(f"\n1. Creating test account: {test_email}")
        try:
            response = await client.post(
                f"{base_url}/api/auth/register",
                json={
                    "username": test_email.split('@')[0],
                    "email": test_email,
                    "password": initial_password
                }
            )
            if response.status_code in [200, 201]:
                print("   ✓ Account created")
            else:
                print(f"   ✗ Failed: {response.status_code} - {response.text}")
                return
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            return

        # Step 2: Login with initial password
        print(f"\n2. Login with initial password")
        try:
            response = await client.post(
                f"{base_url}/api/auth/login",
                json={"username_or_email": test_email, "password": initial_password}
            )
            if response.status_code == 200:
                print("   ✓ Login successful")
            else:
                print(f"   ✗ Failed: {response.status_code} - {response.text}")
                return
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            return

        # Step 3: Request password reset
        print(f"\n3. Request password reset")
        try:
            response = await client.post(
                f"{base_url}/api/auth/forgot-password",
                json={"email": test_email}
            )
            if response.status_code == 200:
                print("   ✓ Reset request sent")
                print("   → Check backend terminal for reset link!")
            else:
                print(f"   ✗ Failed: {response.status_code} - {response.text}")
                return
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            return

        # Step 4: Manually extract token (simulate user clicking link)
        print(f"\n4. Simulating token extraction")
        print("   → In real scenario, user would click email link")
        print("   → For testing, we'll create a token manually")
        
        # Import the token creation function and get account's password hash
        import sys
        sys.path.insert(0, "c:\\Capstone 1\\Heritage")
        from apps.backend.core.security import create_password_reset_token
        from apps.backend.db.base import configure_database, AsyncSessionLocal
        from apps.backend.models.admin import AdminAccount
        from sqlalchemy import select
        
        # Fetch the account to get its password_hash
        configure_database("postgresql+psycopg://postgres:hung2003@localhost:5432/heritage")
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AdminAccount).where(AdminAccount.email == test_email))
            account = result.scalar_one_or_none()
            if not account:
                print(f"   ✗ Could not fetch account for token creation")
                return
            reset_token = create_password_reset_token(test_email, account.password_hash)
        
        print(f"   ✓ Token created: {reset_token[:20]}...")

        # Step 5: Reset password with token
        print(f"\n5. Reset password with token")
        try:
            response = await client.post(
                f"{base_url}/api/auth/reset-password",
                json={"token": reset_token, "new_password": new_password}
            )
            if response.status_code == 200:
                print("   ✓ Password reset successful")
            else:
                print(f"   ✗ Failed: {response.status_code} - {response.text}")
                return
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            return

        # Step 6: Try login with OLD password (should fail)
        print(f"\n6. Try login with OLD password (should fail)")
        try:
            response = await client.post(
                f"{base_url}/api/auth/login",
                json={"username_or_email": test_email, "password": initial_password}
            )
            if response.status_code == 401:
                print("   ✓ Old password rejected (correct!)")
            else:
                print(f"   ✗ SECURITY ISSUE: Old password still works!")
                return
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            return

        # Step 7: Login with NEW password (should succeed)
        print(f"\n7. Login with NEW password")
        try:
            response = await client.post(
                f"{base_url}/api/auth/login",
                json={"username_or_email": test_email, "password": new_password}
            )
            if response.status_code == 200:
                print("   ✓ Login with new password successful!")
            else:
                print(f"   ✗ Failed: {response.status_code} - {response.text}")
                return
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            return

        # Step 8: Try reusing token (should fail)
        print(f"\n8. Try reusing token (should fail)")
        try:
            response = await client.post(
                f"{base_url}/api/auth/reset-password",
                json={"token": reset_token, "new_password": "AnotherPassword789"}
            )
            if response.status_code == 400:
                print("   ✓ Token reuse blocked (correct!)")
            else:
                print(f"   ✗ SECURITY ISSUE: Token can be reused!")
                return
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            return

    print("\n" + "=" * 80)
    print("🎉 ALL PASSWORD RESET FLOW TESTS PASSED!")
    print("=" * 80)
    print(f"\nTest account: {test_email}")
    print(f"Final password: {new_password}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_full_password_reset())
