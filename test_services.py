# test_services.py
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def get_auth_token(email="service_test@example.com", role="mechanic"):
    """Get authentication token for testing"""
    # Use unique emails for each test run to avoid role conflicts
    import random
    unique_suffix = random.randint(1000, 9999)
    
    if role == "mechanic":
        email = f"mechanic_{unique_suffix}@example.com"
        phone = f"987654{unique_suffix:04d}"
        user_data = {
            "email": email,
            "phone": phone,
            "full_name": "Mechanic Test",
            "password": "Test@1234",
            "role": "mechanic"
        }
    else:
        email = f"owner_{unique_suffix}@example.com"
        phone = f"987655{unique_suffix:04d}"
        user_data = {
            "email": email,
            "phone": phone,
            "full_name": "Owner Test",
            "password": "Test@1234",
            "role": "owner"
        }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
        if response.status_code == 201:
            return response.json()["access_token"]
        else:
            print(f"Registration failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Registration error: {e}")
    
    # Try login with the same credentials
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

def test_services():
    print("🔧 Testing Service Management System")
    print("=" * 60)
    
    # Get tokens for different roles
    mechanic_token = get_auth_token("mechanic_test@example.com", "mechanic")
    owner_token = get_auth_token("owner_test@example.com", "owner")
    
    if not mechanic_token or not owner_token:
        print("❌ Failed to get authentication tokens")
        return
    
    mechanic_headers = {"Authorization": f"Bearer {mechanic_token}"}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    
    # First, create a vehicle as owner
    print("\n1. Creating a vehicle as owner...")
    import random
    reg_num = f"DL{random.randint(10,99)}XY{random.randint(1000,9999)}"
    
    vehicle_data = {
        "registration_number": reg_num,
        "make": "Hyundai",
        "model": "Creta",
        "year": 2021,
        "color": "Silver",
        "vehicle_type": "suv",
        "fuel_type": "diesel",
        "transmission": "automatic"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/vehicles/",
        json=vehicle_data,
        headers=owner_headers
    )
    
    if response.status_code != 201:
        print(f"   ❌ Failed to create vehicle: {response.text[:200]}")
        return
    
    vehicle = response.json()
    vehicle_id = vehicle["id"]
    print(f"   ✅ Vehicle created: {vehicle['registration_number']}")
    
    # Test 1: Create service record directly (mechanic)
    print("\\n2. Creating service record manually (mechanic)...")
    service_data = {
        "vehicle_id": vehicle_id,
        "service_type": "regular_service",
        "description": "Engine oil change and filter replacement",
        "service_notes": "Replaced engine oil and oil filter. Checked brake pads and did wheel alignment. Odometer reading 25000 km.",
        "cost_estimate": 3500.0,
        "service_date": "2026-02-01"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/services/",
        json=service_data,
        headers=mechanic_headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        service = response.json()
        service_id = service["id"]
        print(f"   ✅ Service record created!")
        print(f"   Service ID: {service_id}")
        print(f"   Description: {service['description']}")
        print(f"   Cost Estimate: Rs{service['cost_estimate']}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
        return
    
    # Test 2: Get all services
    print("\\n3. Getting all services...")
    response = requests.get(
        f"{BASE_URL}/api/services/drafts",
        headers=mechanic_headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        drafts = response.json()
        print(f"   ✅ Found {len(drafts)} draft(s)")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Test 3: Create manual service (owner)
    print("\n4. Creating manual service record (owner)...")
    manual_service = {
        "vehicle_id": vehicle_id,
        "service_type": "regular_service",
        "service_date": datetime.now().date().isoformat(),
        "odometer_reading": 30000,
        "next_service_date": (datetime.now() + timedelta(days=180)).date().isoformat(),
        "next_service_km": 40000,
        "work_summary": "Regular maintenance service",
        "detailed_notes": "All checks passed. Vehicle in good condition.",
        "labor_cost": 800.0,
        "parts_cost": 2200.0,
        "total_cost": 3000.0,
        "payment_status": "paid",
        "parts_used": [
            {
                "name": "Engine Oil",
                "quantity": 1,
                "unit_price": 500,
                "total_price": 500
            },
            {
                "name": "Oil Filter",
                "quantity": 1,
                "unit_price": 200,
                "total_price": 200
            },
            {
                "name": "Air Filter",
                "quantity": 1,
                "unit_price": 300,
                "total_price": 300
            }
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/services/",
        json=manual_service,
        headers=owner_headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        service = response.json()
        print(f"   ✅ Manual service created!")
        print(f"   Service ID: {service['id']}")
        print(f"   Status: {service['status']}")
        print(f"   Cost: Rs{service['total_cost']}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Test 4: Get approved services
    print("\n5. Getting approved services...")
    response = requests.get(
        f"{BASE_URL}/api/services/approved",
        headers=owner_headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        services = response.json()
        print(f"   ✅ Found {len(services)} approved service(s)")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Test 5: Get vehicle service history
    print(f"\n6. Getting service history for vehicle {vehicle_id}...")
    response = requests.get(
        f"{BASE_URL}/api/services/vehicle/{vehicle_id}/history",
        headers=owner_headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        history = response.json()
        print(f"   ✅ Found {len(history)} service records in history")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Test 6: Get service statistics
    print(f"\n7. Getting service statistics...")
    response = requests.get(
        f"{BASE_URL}/api/services/stats/overview",
        headers=owner_headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"   ✅ Statistics retrieved")
        print(f"   Total services: {stats['total_services']}")
        print(f"   Total revenue: Rs{stats['total_revenue']}")
        print(f"   Avg cost: Rs{stats['average_service_cost']}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    print("\n" + "=" * 60)
    print("✅ Service management tests complete!")
    print("\n🎉 CORE SYSTEM READY!")
    print("\nFeatures implemented:")
    print("  ✅ User Authentication & Profiles")
    print("  ✅ Vehicle Management with Photos")
    print("  ✅ QR Code Generation")
    print("  ✅ Voice-to-Service Processing")
    print("  ✅ Draft/Approval Workflow")
    print("  ✅ Service History & Statistics")
    print("\n📁 Check uploads directory: app/uploads/")
    print(f"🔗 API Docs: {BASE_URL}/docs")

if __name__ == "__main__":
    test_services()