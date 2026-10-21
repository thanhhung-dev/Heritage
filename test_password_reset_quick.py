"""Quick test script for forgot/reset password endpoints"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api"
TEST_EMAIL = "caovankhoa11@gmail.com"


async def test_forgot_password():
    """Test forgot password endpoint"""
    print("🧪 Testing POST /auth/forgot-password...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/forgot-password",
            json={"email": TEST_EMAIL},
            timeout=10.0
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Forgot password endpoint working!")
            print("💡 Check backend terminal for reset link (if SMTP not configured)")
            return True
        else:
            print("❌ Test failed!")
            return False


async def test_reset_password():
    """Test reset password endpoint with a token"""
    token = input("\n📋 Enter reset token from backend terminal: ").strip()
    if not token:
        print("❌ Token is required!")
        return False
    
    new_password = "TestPassword123!@#"
    
    print(f"\n🧪 Testing POST /auth/reset-password...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/reset-password",
            json={
                "token": token,
                "new_password": new_password
            },
            timeout=10.0
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Reset password endpoint working!")
            print(f"🔐 Password changed successfully to: {new_password}")
            return True
        else:
            print("❌ Test failed!")
            return False


async def main():
    print("=" * 60)
    print("Heritage Password Reset Flow Test")
    print("=" * 60)
    print()
    
    try:
        # Test forgot password
        success = await test_forgot_password()
        
        if not success:
            return
        
        # Ask if user wants to test reset
        print()
        choice = input("Do you want to test reset password? (y/n): ").strip().lower()
        if choice == "y":
            await test_reset_password()
            
    except httpx.ConnectError:
        print("❌ ERROR: Cannot connect to backend!")
        print("💡 Make sure backend is running: python -m uvicorn apps.backend.app:app --reload")
    except Exception as e:
        print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
