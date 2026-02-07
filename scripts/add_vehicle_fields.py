#!/usr/bin/env python3
"""
Database Migration: Add Electric and Fuel Vehicle Specific Fields
Adds new columns to vehicle table for electric and fuel vehicle specifications
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings

def run_migration():
    """Add electric and fuel vehicle specific fields to vehicles table"""
    
    engine = create_engine(settings.database_url)
    
    try:
        with engine.connect() as connection:
            # Begin transaction
            trans = connection.begin()
            
            try:
                print("Adding electric vehicle specific fields...")
                
                # Electric Vehicle fields
                connection.execute(text("""
                    ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS battery_capacity_kwh FLOAT
                """))
                
                connection.execute(text("""
                    ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS electric_range_km INTEGER
                """))
                
                connection.execute(text("""
                    ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS charging_port_type VARCHAR(20)
                """))
                
                connection.execute(text("""
                    ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS fast_charging_supported BOOLEAN
                """))
                
                connection.execute(text("""
                    ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS motor_power_kw FLOAT
                """))
                
                print("Adding fuel vehicle specific fields...")
                
                # Fuel Vehicle fields
                connection.execute(text("""
                    ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS engine_displacement_cc INTEGER
                """))
                
                connection.execute(text("""
                    ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS fuel_tank_capacity_l FLOAT
                """))
                
                connection.execute(text("""
                    ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS mileage_kmpl FLOAT
                """))
                
                connection.execute(text("""
                    ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS emission_standard VARCHAR(10)
                """))
                
                print("Adding constraints and indexes...")
                
                # Add constraints - PostgreSQL doesn't support IF NOT EXISTS for constraints
                # So we'll use a try-catch approach for each constraint
                constraints = [
                    ("chk_battery_capacity", "CHECK (battery_capacity_kwh IS NULL OR battery_capacity_kwh > 0)"),
                    ("chk_electric_range", "CHECK (electric_range_km IS NULL OR electric_range_km > 0)"),
                    ("chk_motor_power", "CHECK (motor_power_kw IS NULL OR motor_power_kw > 0)"),
                    ("chk_engine_displacement", "CHECK (engine_displacement_cc IS NULL OR engine_displacement_cc > 0)"),
                    ("chk_fuel_capacity", "CHECK (fuel_tank_capacity_l IS NULL OR fuel_tank_capacity_l > 0)"),
                    ("chk_mileage", "CHECK (mileage_kmpl IS NULL OR mileage_kmpl > 0)")
                ]
                
                for constraint_name, constraint_def in constraints:
                    try:
                        connection.execute(text(f"""
                            ALTER TABLE vehicle ADD CONSTRAINT {constraint_name} {constraint_def}
                        """))
                        print(f"✅ Added constraint: {constraint_name}")
                    except Exception as e:
                        if "already exists" in str(e) or "duplicate key" in str(e):
                            print(f"ℹ️  Constraint {constraint_name} already exists, skipping")
                        else:
                            print(f"⚠️  Warning adding constraint {constraint_name}: {e}")
                            # Don't fail the migration for constraint issues
                
                # Add some sample data updates for existing vehicles
                print("Checking existing vehicles...")
                
                # First, let's see what fuel types exist in the database
                result = connection.execute(text("SELECT DISTINCT fuel_type FROM vehicle LIMIT 5"))
                existing_fuel_types = [row[0] for row in result]
                print(f"Existing fuel types in DB: {existing_fuel_types}")
                
                # Skip sample data for now - just complete the column additions
                print("✅ Columns added successfully. Sample data update skipped for safety.")
                
                # Commit transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                print("✅ Added electric vehicle fields: battery_capacity_kwh, electric_range_km, charging_port_type, fast_charging_supported, motor_power_kw")
                print("✅ Added fuel vehicle fields: engine_displacement_cc, fuel_tank_capacity_l, mileage_kmpl, emission_standard")
                print("ℹ️  Note: Sample data not added - please update vehicles manually or run a separate data update script")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during migration: {e}")
                raise
                
    except SQLAlchemyError as e:
        print(f"❌ Database connection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Starting vehicle fields migration...")
    run_migration()