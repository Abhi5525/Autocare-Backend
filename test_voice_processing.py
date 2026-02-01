# test_voice_processing.py
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def get_auth_token(email="voice_test@example.com", role="mechanic"):
    """Get authentication token for testing"""
    # Use unique emails to avoid role conflicts
    import random
    unique_suffix = random.randint(1000, 9999)
    
    if role == "mechanic":
        email = f"voice_mechanic_{unique_suffix}@example.com"
        phone = f"987655{unique_suffix:04d}"
        user_data = {
            "email": email,
            "phone": phone,
            "full_name": "Voice Test Mechanic",
            "password": "Test@1234",
            "role": "mechanic"  # Important: set role explicitly
        }
    else:
        email = f"voice_owner_{unique_suffix}@example.com"
        phone = f"987656{unique_suffix:04d}"
        user_data = {
            "email": email,
            "phone": phone,
            "full_name": "Voice Test Owner",
            "password": "Test@1234",
            "role": "owner"  # Important: set role explicitly
        }
    
    # Try register
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
        if response.status_code == 201:
            return response.json()["access_token"]
        else:
            print(f"Registration failed for {role}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Registration error for {role}: {e}")
    
    # Try login with the same credentials
    login_form = {"username": email, "password": "Test@1234"}
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data=login_form,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    
    return None

def test_voice_processing():
    print("🎤 Testing Voice Processing System")
    print("=" * 60)
    
    # Get tokens
    mechanic_token = get_auth_token("voice_mechanic@example.com", "mechanic")
    owner_token = get_auth_token("voice_owner@example.com", "owner")
    
    if not mechanic_token or not owner_token:
        print("❌ Failed to get authentication tokens")
        return
    
    mechanic_headers = {"Authorization": f"Bearer {mechanic_token}"}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Step 1: Create a vehicle as owner
    print("\n1. Creating test vehicle...")
    import random
    reg_number = f"VOICE{random.randint(1000, 9999)}"
    
    vehicle_data = {
        "registration_number": reg_number,
        "make": "Maruti Suzuki",
        "model": "Baleno",
        "year": 2022,
        "color": "Blue",
        "vehicle_type": "car",
        "fuel_type": "petrol",
        "transmission": "manual",
        "owner_id": 1
    }
    
    response = requests.post(
        f"{BASE_URL}/api/vehicles/",
        json=vehicle_data,
        headers=owner_headers
    )
    
    if response.status_code != 201:
        print(f"   ❌ Failed to create vehicle: {response.text[:200]}")
        # Try to get existing vehicle
        response = requests.get(f"{BASE_URL}/api/vehicles/my-vehicles", headers=owner_headers)
        if response.status_code == 200:
            vehicles = response.json()
            if vehicles:
                vehicle = vehicles[0]
                reg_number = vehicle["registration_number"]
                print(f"   Using existing vehicle: {reg_number}")
            else:
                return
        else:
            return
    else:
        vehicle = response.json()
        print(f"   ✅ Vehicle created: {vehicle['registration_number']}")
    
    # Step 2: Test different voice transcripts
    print("\n2. Testing Voice Processing with different transcripts...")
    
    test_transcripts = [
        {
            "name": "Simple Oil Change",
            "transcript": "Changed engine oil and oil filter for 1500 rupees. Odometer 25000 km."
        },
        {
            "name": "Brake Service",
            "transcript": "Replaced front brake pads and brake discs. Also changed brake fluid. Total cost 5000 rupees at 30000 km."
        },
        {
            "name": "Full Service",
            "transcript": "Full service done. Replaced engine oil, oil filter, air filter, and spark plugs. Checked brakes and did wheel alignment. Labor 1000, parts 3000, total 4000 rupees. Odometer reading 40000 km."
        },
        {
            "name": "Tire Replacement",
            "transcript": "Replaced all 4 tires with new ones. Cost 8000 rupees including wheel balancing and alignment. Vehicle at 35000 km."
        },
        {
            "name": "Battery Issue",
            "transcript": "Battery not holding charge. Replaced with new battery. Cost 3500 rupees. Odometer 28000 km. Emergency repair."
        }
    ]
    
    created_drafts = []
    
    for i, test in enumerate(test_transcripts, 1):
        print(f"\n   Test {i}: {test['name']}")
        print(f"   Transcript: {test['transcript'][:80]}...")
        
        voice_request = {
            "vehicle_registration": reg_number,
            "transcript": test['transcript'],
            "mechanic_id": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/services/voice-draft",
            json=voice_request,
            headers=mechanic_headers
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            draft_id = result["draft_id"]
            confidence = result["confidence_score"]
            parsed = result["parsed_data"]
            
            print(f"   ✅ Draft created: ID {draft_id}")
            print(f"   Confidence: {confidence:.2f}")
            print(f"   Service Type: {parsed.get('service_type', 'N/A')}")
            print(f"   Parts Found: {len(parsed.get('parts_replaced', []))} replaced, "
                  f"{len(parsed.get('parts_repaired', []))} repaired")
            print(f"   Estimated Cost: ₹{parsed.get('total_cost', 0)}")
            print(f"   Odometer: {parsed.get('odometer_reading', 'N/A')}")
            
            created_drafts.append({
                "id": draft_id,
                "name": test['name'],
                "confidence": confidence,
                "data": parsed
            })
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    
    # Step 3: List all drafts
    print("\n3. Listing all draft services...")
    response = requests.get(
        f"{BASE_URL}/api/services/drafts",
        headers=mechanic_headers
    )
    
    if response.status_code == 200:
        drafts = response.json()
        print(f"   ✅ Found {len(drafts)} draft service(s)")
        
        for draft in drafts[:5]:  # Show first 5
            print(f"   - ID {draft['id']}: {draft.get('description', 'No description')[:60]}...")
            print(f"     Status: {draft['status']}, Voice: {draft.get('voice_transcript') is not None}")
            print(f"     Cost: ₹{draft.get('cost_estimate', 0)}, "
                  f"Confidence: {draft.get('confidence_score', 0):.2f}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
    
    # Step 4: Get specific draft details
    if created_drafts:
        print(f"\n4. Getting details for draft {created_drafts[0]['id']}...")
        response = requests.get(
            f"{BASE_URL}/api/services/{created_drafts[0]['id']}",
            headers=mechanic_headers
        )
        
        if response.status_code == 200:
            draft_details = response.json()
            print(f"   ✅ Draft details retrieved")
            print(f"   Vehicle ID: {draft_details.get('vehicle_id')}")
            print(f"   Service Date: {draft_details.get('service_date')}")
            print(f"   Transcript: {draft_details.get('voice_transcript', 'N/A')[:100]}...")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    
    # Step 5: Test updating a draft
    if created_drafts:
        print(f"\n5. Updating draft {created_drafts[0]['id']}...")
        update_data = {
            "work_summary": "Updated: " + created_drafts[0]['data']['work_summary'],
            "labor_cost": 1000.0,
            "parts_cost": 2000.0,
            "total_cost": 3000.0
        }
        
        response = requests.put(
            f"{BASE_URL}/api/services/{created_drafts[0]['id']}",
            json=update_data,
            headers=mechanic_headers
        )
        
        if response.status_code == 200:
            updated = response.json()
            print(f"   ✅ Draft updated")
            print(f"   New summary: {updated.get('work_summary', 'N/A')[:80]}...")
            print(f"   New total cost: ₹{updated.get('total_cost', 0)}")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    
    # Step 6: Test voice parsing accuracy
    print("\n6. Testing Voice Parsing Accuracy...")
    
    test_cases = [
        {
            "input": "Changed oil filter and engine oil for 1200 rupees at 15000 km",
            "expected_parts": ["Engine Oil", "Oil Filter"],
            "expected_cost": 1200
        },
        {
            "input": "Replaced brake pads front and rear, total 3000 rupees",
            "expected_parts": ["Brake Pads"],
            "expected_cost": 3000
        },
        {
            "input": "Full service with air filter, oil filter, engine oil change. 2500 rupees",
            "expected_parts": ["Air Filter", "Oil Filter", "Engine Oil"],
            "expected_cost": 2500
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   Accuracy Test {i}:")
        print(f"   Input: {test_case['input']}")
        
        # We can test parsing directly using the service
        voice_request = {
            "vehicle_registration": reg_number,
            "transcript": test_case['input'],
            "mechanic_id": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/services/voice-draft",
            json=voice_request,
            headers=mechanic_headers
        )
        
        if response.status_code == 200:
            result = response.json()
            parsed = result["parsed_data"]
            found_parts = [p['name'] for p in parsed.get('parts_replaced', [])]
            
            # Check accuracy
            correct_parts = sum(1 for part in test_case['expected_parts'] 
                              if any(test_part in part for test_part in found_parts))
            parts_accuracy = correct_parts / len(test_case['expected_parts']) if test_case['expected_parts'] else 1
            
            cost_accuracy = 1 if abs(parsed.get('total_cost', 0) - test_case['expected_cost']) < 500 else 0
            
            print(f"   Found parts: {found_parts}")
            print(f"   Expected parts: {test_case['expected_parts']}")
            print(f"   Parts accuracy: {parts_accuracy:.0%}")
            print(f"   Found cost: ₹{parsed.get('total_cost', 0)}")
            print(f"   Expected cost: ₹{test_case['expected_cost']}")
            print(f"   Cost accuracy: {'✓' if cost_accuracy else '✗'}")
        else:
            print(f"   ❌ Parsing failed")
    
    # Step 7: Test the workflow (Create → List → View → Update)
    print("\n7. Testing Complete Workflow...")
    
    # Create one more draft
    workflow_transcript = "Wheel alignment and balancing done. Also replaced wiper blades. Total 1500 rupees at 32000 km."
    
    voice_request = {
        "vehicle_registration": reg_number,
        "transcript": workflow_transcript,
        "mechanic_id": 1
    }
    
    response = requests.post(
        f"{BASE_URL}/api/services/voice-draft",
        json=voice_request,
        headers=mechanic_headers
    )
    
    if response.status_code == 200:
        workflow_draft = response.json()
        print(f"   ✅ Workflow draft created: ID {workflow_draft['draft_id']}")
        
        # Get draft list again
        response = requests.get(f"{BASE_URL}/api/services/drafts", headers=mechanic_headers)
        if response.status_code == 200:
            final_drafts = response.json()
            print(f"   Total drafts in system: {len(final_drafts)}")
            
            # Show statistics
            voice_drafts = [d for d in final_drafts if d.get('is_voice_entry')]
            manual_drafts = [d for d in final_drafts if not d.get('is_voice_entry', False)]
            
            print(f"   Voice entries: {len(voice_drafts)}")
            print(f"   Manual entries: {len(manual_drafts)}")
            
            if voice_drafts:
                avg_confidence = sum(d.get('processing_confidence', 0) for d in voice_drafts) / len(voice_drafts)
                avg_cost = sum(d.get('total_cost', 0) for d in voice_drafts) / len(voice_drafts)
                print(f"   Avg confidence: {avg_confidence:.2f}")
                print(f"   Avg cost: ₹{avg_cost:.2f}")
    
    print("\n" + "=" * 60)
    print("✅ Voice Processing Tests Complete!")
    print("\n📊 Summary:")
    print(f"   Created {len(created_drafts)} voice drafts")
    print(f"   Tested {len(test_transcripts)} different transcripts")
    print(f"   Tested parsing accuracy with {len(test_cases)} cases")
    print("\n🚀 Next: Test approval workflow as admin!")
    print("   Use POST /api/services/{id}/approve to approve drafts")
    print("   Use POST /api/services/{id}/reject to reject drafts")

if __name__ == "__main__":
    test_voice_processing()