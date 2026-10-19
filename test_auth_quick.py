"""
Quick test registration and login
"""
import asyncio
import sys
import time

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_auth():
    import httpx
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n" + "="*80)
        print("QUICK AUTH TEST")
        print("="*80)
        
        # Test 1: Register
        timestamp = int(time.time())
        register_data = {
            "email": f"test{timestamp}@example.com",
            "username": f"user{timestamp}",
            "password": "TestPassword123"
        }
        
        print(f"\n1. Registering: {register_data['email']}")
        try:
            response = await client.post(
                f"{base_url}/api/auth/register",
                json=register_data
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 201:
                print(f"   SUCCESS - User registered")
            else:
                print(f"   FAILED: {response.json()}")
                return False
        except Exception as e:
            print(f"   ERROR: {e}")
            return False
        
        # Test 2: Login with email
        print(f"\n2. Login with email...")
        try:
            response = await client.post(
                f"{base_url}/api/auth/login",
                json={
                    "username_or_email": register_data["email"],
                    "password": register_data["password"]
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                token = result.get("access_token")
                user = result.get("user", {})
                print(f"   SUCCESS")
                print(f"   Token: {token[:30]}...")
                print(f"   User: {user.get('email')} / {user.get('username')}")
            else:
                print(f"   FAILED: {response.json()}")
                return False
        except Exception as e:
            print(f"   ERROR: {e}")
            return False
        
        # Test 3: Login with username
        print(f"\n3. Login with username...")
        try:
            response = await client.post(
                f"{base_url}/api/auth/login",
                json={
                    "username_or_email": register_data["username"],
                    "password": register_data["password"]
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   SUCCESS - Login with username works!")
            else:
                print(f"   FAILED: {response.json()}")
                return False
        except Exception as e:
            print(f"   ERROR: {e}")
            return False
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED!")
        print("="*80 + "\n")
        return True

if __name__ == "__main__":
    # Backend should already be running on port 8000
    print("Make sure backend is running on port 8000")
    print("Starting tests in 2 seconds...\n")
    time.sleep(2)
    
    result = asyncio.run(test_auth())
    if not result:
        sys.exit(1)
