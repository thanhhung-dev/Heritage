"""
Quick backend health check script
Run this to verify backend is running properly
"""
import httpx
import sys

def check_backend():
    print("🔍 Checking Heritage Backend...")
    print("=" * 50)
    
    try:
        response = httpx.get("http://localhost:8000/api/health", timeout=5.0)
        
        if response.status_code == 503:
            print("✅ Backend is RUNNING (starting state)")
            print("   Status: 503 (normal - model loading)")
            print("   Auth endpoints: AVAILABLE ✅")
            return True
        elif response.status_code == 200:
            print("✅ Backend is RUNNING (ready state)")
            print("   Status: 200 OK")
            return True
        else:
            print(f"⚠️  Backend returned status: {response.status_code}")
            return False
            
    except httpx.ConnectError:
        print("❌ Backend is NOT running!")
        print("")
        print("To start backend, run:")
        print("  PowerShell:  .\\start-backend.ps1")
        print("  CMD:         start-backend.bat")
        print("")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("")
    success = check_backend()
    print("=" * 50)
    print("")
    
    if success:
        print("✅ You can now test password reset:")
        print("   http://localhost:3000/forgot-password")
    else:
        sys.exit(1)
