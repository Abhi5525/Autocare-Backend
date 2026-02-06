# Fix existing vehicles - update primary_photo_url from VehiclePhoto records
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import Session, select, create_engine
from app.core.config import settings

# Create engine directly
engine = create_engine(str(settings.database_url))

# Import models after engine is created
from app.models.vehicle import Vehicle
from app.models.vehicle_photo import VehiclePhoto

with Session(engine) as session:
    print("\n" + "="*60)
    print("FIXING VEHICLE PRIMARY PHOTO URLs")
    print("="*60)
    
    # Get all vehicles with null primary_photo_url
    vehicles = session.exec(
        select(Vehicle).where(Vehicle.primary_photo_url == None)
    ).all()
    
    fixed_count = 0
    
    for vehicle in vehicles:
        # Check if this vehicle has any photos in VehiclePhoto table
        primary_photo = session.exec(
            select(VehiclePhoto)
            .where(VehiclePhoto.vehicle_id == vehicle.id)
            .where(VehiclePhoto.is_primary == True)
        ).first()
        
        if not primary_photo:
            # If no primary photo, get the first photo
            primary_photo = session.exec(
                select(VehiclePhoto)
                .where(VehiclePhoto.vehicle_id == vehicle.id)
            ).first()
        
        if primary_photo:
            print(f"\nVehicle ID {vehicle.id} ({vehicle.registration_number})")
            print(f"  Setting primary_photo_url to: {primary_photo.photo_url}")
            vehicle.primary_photo_url = primary_photo.photo_url
            primary_photo.is_primary = True
            session.add(vehicle)
            session.add(primary_photo)
            fixed_count += 1
    
    session.commit()
    
    print(f"\n{'-'*60}")
    print(f"✅ Fixed {fixed_count} vehicle(s)")
    print("="*60 + "\n")
