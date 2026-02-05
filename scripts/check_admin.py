# check_admin.py - Check if superadmin account exists
"""
Check for existing superadmin account
"""

from app.core.database import engine
from app.models.user import User
from app.models.service import ServiceRecord
from app.models.vehicle import Vehicle
from sqlmodel import Session, select

def check_admin():
    with Session(engine) as session:
        # Check for admin user
        admin = session.exec(
            select(User).where(User.role == "admin")
        ).first()
        
        if admin:
            print("✅ Superadmin account found!")
            print(f"\n{'='*50}")
            print("SUPERADMIN CREDENTIALS")
            print(f"{'='*50}")
            print(f"Email: {admin.email}")
            print(f"Phone: {admin.phone}")
            print(f"Name: {admin.full_name}")
            print(f"Role: {admin.role}")
            print(f"User ID: {admin.id}")
            print(f"Active: {admin.is_active}")
            print(f"Approved: {admin.is_approved}")
            print(f"Created: {admin.created_at}")
            print(f"{'='*50}")
            print("\n⚠️  Default Password: Admin@123")
            print("(Change after first login if you haven't already)")
            print("\nLogin URL: http://localhost:3000/login\n")
        else:
            print("❌ No admin account found in database")
            print("Run: python create_superadmin.py")

if __name__ == "__main__":
    try:
        check_admin()
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
