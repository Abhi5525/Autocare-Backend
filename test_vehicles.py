# test_vehicles.py
import requests
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

def get_auth_token():
    """Get authentication token for testing"""
    # First register or login
    login_data = {
        "email": "vehicle_test@example.com",
        "phone": "9876543222",
        "full_name": "Vehicle Test User",
        "password": "Test@1234"
    }
    
    # Try to register
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=login_data)
        if response.status_code == 201:
            return response.json()["access_token"]
    except:
        pass
    
    # If registration fails, try login
    login_form = {
        "username": "vehicle_test@example.com",
        "password": "Test@1234"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data=login_form,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    
    return None

def test_vehicles():
    print("🚗 Testing Vehicle Management System")
    print("=" * 60)
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Create a vehicle
    print("\n1. Creating a new vehicle...")
    vehicle_data = {
        "registration_number": "MH12AB1234",
        "make": "Maruti Suzuki",
        "model": "Swift Dzire",
        "year": 2020,
        "color": "Pearl White",
        "vehicle_type": "car",
        "fuel_type": "petrol",
        "transmission": "manual",
        "owner_id": 4  # Will be overridden by current user
    }
    
    response = requests.post(
        f"{BASE_URL}/api/vehicles/",
        json=vehicle_data,
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        vehicle = response.json()
        vehicle_id = vehicle["id"]
        print(f"   ✅ Vehicle created!")
        print(f"   ID: {vehicle_id}")
        print(f"   Registration: {vehicle['registration_number']}")
        print(f"   Make/Model: {vehicle['make']} {vehicle['model']}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
        return
    
    # Test 2: Get my vehicles
    print("\n2. Getting my vehicles...")
    response = requests.get(f"{BASE_URL}/api/vehicles/my-vehicles", headers=headers)
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        vehicles = response.json()
        print(f"   ✅ Found {len(vehicles)} vehicles")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Test 3: Get specific vehicle
    print(f"\n3. Getting vehicle {vehicle_id}...")
    response = requests.get(f"{BASE_URL}/api/vehicles/{vehicle_id}", headers=headers)
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        vehicle = response.json()
        print(f"   ✅ Vehicle retrieved")
        print(f"   QR Code URL: {vehicle.get('qr_code_url', 'Not generated')}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Test 4: Update vehicle
    print(f"\n4. Updating vehicle {vehicle_id}...")
    update_data = {
        "color": "Midnight Blue",
        "current_odometer": 25000
    }
    
    response = requests.put(
        f"{BASE_URL}/api/vehicles/{vehicle_id}",
        json=update_data,
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Vehicle updated")
        vehicle = response.json()
        print(f"   New color: {vehicle['color']}")
        print(f"   Odometer: {vehicle['current_odometer']}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Test 5: Get vehicle by registration
    print(f"\n5. Getting vehicle by registration...")
    response = requests.get(
        f"{BASE_URL}/api/vehicles/registration/MH12AB1234",
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Found by registration")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Test 6: Get QR code
    print(f"\n6. Getting QR code for vehicle...")
    response = requests.get(
        f"{BASE_URL}/api/vehicles/{vehicle_id}/qr",
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        qr_info = response.json()
        print(f"   ✅ QR code: {qr_info.get('qr_code_url')}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    print("\n" + "=" * 60)
    print("✅ Vehicle management tests complete!")
    print(f"📁 Check uploads directory: app/uploads/")
    print(f"🔗 API Docs: {BASE_URL}/docs")

if __name__ == "__main__":
    test_vehicles()