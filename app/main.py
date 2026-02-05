# app/main.py - Add services router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime
from app.core.database import create_db_and_tables, drop_and_recreate_tables
from app.core.config import settings
from app.routers import auth, vehicles, services, vehicle_access  # Add vehicle_access

# Create FastAPI app
app = FastAPI(
    title="AutoCare Connect API",
    description="Intelligent Vehicle Service Management System",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    # allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

# Create tables on startup
@app.on_event("startup")
def on_startup():
    # Create tables if they don't exist (but don't drop existing data)
    create_db_and_tables()
    print("✅ Database tables ready")
    print("🚀 AutoCare Connect API Ready!")
    print(f"📡 API: http://localhost:8000")
    print(f"📚 Docs: http://localhost:8000/docs")
    print(f"💡 To reseed database: python seed_test_data.py")

# Include routers
app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(services.router)  # Add this line
app.include_router(vehicle_access.router)  # Add vehicle access router

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "AutoCare Connect API",
        "version": "2.0.0",
        "features": [
            "User Authentication & Profiles",
            "Vehicle Management with Photos",
            "QR Code Generation & Scanning",
            "Voice-to-Service Processing",
            "Draft/Approval Workflow",
            "Service History Tracking"
        ],
        "endpoints": {
            "auth": "/api/auth",
            "vehicles": "/api/vehicles",
            "services": "/api/services"
        },
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "autocare-api", "timestamp": datetime.now().isoformat()}