# update_rejected_to_pending.py - Update all rejected mechanics to pending status for testing
"""
Update rejected mechanics to pending status so they appear in admin dashboard
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from app.core.config import settings

def update_rejected_to_pending():
    """Update all rejected mechanics (is_active=false) to pending (is_active=true, is_approved=false)"""
    
    # Get database URL from settings
    db_url = settings.database_url
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check current rejected mechanics
        print("Checking current rejected mechanics...")
        cursor.execute("""
            SELECT id, full_name, email, is_active, is_approved 
            FROM "user" 
            WHERE role = 'mechanic' AND is_active = false;
        """)
        
        rejected_mechanics = cursor.fetchall()
        print(f"Found {len(rejected_mechanics)} rejected mechanics.")
        
        if rejected_mechanics:
            print("Current rejected mechanics:")
            for mech in rejected_mechanics:
                print(f"  - ID {mech[0]}: {mech[1]} ({mech[2]}) - Active: {mech[3]}, Approved: {mech[4]}")
        
        # Update rejected mechanics to pending status
        print("\nUpdating rejected mechanics to pending status...")
        cursor.execute("""
            UPDATE "user" 
            SET is_active = true, is_approved = false
            WHERE role = 'mechanic' AND is_active = false;
        """)
        
        updated_count = cursor.rowcount
        
        # Commit changes
        conn.commit()
        
        # Verify update
        cursor.execute("""
            SELECT id, full_name, email, is_active, is_approved 
            FROM "user" 
            WHERE role = 'mechanic' AND is_approved = false;
        """)
        
        pending_mechanics = cursor.fetchall()
        
        print(f"\n✅ Updated {updated_count} mechanics to pending status!")
        print(f"Now showing {len(pending_mechanics)} pending mechanics in admin dashboard:")
        
        for mech in pending_mechanics:
            print(f"  - ID {mech[0]}: {mech[1]} ({mech[2]}) - Active: {mech[3]}, Approved: {mech[4]}")
            
        print("\n🎯 All rejected mechanics are now pending and will appear in the admin dashboard!")
        
    except Exception as e:
        print(f"\n❌ Update failed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    print("🚀 Updating rejected mechanics to pending status for testing...")
    update_rejected_to_pending()
    print("✅ Update complete!")