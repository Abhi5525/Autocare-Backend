# run_migration.py - Run database migration to add municipality and ward_no fields
"""
Execute SQL migration to add missing columns
"""

import psycopg2
from app.core.config import settings

def run_migration():
    """Add municipality and ward_no columns to user table"""
    
    # Get database URL from settings
    db_url = settings.database_url
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Add municipality column
        print("Adding municipality column...")
        cursor.execute("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS municipality VARCHAR;
        """)
        
        # Add ward_no column  
        print("Adding ward_no column...")
        cursor.execute("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS ward_no VARCHAR;
        """)
        
        # Commit changes
        conn.commit()
        
        # Verify
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND column_name IN ('municipality', 'ward_no');
        """)
        
        results = cursor.fetchall()
        print("\n✅ Migration completed successfully!")
        print("\nAdded columns:")
        for row in results:
            print(f"  - {row[0]}: {row[1]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ You can now run: python create_superadmin.py")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()
