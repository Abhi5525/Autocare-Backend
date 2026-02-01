# test_fix.py
import requests

BASE_URL = "http://localhost:8000"

def test_manual_service_fix():
    print("Testing manual service creation fix...")
    
    # Get mechanic token (mechanics typically create services)
    login_form = {"username": "mechanic_test@example.com", "password": "Test@1234"}
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data=login_form,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        print("Mechanic login failed, trying to get owner token...")
        # Fallback to owner if mechanic doesn't exist
        login_form = {"username": "owner_test@example.com", "password": "Test@1234"}
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data=login_form,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            print("Login failed")
            return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get owner token for vehicle access
    owner_login_form = {"username": "owner_test@example.com", "password": "Test@1234"}
    owner_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data=owner_login_form,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if owner_response.status_code != 200:
        print("Owner login failed")
        return
        
    owner_token = owner_response.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Get a vehicle using owner token
    response = requests.get(f"{BASE_URL}/api/vehicles/my-vehicles", headers=owner_headers)
    if response.status_code != 200 or not response.json():
        print("No vehicles found")
        return
    
    vehicle = response.json()[0]
    vehicle_id = vehicle["id"]
    
    # Create manual service with correct fields that match ServiceRecord model
    manual_service = {
        "vehicle_id": vehicle_id,
        "service_type": "regular_service",
        "description": "Regular maintenance service",  # Correct field name
        "service_notes": "All checks passed. Vehicle in good condition.",  # Correct field name
        "cost_estimate": 3000.0,  # Correct field name
        "service_date": "2026-02-01"  # Correct field name
    }
    
    response = requests.post(
        f"{BASE_URL}/api/services/",
        json=manual_service,
        headers=headers  # Use mechanic token for service creation
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print("✅ Manual service created successfully!")
        print(f"Service ID: {response.json()['id']}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_manual_service_fix()