from sqlmodel import Session, select
from app.core.database import engine
from app.models.vehicle import Vehicle

with Session(engine) as session:
    vehicles = session.exec(select(Vehicle)).all()
    
    print("\n" + "="*60)
    print("VEHICLE PHOTO URLs IN DATABASE")
    print("="*60)
    
    for v in vehicles:
        print(f"\nVehicle ID: {v.id}")
        print(f"Registration: {v.registration_number}")
        print(f"Make/Model: {v.make} {v.model}")
        print(f"Primary Photo URL: {v.primary_photo_url}")
        print(f"Full URL would be: http://localhost:8000{v.primary_photo_url if v.primary_photo_url else 'NO PHOTO'}")
    
    print("\n" + "="*60)
