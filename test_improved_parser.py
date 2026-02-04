# test_improved_parser.py
from app.services.voice_service import VoiceProcessingService

def test_improved_parser():
    print("🧪 Testing Improved Voice Parser")
    print("=" * 60)
    
    service = VoiceProcessingService()
    
    test_cases = [
        {
            "name": "Simple Oil Change",
            "transcript": "Changed engine oil and oil filter for 1500 rupees. Odometer 25000 km.",
            "expected_parts": ["Engine Oil", "Oil Filter"]
        },
        {
            "name": "Brake Service",
            "transcript": "Replaced front brake pads and brake discs. Also changed brake fluid. Total cost 5000 rupees at 30000 km.",
            "expected_parts": ["Brake Pads", "Brake Disc", "Brake Fluid"]
        },
        {
            "name": "Full Service",
            "transcript": "Full service done. Replaced engine oil, oil filter, air filter, and spark plugs. Checked brakes and did wheel alignment. Labor 1000, parts 3000, total 4000 rupees. Odometer reading 40000 km.",
            "expected_parts": ["Engine Oil", "Oil Filter", "Air Filter", "Spark Plug", "Wheel Alignment"]
        },
        {
            "name": "Tire Replacement",
            "transcript": "Replaced all 4 tires with new ones. Cost 8000 rupees including wheel balancing and alignment. Vehicle at 35000 km.",
            "expected_parts": ["Tire", "Wheel Balancing", "Wheel Alignment"]
        },
        {
            "name": "Multiple Services",
            "transcript": "Did oil change, replaced air filter, new wiper blades, and wheel alignment. Total bill 4500 rupees. Car at 28000 km.",
            "expected_parts": ["Engine Oil", "Air Filter", "Wiper Blades", "Wheel Alignment"]
        }
    ]
    
    for test in test_cases:
        print(f"\n📝 Test: {test['name']}")
        print(f"   Input: {test['transcript'][:80]}...")
        
        result = service.process_transcript(test['transcript'])
        
        print(f"   Confidence: {result['confidence_score']:.2f}")
        print(f"   Service Type: {result['service_type']}")
        print(f"   Total Cost: Rs{result['total_cost']}")
        print(f"   Odometer: {result['odometer_reading']}")
        
        found_parts = [p['name'] for p in result['parts_replaced']]
        print(f"   Found Parts: {found_parts}")
        print(f"   Expected Parts: {test['expected_parts']}")
        
        # Calculate accuracy with better matching
        correct = 0
        for expected_part in test['expected_parts']:
            for found_part in found_parts:
                # Check if expected part name matches found part (more precise)
                if expected_part.lower() in found_part.lower() or found_part.lower() in expected_part.lower():
                    correct += 1
                    break
        
        accuracy = correct / len(test['expected_parts']) if test['expected_parts'] else 1
        
        print(f"   Accuracy: {accuracy:.0%}")
        
        if accuracy >= 0.7:
            print("   ✅ Good!")
        elif accuracy >= 0.4:
            print("   ⚠️  Needs improvement")
        else:
            print("   ❌ Poor detection")
    
    print("\n" + "=" * 60)
    print("🧠 Testing Edge Cases:")
    
    edge_cases = [
        "Oil change done. 1200 rupees.",
        "Just checked the vehicle, everything okay.",
        "Emergency breakdown service. Battery replacement. 3500 rupees.",
        "Full service with all filters changed and AC gas filled.",
    ]
    
    for i, transcript in enumerate(edge_cases, 1):
        print(f"\n   Edge Case {i}: {transcript}")
        result = service.process_transcript(transcript)
        print(f"   Confidence: {result['confidence_score']:.2f}")
        print(f"   Parts Found: {len(result['parts_replaced'])}")
        print(f"   Cost: Rs{result['total_cost']}")

if __name__ == "__main__":
    test_improved_parser()