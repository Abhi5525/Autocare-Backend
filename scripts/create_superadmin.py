# create_superadmin.py
"""
Script to create a superadmin user for AutoCare Connect
Run this script once to create the initial admin account
Usage: python create_superadmin.py
"""

from app.core.database import engine
from app.models.user import User
from app.models.service import ServiceRecord  # Import to resolve relationships
from app.models.vehicle import Vehicle  # Import to resolve relationships
from app.core.security import get_password_hash
from sqlmodel import Session, select
from datetime import datetime

def create_superadmin():
    with Session(engine) as session:
        # Check if superadmin already exists
        existing_admin = session.exec(
            select(User).where(User.email == "admin@autocare.com")
        ).first()
        
        if existing_admin:
            print("❌ Superadmin already exists!")
            print(f"Email: {existing_admin.email}")
            print(f"Name: {existing_admin.full_name}")
            return
        
        # Create superadmin user
        superadmin = User(
            email="admin@autocare.com",
            phone="9800000000",
            full_name="Super Administrator",
            password_hash=get_password_hash("Admin@123"),
            role="admin",
            is_verified=True,
            is_active=True,
            is_approved=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        session.add(superadmin)
        session.commit()
        session.refresh(superadmin)
        
        print("✅ Superadmin created successfully!")
        print(f"\n{'='*50}")
        print("SUPERADMIN CREDENTIALS")
        print(f"{'='*50}")
        print(f"Email: admin@autocare.com")
        print(f"Phone: 9800000000")
        print(f"Password: Admin@123")
        print(f"Role: admin")
        print(f"User ID: {superadmin.id}")
        print(f"{'='*50}")
        print("\n⚠️  IMPORTANT: Change the password after first login!")
        print("You can login at: http://localhost:3000/login\n")

if __name__ == "__main__":
    try:
        print("Creating superadmin account...")
        create_superadmin()
    except Exception as e:
        print(f"❌ Error creating superadmin: {e}")
        raise
