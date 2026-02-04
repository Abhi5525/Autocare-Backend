# test_approval_workflow.py
import requests
import json

BASE_URL = "http://localhost:8000"

def create_admin_user():
    """Create or get admin user"""
    # First create admin user
    admin_data = {
        "email": "admin_test@example.com",
        "phone": "9876500000",
        "full_name": "Admin User",
        "password": "Admin@1234",
        "role": "admin"  # Important: set admin role
    }
    
    # Try register
    response = requests.post(f"{BASE_URL}/api/auth/register", json=admin_data)
    
    if response.status_code == 201:
        token = response.json()["access_token"]
        # Update role to admin (in real app, this would be separate endpoint)
        headers = {"Authorization": f"Bearer {token}"}
        # We'll just use the token for now
        return token
    else:
        # Try login
        login_form = {"username": "admin_test@example.com", "password": "Admin@1234"}
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data=login_form,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
    
    return None

def test_approval_workflow():
    print("👑 Testing Admin Approval Workflow")
    print("=" * 60)
    
    # Get admin token
    admin_token = create_admin_user()
    if not admin_token:
        print("❌ Failed to create/get admin user")
        return
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get or create mechanic token
    print("\n1. Getting/creating mechanic user...")
    
    # Try to create mechanic user first
    import random
    unique_suffix = random.randint(1000, 9999)
    mechanic_email = f"workflow_mechanic_{unique_suffix}@example.com"
    mechanic_phone = f"987700{unique_suffix:04d}"
    
    mechanic_data = {
        "email": mechanic_email,
        "phone": mechanic_phone,
        "full_name": "Workflow Test Mechanic",
        "password": "Test@1234",
        "role": "mechanic"
    }
    
    # Try register
    response = requests.post(f"{BASE_URL}/api/auth/register", json=mechanic_data)
    
    if response.status_code == 201:
        mechanic_token = response.json()["access_token"]
        print(f"   ✅ Created new mechanic: {mechanic_email}")
    else:
        # Fallback to existing mechanic (if any)
        login_form = {"username": "mechanic_test@example.com", "password": "Test@1234"}
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data=login_form,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            mechanic_token = response.json()["access_token"]
            mechanic_email = "mechanic_test@example.com"
            print(f"   ✅ Using existing mechanic: {mechanic_email}")
        else:
            print("❌ Failed to get/create mechanic token")
            return
    
    mechanic_headers = {"Authorization": f"Bearer {mechanic_token}"}
    
    # Step 1: Create a draft as mechanic
    print("\n2. Creating draft as mechanic...")
    
    # First get a vehicle (need to get/create owner for this)
    # Try to get existing owner first
    owner_login = {"username": "owner_test@example.com", "password": "Test@1234"}
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data=owner_login,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        owner_token = response.json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        print("   ✅ Using existing owner")
    else:
        # Create owner if doesn't exist
        owner_data = {
            "email": f"workflow_owner_{unique_suffix}@example.com",
            "phone": f"987701{unique_suffix:04d}",
            "full_name": "Workflow Test Owner",
            "password": "Test@1234",
            "role": "owner"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=owner_data)
        if response.status_code == 201:
            owner_token = response.json()["access_token"]
            owner_headers = {"Authorization": f"Bearer {owner_token}"}
            print("   ✅ Created new owner")
        else:
            print("❌ Failed to get/create owner")
            return
    
    # Get vehicles for the owner
    response = requests.get(f"{BASE_URL}/api/vehicles/my-vehicles", headers=owner_headers)
    if response.status_code != 200 or not response.json():
        print("   No vehicles found, creating one...")
        
        import random
        reg = f"APPROVE{random.randint(1000, 9999)}"
        vehicle_data = {
            "registration_number": reg,
            "make": "Test",
            "model": "Model",
            "year": 2023,
            "color": "Red",
            "vehicle_type": "car",
            "fuel_type": "petrol",
            "transmission": "manual"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/vehicles/",
            json=vehicle_data,
            headers=owner_headers
        )
        
        if response.status_code != 201:
            print(f"❌ Failed to create vehicle: {response.text[:200]}")
            return
        
        vehicle = response.json()
        vehicle_id = vehicle["id"]
        reg_number = vehicle["registration_number"]
    else:
        vehicle = response.json()[0]
        vehicle_id = vehicle["id"]
        reg_number = vehicle["registration_number"]
    
    print(f"   Using vehicle: {reg_number}")
    
    # Create voice draft
    voice_request = {
        "vehicle_registration": reg_number,
        "transcript": "Oil change and filter replacement. 2000 rupees at 15000 km."
    }
    
    response = requests.post(
        f"{BASE_URL}/api/services/voice-draft",
        json=voice_request,
        headers=mechanic_headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create draft: {response.text[:200]}")
        return
    
    draft = response.json()
    draft_id = draft["draft_id"]
    print(f"   ✅ Draft created: ID {draft_id}")
    
    # Step 2: Get draft as admin
    print("\n3. Getting draft as admin...")
    response = requests.get(f"{BASE_URL}/api/services/{draft_id}", headers=admin_headers)
    
    if response.status_code == 200:
        draft_details = response.json()
        print(f"   ✅ Draft retrieved")
        print(f"   Status: {draft_details['status']}")
        print(f"   Work: {draft_details.get('description', 'N/A')}")
        print(f"   Cost: Rs{draft_details.get('cost_estimate', 0)}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Step 3: Approve draft as admin
    print(f"\n4. Approving draft {draft_id} as admin...")
    response = requests.put(
        f"{BASE_URL}/api/services/{draft_id}/approve",
        headers=admin_headers
    )
    
    if response.status_code == 200:
        approved = response.json()
        print(f"   ✅ Draft approved!")
        print(f"   New Status: {approved['status']}")
        print(f"   Approved By: {approved.get('approved_by')}")
        print(f"   Approved At: {approved.get('approved_at')}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
        
        # Try alternative endpoint if above doesn't work
        print("   Trying alternative approval endpoint...")
        response = requests.post(
            f"{BASE_URL}/api/services/{draft_id}/approve",
            headers=admin_headers
        )
        
        if response.status_code == 200:
            print("   ✅ Approved via POST endpoint")
        else:
            print(f"   ❌ Still failed: {response.text[:200]}")
    
    # Step 4: Check approved services list
    print("\n5. Checking approved services list...")
    response = requests.get(f"{BASE_URL}/api/services/approved", headers=admin_headers)
    
    if response.status_code == 200:
        approved_services = response.json()
        print(f"   ✅ Found {len(approved_services)} approved service(s)")
        
        if approved_services:
            latest = approved_services[0]
            print(f"   Latest approved:")
            print(f"     ID: {latest['id']}")
            print(f"     Vehicle: {latest.get('vehicle_id')}")
            print(f"     Cost: Rs{latest.get('cost_estimate', 0)}")
            print(f"     Date: {latest.get('service_date')}")
    
    # Step 5: Test reject workflow
    print("\n6. Testing reject workflow...")
    
    # Create another draft
    voice_request = {
        "vehicle_registration": reg_number,
        "transcript": "Test draft for rejection. 1000 rupees."
    }
    
    response = requests.post(
        f"{BASE_URL}/api/services/voice-draft",
        json=voice_request,
        headers=mechanic_headers
    )
    
    if response.status_code == 200:
        reject_draft = response.json()
        reject_id = reject_draft["draft_id"]
        print(f"   Created draft for rejection: ID {reject_id}")
        
        # Reject it
        reject_data = {"reason": "Incomplete information. Please add more details."}
        
        # Try POST first
        response = requests.post(
            f"{BASE_URL}/api/services/{reject_id}/reject",
            json=reject_data,
            headers=admin_headers
        )
        
        if response.status_code == 200:
            print(f"   ✅ Draft rejected!")
            print(f"   Reason: {reject_data['reason']}")
        else:
            # Try PUT
            response = requests.put(
                f"{BASE_URL}/api/services/{reject_id}/reject",
                json=reject_data,
                headers=admin_headers
            )
            if response.status_code == 200:
                print(f"   ✅ Draft rejected via PUT!")
            else:
                print(f"   ❌ Reject failed: {response.text[:200]}")
    
    print("\n" + "=" * 60)
    print("✅ Approval Workflow Test Complete!")
    print("\n🎯 Next Steps:")
    print("   1. Test the improved voice parser")
    print("   2. Build React frontend")
    print("   3. Add email/SMS notifications")
    print("   4. Implement invoice generation")

if __name__ == "__main__":
    test_approval_workflow()