# Quick script to check vehicle photo URLs in database
from sqlmodel import Session, select
from app.core.database import engine
from app.models.vehicle import Vehicle
from app.models.vehicle_photo import VehiclePhoto

with Session(engine) as session:
    print("\n=== VEHICLES WITH PHOTOS ===")
    vehicles = session.exec(select(Vehicle)).all()
    
    for vehicle in vehicles:
        print(f"\nVehicle ID: {vehicle.id}")
        print(f"Registration: {vehicle.registration_number}")
        print(f"Make/Model: {vehicle.make} {vehicle.model}")
        print(f"Primary Photo URL: {vehicle.primary_photo_url}")
        
        # Check associated photos
        photos = session.exec(
            select(VehiclePhoto).where(VehiclePhoto.vehicle_id == vehicle.id)
        ).all()
        
        if photos:
            print(f"  Photo records: {len(photos)}")
            for photo in photos:
                print(f"    - {photo.photo_url} (Primary: {photo.is_primary})")
        else:
            print("  No photo records found")
    
    print("\n" + "="*50)
