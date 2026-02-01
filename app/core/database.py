# app/core/database.py
from sqlmodel import SQLModel, create_engine, Session
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
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

def get_session():
    """Get database session (dependency)"""
    with Session(engine) as session:
        yield session