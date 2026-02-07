# add_password_reset_fields.py - Database migration to add password reset functionality
"""
Execute SQL migration to add password reset fields to user table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from app.core.config import settings

def run_migration():
    """Add reset_token_hash and reset_token_expires_at columns to user table"""
    
    # Get database URL from settings
    db_url = settings.database_url
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Add reset_token_hash column
        print("Adding reset_token_hash column...")
        cursor.execute("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS reset_token_hash VARCHAR;
        """)
        
        # Add reset_token_expires_at column  
        print("Adding reset_token_expires_at column...")
        cursor.execute("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP;
        """)
        
        # Commit changes
        conn.commit()
        
        # Verify
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND column_name IN ('reset_token_hash', 'reset_token_expires_at');
        """)
        
        results = cursor.fetchall()
        print("\n✅ Password reset migration completed successfully!")
        print("\nAdded columns:")
        for row in results:
            print(f"  - {row[0]}: {row[1]}")
            
        print("\n🔐 Password reset functionality is now available!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    print("🚀 Starting password reset field migration...")
    run_migration()
    print("✅ Migration complete!")