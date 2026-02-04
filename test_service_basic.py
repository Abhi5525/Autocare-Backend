# test_service_basic.py
import requests
import json
from datetime import datetime, date

BASE_URL = "http://localhost:8000"

def get_auth_token(role="owner"):
    """Get authentication token for existing users"""
    if role == "mechanic":
        email = "mechanic_test@example.com"
    else:
        email = "owner_test@example.com"
    
    login_form = {
        "username": email,
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

def test_basic_service_creation():
    print("🔧 Testing Basic Service Creation")
    print("=" * 50)
    
    # Get tokens
    owner_token = get_auth_token("owner")
    mechanic_token = get_auth_token("mechanic")
    
    if not owner_token:
        print("❌ Failed to get owner token")
        return
    
    if not mechanic_token:
        print("❌ Failed to get mechanic token")
        return
        
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    mechanic_headers = {"Authorization": f"Bearer {mechanic_token}"}
    
    # Get existing vehicles
    print("\n1. Getting existing vehicles...")
    response = requests.get(f"{BASE_URL}/api/vehicles/my-vehicles", headers=owner_headers)
    
    if response.status_code != 200 or not response.json():
        print("   ❌ No vehicles found, creating one first...")
        # Create a vehicle
        vehicle_data = {
            "registration_number": f"DL{datetime.now().microsecond % 100}XY{datetime.now().second}{datetime.now().minute}",
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "color": "White",
            "vehicle_type": "car",
            "fuel_type": "petrol",
            "transmission": "automatic"
        }
        
        response = requests.post(f"{BASE_URL}/api/vehicles/", json=vehicle_data, headers=owner_headers)
        if response.status_code != 201:
            print(f"   ❌ Failed to create vehicle: {response.text}")
            return
        vehicle = response.json()
    else:
        vehicles = response.json()
        vehicle = vehicles[0]
    
    vehicle_id = vehicle["id"]
    print(f"   ✅ Using vehicle: {vehicle['registration_number']} (ID: {vehicle_id})")
    
    # Test basic service creation with correct fields
    print("\n2. Creating basic service record...")
    service_data = {
        "vehicle_id": vehicle_id,
        "service_type": "regular_service",
        "description": "Basic oil change and inspection",
        "service_notes": "Changed engine oil, checked all fluids, inspected brakes and tires.",
        "cost_estimate": 2500.0,
        "service_date": "2026-02-01"
    }
    
    response = requests.post(f"{BASE_URL}/api/services/", json=service_data, headers=mechanic_headers)
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        service = response.json()
        print(f"   ✅ Service created successfully!")
        print(f"   Service ID: {service['id']}")
        print(f"   Status: {service['status']}")
        print(f"   Description: {service['description']}")
        return service['id']
    else:
        print(f"   ❌ Error: {response.text}")
        return None

def test_service_update():
    print("\n3. Testing service update...")
    
    # Get mechanic token
    mechanic_token = get_auth_token("mechanic")
    if not mechanic_token:
        print("   ❌ Failed to get mechanic token")
        return
        
    mechanic_headers = {"Authorization": f"Bearer {mechanic_token}"}
    
    # Get services to find one to update
    response = requests.get(f"{BASE_URL}/api/services/drafts", headers=mechanic_headers)
    
    if response.status_code != 200 or not response.json():
        print("   ❌ No services found to update")
        return
    
    services = response.json()
    service_id = services[0]['id']
    
    # Update service
    update_data = {
        "final_cost": 2800.0,
        "status": "completed",
        "completion_date": "2026-02-01"
    }
    
    response = requests.patch(f"{BASE_URL}/api/services/{service_id}", json=update_data, headers=mechanic_headers)
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        service = response.json()
        print(f"   ✅ Service updated successfully!")
        print(f"   Service ID: {service['id']}")
        print(f"   Status: {service['status']}")
        print(f"   Final Cost: Rs{service.get('final_cost', 'N/A')}")
    else:
        print(f"   ❌ Error: {response.text}")

if __name__ == "__main__":
    service_id = test_basic_service_creation()
    if service_id:
        test_service_update()