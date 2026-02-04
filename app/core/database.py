# app/core/database.py
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text
from app.core.config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    echo=True,  # Shows SQL queries in console (good for debugging)
    future=True
)

def create_db_and_tables():
    """Create all database tables"""
    SQLModel.metadata.create_all(engine)

def drop_and_recreate_tables():
    """Drop all tables and recreate them (for development only)"""
    # Drop all tables
    SQLModel.metadata.drop_all(engine)
    
    # Drop all custom ENUM types (PostgreSQL specific)
    with engine.connect() as conn:
        # Drop ENUMs in reverse order to avoid dependency issues
        conn.execute(text("DROP TYPE IF EXISTS servicestatus CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS servicetype CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS paymentstatus CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS transmissiontype CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS fueltype CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS vehicletype CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS userrole CASCADE"))
        conn.commit()
    
    # Recreate all tables (which will recreate the ENUMs)
    SQLModel.metadata.create_all(engine)

def get_session():
    """Get database session (dependency)"""
    with Session(engine) as session:
        yield session