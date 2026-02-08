#!/usr/bin/env python3
"""
Migration script to add workshop_name field to user table
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, text
from app.core.database import engine

def add_workshop_name_field():
    """Add workshop_name field to user table if it doesn't exist"""
    with Session(engine) as session:
        try:
            # Check if column exists
            result = session.exec(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user' AND column_name = 'workshop_name'
            """))
            
            if result.fetchone() is None:
                # Add the column
                print("Adding workshop_name field to user table...")
                session.exec(text("""
                    ALTER TABLE "user" 
                    ADD COLUMN workshop_name VARCHAR(255) DEFAULT NULL
                """))
                session.commit()
                print("✅ workshop_name field added successfully!")
            else:
                print("✅ workshop_name field already exists.")
                
        except Exception as e:
            print(f"❌ Error adding workshop_name field: {e}")
            session.rollback()

if __name__ == "__main__":
    print("Running migration to add workshop_name field...")
    add_workshop_name_field()
    print("Migration completed!")