# test_auth.py
import requests
import json

BASE_URL = "http://localhost:8000"

def test_auth():
    print("🔐 Testing Authentication System")
    print("=" * 60)
    
    # Test 1: Register a new user
    print("\n1. Testing user registration...")
    register_data = {
        "email": "test111@example.com",
        "phone": "9876543200",
        "full_name": "Test User",
        "password": "Test@1234"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 201:
        token = response.json()["access_token"]
        print("   ✅ Registration successful!")
        print(f"   Token: {token[:50]}...")
    else:
        print(f"   ❌ Error: {response.json()}")
        return
    
    # Test 2: Login with email
    print("\n2. Testing login with email...")
    login_data = {
        "username": "test@example.com",
        "password": "Test@1234"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Login successful!")
    else:
        print(f"   ❌ Error: {response.json()}")
    
    # Test 3: Get current user profile
    print("\n3. Testing get current user profile...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        user = response.json()
        print(f"   ✅ User profile retrieved!")
        print(f"   Name: {user['full_name']}")
        print(f"   Email: {user['email']}")
        print(f"   Role: {user['role']}")
    else:
        print(f"   ❌ Error: {response.json()}")
    
    # Test 4: Login with JSON
    print("\n4. Testing login with JSON...")
    login_json = {
        "email": "test@example.com",
        "password": "Test@1234"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/login-json", json=login_json)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ JSON login successful!")
    else:
        print(f"   ❌ Error: {response.json()}")
    
    print("\n" + "=" * 60)
    print("✅ Authentication system test complete!")

if __name__ == "__main__":
    test_auth()