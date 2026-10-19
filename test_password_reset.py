"""Test script cho forgot/reset password endpoints"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api"
TEST_EMAIL = "test@example.com"


async def test_forgot_password():
    """Test forgot password endpoint"""
    print("Testing POST /auth/forgot-password...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/forgot-password",
            json={"email": TEST_EMAIL}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print("\nCheck backend terminal for reset link!")


async def test_reset_password():
    """Test reset password endpoint with a token"""
    token = input("\nEnter reset token from backend terminal: ").strip()
    new_password = "NewPassword123!"
    
    print(f"\nTesting POST /auth/reset-password...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/reset-password",
            json={
                "token": token,
                "new_password": new_password
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


async def main():
    print("=== Heritage Password Reset API Test ===\n")
    
    try:
        # Test forgot password
        await test_forgot_password()
        
        # Ask if user wants to test reset
        choice = input("\nDo you want to test reset password? (y/n): ").strip().lower()
        if choice == "y":
            await test_reset_password()
            
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(main())
