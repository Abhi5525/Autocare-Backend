# test_service_advanced.py
import requests
import json
from datetime import datetime, date

BASE_URL = "http://localhost:8000"

def get_auth_token(role="owner"):
    """Get authentication token for existing users"""
    if role == "mechanic":
        email = "mechanic_test@example.com"
    elif role == "admin":
        email = "admin_test@example.com"
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

def test_service_workflow():
    print("🔧 Testing Complete Service Workflow")
    print("=" * 50)
    
    # Get tokens
    owner_token = get_auth_token("owner")
    mechanic_token = get_auth_token("mechanic")
    
    if not owner_token or not mechanic_token:
        print("❌ Failed to get authentication tokens")
        return
        
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    mechanic_headers = {"Authorization": f"Bearer {mechanic_token}"}
    
    # Get existing vehicles
    print("\n1. Getting vehicle for service...")
    response = requests.get(f"{BASE_URL}/api/vehicles/my-vehicles", headers=owner_headers)
    
    if response.status_code != 200 or not response.json():
        print("   ❌ No vehicles found")
        return
    
    vehicles = response.json()
    vehicle = vehicles[0]
    vehicle_id = vehicle["id"]
    print(f"   ✅ Using vehicle: {vehicle['registration_number']} (ID: {vehicle_id})")
    
    # Create detailed service record
    print("\n2. Creating detailed service record...")
    service_data = {
        "vehicle_id": vehicle_id,
        "service_type": "repair",
        "description": "Brake system repair and maintenance",
        "service_notes": "Replaced front brake pads, checked brake fluid levels, inspected brake lines. Customer reported squeaking noise - resolved after pad replacement. Test drive completed successfully.",
        "cost_estimate": 4500.0,
        "service_date": "2026-02-01"
    }
    
    response = requests.post(f"{BASE_URL}/api/services/", json=service_data, headers=mechanic_headers)
    
    if response.status_code != 201:
        print(f"   ❌ Failed to create service: {response.text}")
        return
    
    service = response.json()
    service_id = service["id"]
    print(f"   ✅ Service created: ID {service_id}")
    
    # Get specific service
    print("\n3. Retrieving service details...")
    response = requests.get(f"{BASE_URL}/api/services/{service_id}", headers=mechanic_headers)
    
    if response.status_code == 200:
        service_details = response.json()
        print(f"   ✅ Service retrieved:")
        print(f"   - Type: {service_details['service_type']}")
        print(f"   - Status: {service_details['status']}")
        print(f"   - Estimate: ₹{service_details['cost_estimate']}")
        print(f"   - Date: {service_details['service_date']}")
    else:
        print(f"   ❌ Failed to retrieve service: {response.text}")
    
    # Update service with completion details
    print("\n4. Completing service...")
    completion_data = {
        "status": "completed",
        "final_cost": 4200.0,
        "completion_date": "2026-02-01",
        "service_notes": "Brake system repair completed successfully. All components functioning properly. Customer satisfied with repair quality."
    }
    
    response = requests.patch(f"{BASE_URL}/api/services/{service_id}", json=completion_data, headers=mechanic_headers)
    
    if response.status_code == 200:
        completed_service = response.json()
        print(f"   ✅ Service completed!")
        print(f"   - Final Status: {completed_service['status']}")
        print(f"   - Final Cost: ₹{completed_service.get('final_cost', 'N/A')}")
        print(f"   - Completion Date: {completed_service.get('completion_date', 'N/A')}")
    else:
        print(f"   ❌ Failed to complete service: {response.text}")
    
    # Get all services for the vehicle
    print("\n5. Getting all services...")
    response = requests.get(f"{BASE_URL}/api/services/approved", headers=owner_headers)
    
    if response.status_code == 200:
        all_services = response.json()
        print(f"   ✅ Found {len(all_services)} services")
        for svc in all_services:
            print(f"   - ID: {svc['id']}, Type: {svc['service_type']}, Status: {svc['status']}")
    else:
        print(f"   ❌ Failed to get services: {response.text}")

def test_service_parts():
    print("\n6. Testing service with parts...")
    
    # Get tokens
    mechanic_token = get_auth_token("mechanic")
    owner_token = get_auth_token("owner")
    
    if not mechanic_token or not owner_token:
        print("   ❌ Failed to get tokens")
        return
        
    mechanic_headers = {"Authorization": f"Bearer {mechanic_token}"}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Get vehicle
    response = requests.get(f"{BASE_URL}/api/vehicles/my-vehicles", headers=owner_headers)
    if response.status_code != 200 or not response.json():
        print("   ❌ No vehicles found")
        return
    
    vehicle_id = response.json()[0]["id"]
    
    # Create service with parts information in notes
    service_data = {
        "vehicle_id": vehicle_id,
        "service_type": "regular_service",
        "description": "Oil change with filter replacement",
        "service_notes": "Parts used: Engine Oil (5L) - ₹800, Oil Filter - ₹300, Air Filter - ₹250. Labor: ₹500. Total parts cost: ₹1350, Total service: ₹1850",
        "cost_estimate": 1850.0,
        "service_date": "2026-02-01"
    }
    
    response = requests.post(f"{BASE_URL}/api/services/", json=service_data, headers=mechanic_headers)
    
    if response.status_code == 201:
        service = response.json()
        print(f"   ✅ Service with parts created: ID {service['id']}")
        print(f"   - Description: {service['description']}")
        print(f"   - Cost: ₹{service['cost_estimate']}")
    else:
        print(f"   ❌ Failed to create service with parts: {response.text}")

if __name__ == "__main__":
    test_service_workflow()
    test_service_parts()