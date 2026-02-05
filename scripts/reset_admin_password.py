"""
Reset admin password
"""
import sys
from sqlalchemy import create_engine, text
from argon2 import PasswordHasher
from argon2.exceptions import HashingError

# Database URL
DATABASE_URL = "postgresql://postgres:root123@localhost/autocare_db"

def reset_admin_password():
    print("Resetting admin password...")
    
    # Create password hasher
    ph = PasswordHasher()
    
    # Hash the new password
    new_password = "Admin@123"
    password_hash = ph.hash(new_password)
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if admin exists
        result = conn.execute(
            text("SELECT id, email, phone, full_name FROM \"user\" WHERE email = :email"),
            {"email": "admin@test.com"}
        )
        admin = result.fetchone()
        
        if not admin:
            print("❌ Admin account not found!")
            return
        
        # Update password
        conn.execute(
            text("UPDATE \"user\" SET password_hash = :password_hash WHERE email = :email"),
            {"password_hash": password_hash, "email": "admin@test.com"}
        )
        conn.commit()
        
        print("\n" + "="*50)
        print("✅ Admin password reset successfully!")
        print("="*50)
        print(f"Email: {admin[1]}")
        print(f"Password: {new_password}")
        print(f"Phone: {admin[2]}")
        print(f"Name: {admin[3]}")
        print("="*50)
        print("\nYou can now login with these credentials.")

if __name__ == "__main__":
    try:
        reset_admin_password()
    except Exception as e:
        print(f"\n❌ Error resetting password: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
