# Fix vehicle photos using direct SQL
import psycopg2
from psycopg2 import sql

# Database connection
conn = psycopg2.connect(
    dbname="autocare_db",
    user="postgres",
    password="root123",
    host="localhost",
    port="5432"
)

try:
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("FIXING VEHICLE PRIMARY PHOTO URLs")
    print("="*60)
    
    # First check what tables exist
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND (tablename LIKE '%vehicle%' OR tablename LIKE '%photo%')
        ORDER BY tablename;
    """)
    tables = cursor.fetchall()
    print("\nAvailable tables:", [t[0] for t in tables])
    
    # Find vehicles with null primary_photo_url that have photos
    query = """
        UPDATE vehicle v
        SET primary_photo_url = vp.photo_url
        FROM vehiclephoto vp
        WHERE v.id = vp.vehicle_id
        AND v.primary_photo_url IS NULL
        AND vp.id = (
            SELECT id FROM vehiclephoto
            WHERE vehicle_id = v.id
            ORDER BY created_at ASC
            LIMIT 1
        )
        RETURNING v.id, v.registration_number, v.primary_photo_url;
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    for vehicle_id, registration, photo_url in results:
        print(f"\nVehicle ID {vehicle_id} ({registration})")
        print(f"  Set primary_photo_url to: {photo_url}")
    
    # Also mark photos as primary
    if results:
        update_photos_query = """
            UPDATE vehiclephoto
            SET is_primary = true
            WHERE id IN (
                SELECT vp.id
                FROM vehicle v
                JOIN vehiclephoto vp ON v.id = vp.vehicle_id
                WHERE v.primary_photo_url = vp.photo_url
            );
        """
        cursor.execute(update_photos_query)
    
    conn.commit()
    
    print(f"\n{'-'*60}")
    print(f"✅ Fixed {len(results)} vehicle(s)")
    print("="*60 + "\n")
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
