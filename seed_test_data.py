# seed_test_data.py - Test Data Seeder for AutoCare Connect
"""
This script resets the database and seeds it with test data.
Run this script to get fresh test data for development.

Usage:
    python seed_test_data.py
"""

from sqlmodel import Session, select
from datetime import datetime, date, timedelta
from app.core.database import engine, drop_and_recreate_tables
from app.core.security import get_password_hash
from app.models.user import User
from app.models.vehicle import Vehicle, VehicleType, FuelType, TransmissionType
from app.models.service import ServiceRecord, ServiceType, ServiceStatus, PaymentStatus, ServicePart
from app.services.qr_service import QRService
import random

def seed_data():
    """Seed the database with test data"""
    
    print("🔄 Dropping and recreating all tables...")
    drop_and_recreate_tables()
    print("✅ Tables recreated successfully!\n")
    
    with Session(engine) as session:
        print("👥 Creating test users...")
        
        # Test User 1: Vehicle Owner (Owner)
        owner1 = User(
            email="owner@test.com",
            phone="9812345678",
            full_name="Raj Kumar",
            password_hash=get_password_hash("password123"),
            role="owner",
            is_verified=True,
            is_active=True,
            address="123 MG Road, Bangalore",
            city="Bangalore",
            state="Karnataka",
            pincode="560001"
        )
        session.add(owner1)
        
        # Test User 2: Another Vehicle Owner
        owner2 = User(
            email="priya@test.com",
            phone="9823456789",
            full_name="Priya Sharma",
            password_hash=get_password_hash("password123"),
            role="owner",
            is_verified=True,
            is_active=True,
            address="456 Koramangala, Bangalore",
            city="Bangalore",
            state="Karnataka",
            pincode="560034"
        )
        session.add(owner2)
        
        # Test User 3: Mechanic
        mechanic1 = User(
            email="mechanic@test.com",
            phone="9834567890",
            full_name="Suresh Kumar",
            password_hash=get_password_hash("mechanic123"),
            role="mechanic",
            is_verified=True,
            is_active=True,
            address="Workshop Center, Indiranagar",
            city="Bangalore",
            state="Karnataka",
            pincode="560038"
        )
        session.add(mechanic1)
        
        # Test User 4: Another Mechanic
        mechanic2 = User(
            email="amit@test.com",
            phone="9845678901",
            full_name="Amit Patel",
            password_hash=get_password_hash("mechanic123"),
            role="mechanic",
            is_verified=True,
            is_active=True,
            address="AutoCare Workshop, Whitefield",
            city="Bangalore",
            state="Karnataka",
            pincode="560066"
        )
        session.add(mechanic2)
        
        # Test User 5: Admin
        admin = User(
            email="admin@test.com",
            phone="9856789012",
            full_name="Admin User",
            password_hash=get_password_hash("admin123"),
            role="admin",
            is_verified=True,
            is_active=True,
            address="AutoCare HQ, MG Road",
            city="Bangalore",
            state="Karnataka",
            pincode="560001"
        )
        session.add(admin)
        
        session.commit()
        session.refresh(owner1)
        session.refresh(owner2)
        session.refresh(mechanic1)
        session.refresh(mechanic2)
        session.refresh(admin)
        
        print(f"✅ Created 5 test users")
        print(f"   - Owner 1: {owner1.email} (ID: {owner1.id})")
        print(f"   - Owner 2: {owner2.email} (ID: {owner2.id})")
        print(f"   - Mechanic 1: {mechanic1.email} (ID: {mechanic1.id})")
        print(f"   - Mechanic 2: {mechanic2.email} (ID: {mechanic2.id})")
        print(f"   - Admin: {admin.email} (ID: {admin.id})\n")
        
        print("🚗 Creating test vehicles...")
        
        # Owner 1's Vehicles
        vehicle1 = Vehicle(
            registration_number="KA01AB1234",
            make="Maruti Suzuki",
            model="Swift",
            year=2020,
            color="Red",
            vehicle_type=VehicleType.CAR,
            fuel_type=FuelType.PETROL,
            transmission=TransmissionType.MANUAL,
            vin="MA3ERLF1S00123456",
            engine_number="G12B1234567",
            current_odometer=25000,
            owner_id=owner1.id,
            last_service_date=date.today() - timedelta(days=90),
            last_service_km=22000,
            next_service_date=date.today() + timedelta(days=90),
            next_service_km=30000
        )
        session.add(vehicle1)
        session.commit()
        session.refresh(vehicle1)
        vehicle1.qr_code_url = QRService.generate_vehicle_qr(vehicle1.id, vehicle1.registration_number)
        
        vehicle2 = Vehicle(
            registration_number="KA02CD5678",
            make="Honda",
            model="City",
            year=2021,
            color="White",
            vehicle_type=VehicleType.CAR,
            fuel_type=FuelType.PETROL,
            transmission=TransmissionType.AUTOMATIC,
            vin="HMACX1234567890",
            current_odometer=15000,
            owner_id=owner1.id,
            last_service_date=date.today() - timedelta(days=60),
            last_service_km=13000,
            next_service_date=date.today() + timedelta(days=120),
            next_service_km=20000
        )
        session.add(vehicle2)
        session.commit()
        session.refresh(vehicle2)
        vehicle2.qr_code_url = QRService.generate_vehicle_qr(vehicle2.id, vehicle2.registration_number)
        
        # Owner 2's Vehicles
        vehicle3 = Vehicle(
            registration_number="KA03EF9012",
            make="Hyundai",
            model="Creta",
            year=2022,
            color="Blue",
            vehicle_type=VehicleType.SUV,
            fuel_type=FuelType.DIESEL,
            transmission=TransmissionType.AUTOMATIC,
            current_odometer=8000,
            owner_id=owner2.id,
            next_service_date=date.today() + timedelta(days=30),
            next_service_km=10000
        )
        session.add(vehicle3)
        session.commit()
        session.refresh(vehicle3)
        vehicle3.qr_code_url = QRService.generate_vehicle_qr(vehicle3.id, vehicle3.registration_number)
        
        vehicle4 = Vehicle(
            registration_number="KA04GH3456",
            make="Hero",
            model="Splendor Plus",
            year=2019,
            color="Black",
            vehicle_type=VehicleType.BIKE,
            fuel_type=FuelType.PETROL,
            transmission=TransmissionType.MANUAL,
            current_odometer=32000,
            owner_id=owner2.id,
            last_service_date=date.today() - timedelta(days=120),
            last_service_km=30000,
            next_service_date=date.today() - timedelta(days=10),  # Overdue!
            next_service_km=35000
        )
        session.add(vehicle4)
        session.commit()
        session.refresh(vehicle4)
        vehicle4.qr_code_url = QRService.generate_vehicle_qr(vehicle4.id, vehicle4.registration_number)
        
        session.commit()
        
        print(f"✅ Created 4 test vehicles")
        print(f"   - {vehicle1.registration_number} - {vehicle1.make} {vehicle1.model} (Owner: {owner1.full_name})")
        print(f"   - {vehicle2.registration_number} - {vehicle2.make} {vehicle2.model} (Owner: {owner1.full_name})")
        print(f"   - {vehicle3.registration_number} - {vehicle3.make} {vehicle3.model} (Owner: {owner2.full_name})")
        print(f"   - {vehicle4.registration_number} - {vehicle4.make} {vehicle4.model} (Owner: {owner2.full_name})\n")
        
        print("🔧 Creating test service records...")
        
        # Service 1: Approved service for vehicle1
        service1 = ServiceRecord(
            vehicle_id=vehicle1.id,
            mechanic_id=mechanic1.id,
            approver_id=admin.id,
            service_type=ServiceType.REGULAR_SERVICE,
            description="Regular service - Oil change and filter replacement",
            service_notes="All systems checked. Vehicle in good condition.",
            cost_estimate=2500.0,
            final_cost=2500.0,
            payment_status=PaymentStatus.PAID,
            status=ServiceStatus.APPROVED,
            service_date=date.today() - timedelta(days=90),
            completion_date=date.today() - timedelta(days=90),
            approved_at=datetime.now() - timedelta(days=90)
        )
        session.add(service1)
        session.commit()
        session.refresh(service1)
        
        # Add parts for service1
        part1 = ServicePart(
            service_id=service1.id,
            part_name="Engine Oil (5W-30)",
            quantity=4,
            unit_price=450.0,
            total_price=1800.0,
            installed_by=mechanic1.id,
            warranty_months=6
        )
        part2 = ServicePart(
            service_id=service1.id,
            part_name="Oil Filter",
            quantity=1,
            unit_price=250.0,
            total_price=250.0,
            installed_by=mechanic1.id,
            warranty_months=6
        )
        part3 = ServicePart(
            service_id=service1.id,
            part_name="Air Filter",
            quantity=1,
            unit_price=450.0,
            total_price=450.0,
            installed_by=mechanic1.id,
            warranty_months=6
        )
        session.add_all([part1, part2, part3])
        
        # Service 2: Another approved service for vehicle1
        service2 = ServiceRecord(
            vehicle_id=vehicle1.id,
            mechanic_id=mechanic2.id,
            approver_id=admin.id,
            service_type=ServiceType.REPAIR,
            description="Brake pad replacement - Front",
            service_notes="Front brake pads worn out. Replaced both sides.",
            cost_estimate=3500.0,
            final_cost=3200.0,
            payment_status=PaymentStatus.PAID,
            status=ServiceStatus.APPROVED,
            service_date=date.today() - timedelta(days=180),
            completion_date=date.today() - timedelta(days=180),
            approved_at=datetime.now() - timedelta(days=180)
        )
        session.add(service2)
        
        # Service 3: Draft service (pending approval) for vehicle2
        service3 = ServiceRecord(
            vehicle_id=vehicle2.id,
            mechanic_id=mechanic1.id,
            service_type=ServiceType.INSPECTION,
            description="Pre-monsoon inspection",
            service_notes="Customer requested comprehensive check before monsoon season.",
            cost_estimate=1500.0,
            status=ServiceStatus.DRAFT,
            service_date=date.today(),
            voice_transcript="Pre-monsoon check requested. Check all electrical systems, wipers, tires, and brakes.",
            confidence_score=0.92
        )
        session.add(service3)
        
        # Service 4: Draft service for vehicle3
        service4 = ServiceRecord(
            vehicle_id=vehicle3.id,
            mechanic_id=mechanic2.id,
            service_type=ServiceType.REGULAR_SERVICE,
            description="First free service",
            service_notes="Complimentary first service. 10,000 km check.",
            cost_estimate=0.0,
            status=ServiceStatus.DRAFT,
            service_date=date.today(),
        )
        session.add(service4)
        
        # Service 5: Approved service for vehicle4
        service5 = ServiceRecord(
            vehicle_id=vehicle4.id,
            mechanic_id=mechanic1.id,
            approver_id=admin.id,
            service_type=ServiceType.REGULAR_SERVICE,
            description="Chain cleaning and lubrication",
            service_notes="Regular maintenance completed.",
            cost_estimate=800.0,
            final_cost=800.0,
            payment_status=PaymentStatus.PAID,
            status=ServiceStatus.APPROVED,
            service_date=date.today() - timedelta(days=120),
            completion_date=date.today() - timedelta(days=120),
            approved_at=datetime.now() - timedelta(days=120)
        )
        session.add(service5)
        
        session.commit()
        
        print(f"✅ Created 5 test service records")
        print(f"   - 3 Approved services")
        print(f"   - 2 Draft services (pending approval)\n")
        
        print("=" * 60)
        print("🎉 DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 60)
        print("\n📝 TEST CREDENTIALS:\n")
        
        print("👤 VEHICLE OWNER 1:")
        print(f"   Email: owner@test.com")
        print(f"   Password: password123")
        print(f"   Vehicles: 2 (Swift, City)")
        print(f"   Services: 3 (2 approved, 1 draft)\n")
        
        print("👤 VEHICLE OWNER 2:")
        print(f"   Email: priya@test.com")
        print(f"   Password: password123")
        print(f"   Vehicles: 2 (Creta, Splendor Plus)")
        print(f"   Services: 2 (1 approved, 1 draft)\n")
        
        print("🔧 MECHANIC 1:")
        print(f"   Email: mechanic@test.com")
        print(f"   Password: mechanic123")
        print(f"   Services Created: 3\n")
        
        print("🔧 MECHANIC 2:")
        print(f"   Email: amit@test.com")
        print(f"   Password: mechanic123")
        print(f"   Services Created: 2\n")
        
        print("👨‍💼 ADMIN:")
        print(f"   Email: admin@test.com")
        print(f"   Password: admin123")
        print(f"   Role: Full system access\n")
        
        print("=" * 60)
        print("🚀 NEXT STEPS:")
        print("=" * 60)
        print("1. Start the backend server:")
        print("   cd backend")
        print("   uvicorn app.main:app --reload\n")
        print("2. Start the frontend:")
        print("   cd autocare-frontend")
        print("   npm start\n")
        print("3. Open browser: http://localhost:3000")
        print("4. Login with any test credentials above\n")
        print("=" * 60)

if __name__ == "__main__":
    try:
        seed_data()
    except Exception as e:
        print(f"\n❌ Error seeding data: {str(e)}")
        import traceback
        traceback.print_exc()
