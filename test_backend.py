"""
Test backend startup and auth endpoints
"""
import asyncio
import sys

# Fix Windows ProactorEventLoop issue with psycopg
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx
import uvicorn
from multiprocessing import Process
import time

def start_backend():
    """Start backend server"""
    uvicorn.run("apps.backend.app:app", host="127.0.0.1", port=8000, log_level="info")

async def test_auth_endpoints():
    """Test registration and login"""
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n" + "="*80)
        print("TESTING AUTHENTICATION ENDPOINTS")
        print("="*80)
        
        # Test 1: Health check
        print("\n1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/api/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        
        # Test 2: Register new user
        print("\n2. Testing registration...")
        register_data = {
            "email": f"test_{int(time.time())}@example.com",
            "username": f"testuser_{int(time.time())}",
            "password": "TestPassword123"
        }
        try:
            response = await client.post(
                f"{base_url}/api/auth/register",
                json=register_data
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            
            if response.status_code != 201:
                print(f"   ❌ Registration failed!")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        
        # Test 3: Login with email
        print("\n3. Testing login with email...")
        login_data = {
            "username_or_email": register_data["email"],
            "password": register_data["password"]
        }
        try:
            response = await client.post(
                f"{base_url}/api/auth/login",
                json=login_data
            )
            print(f"   Status: {response.status_code}")
            result = response.json()
            print(f"   Response: {result}")
            
            if response.status_code != 200:
                print(f"   ❌ Login failed!")
                return False
            
            token = result.get("access_token")
            print(f"   ✅ Got access token: {token[:50]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        
        # Test 4: Login with username
        print("\n4. Testing login with username...")
        login_data = {
            "username_or_email": register_data["username"],
            "password": register_data["password"]
        }
        try:
            response = await client.post(
                f"{base_url}/api/auth/login",
                json=login_data
            )
            print(f"   Status: {response.status_code}")
            result = response.json()
            print(f"   Response: {result}")
            
            if response.status_code != 200:
                print(f"   ❌ Login failed!")
                return False
            
            print(f"   ✅ Login with username successful!")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        
        # Test 5: Get user info with token
        print("\n5. Testing /me endpoint...")
        try:
            response = await client.get(
                f"{base_url}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            
            if response.status_code != 200:
                print(f"   ❌ /me failed!")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80 + "\n")
        return True

if __name__ == "__main__":
    print("Starting backend server...")
    print("This will start the server and run tests")
    print("Press Ctrl+C to stop\n")
    
    # Start backend in subprocess
    backend_process = Process(target=start_backend)
    backend_process.start()
    
    # Wait for backend to start
    print("Waiting for backend to start...")
    time.sleep(5)
    
    try:
        # Run tests
        result = asyncio.run(test_auth_endpoints())
        
        if result:
            print("\n✅ Backend is working correctly!")
            print("   You can now:")
            print("   1. Keep the server running for manual testing")
            print("   2. Test frontend login/register")
            print("   3. Press Ctrl+C to stop")
            
            # Keep running
            backend_process.join()
        else:
            print("\n❌ Tests failed!")
            backend_process.terminate()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nStopping backend...")
        backend_process.terminate()
        backend_process.join()
        print("Backend stopped.")
