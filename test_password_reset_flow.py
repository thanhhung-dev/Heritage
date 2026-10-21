"""
Test password reset flow
"""
import asyncio
import sys
import time

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_password_reset():
    import httpx
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n" + "="*80)
        print("PASSWORD RESET TEST")
        print("="*80)
        
        # Create test account first
        timestamp = int(time.time())
        test_email = f"resettest{timestamp}@example.com"
        test_username = f"resetuser{timestamp}"
        original_password = "OldPassword123"
        
        print(f"\n1. Creating test account: {test_email}")
        try:
            response = await client.post(
                f"{base_url}/api/auth/register",
                json={
                    "email": test_email,
                    "username": test_username,
                    "password": original_password
                }
            )
            if response.status_code != 201:
                print(f"   FAILED to register: {response.json()}")
                return False
            print(f"   SUCCESS - Account created")
        except Exception as e:
            print(f"   ERROR: {e}")
            return False
        
        # Test password reset request
        print(f"\n2. Requesting password reset for: {test_email}")
        try:
            response = await client.post(
                f"{base_url}/api/auth/forgot-password",
                json={"email": test_email}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   SUCCESS: {result.get('message')}")
                print(f"   Check backend terminal for reset link!")
            else:
                print(f"   FAILED: {response.json()}")
                return False
        except Exception as e:
            print(f"   ERROR: {e}")
            return False
        
        # Test non-existent email (should still return 200 for security)
        print(f"\n3. Testing with non-existent email (security check)...")
        try:
            response = await client.post(
                f"{base_url}/api/auth/forgot-password",
                json={"email": "nonexistent@example.com"}
            )
            if response.status_code == 200:
                print(f"   SUCCESS - Returns 200 even for non-existent email (good!)")
            else:
                print(f"   WARNING: Status {response.status_code} reveals email existence")
        except Exception as e:
            print(f"   ERROR: {e}")
            return False
        
        print("\n" + "="*80)
        print("PASSWORD RESET REQUEST TESTS PASSED!")
        print("="*80)
        print("\nNOTE: To complete the reset flow:")
        print("1. Check backend terminal for the reset link")
        print("2. Copy the token from the link")
        print("3. Use POST /api/auth/reset-password with:")
        print("   {\"token\": \"<token>\", \"new_password\": \"NewPassword123\"}")
        print("="*80 + "\n")
        return True

if __name__ == "__main__":
    result = asyncio.run(test_password_reset())
    if not result:
        sys.exit(1)
