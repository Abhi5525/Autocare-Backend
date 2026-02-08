#!/usr/bin/env python3
"""
Migration script to add odometer_reading field to servicerecord table
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine

def migrate():
    """Add odometer_reading column to servicerecord table"""
    
    migration_sql = """
    -- Add odometer_reading column if it doesn't exist
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name='servicerecord' 
            AND column_name='odometer_reading'
        ) THEN
            ALTER TABLE servicerecord 
            ADD COLUMN odometer_reading INTEGER;
            
            RAISE NOTICE 'Column odometer_reading added successfully';
        ELSE
            RAISE NOTICE 'Column odometer_reading already exists';
        END IF;
    END $$;
    """
    
    try:
        with engine.connect() as conn:
            print("Running migration: Adding odometer_reading field to servicerecord table...")
            conn.execute(text(migration_sql))
            conn.commit()
            print("✓ Migration completed successfully!")
            
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
