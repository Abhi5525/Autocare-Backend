# app/models/vehicle_photo.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime

from app.models.user import User
from app.models.vehicle import Vehicle

class VehiclePhotoBase(SQLModel):
    """Base vehicle photo model"""
    caption: Optional[str] = None
    is_primary: bool = False

class VehiclePhotoCreate(VehiclePhotoBase):
    """For creating a vehicle photo"""
    vehicle_id: int

class VehiclePhoto(VehiclePhotoBase, table=True):
    """Database model for vehicle photos"""
    id: Optional[int] = Field(default=None, primary_key=True)
    vehicle_id: int = Field(foreign_key="vehicle.id")
    photo_url: str  # Path or URL to the photo
    uploaded_by: int = Field(foreign_key="user.id")
    
    # Metadata
    file_size: int  # In bytes
    file_type: str  # e.g., 'image/jpeg'
    width: Optional[int] = None
    height: Optional[int] = None
    
    uploaded_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    vehicle: "Vehicle" = Relationship(back_populates="photos")
    uploader: "User" = Relationship()
    
    class Config:
        from_attributes = True