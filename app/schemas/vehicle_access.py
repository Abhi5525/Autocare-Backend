# app/schemas/vehicle_access.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.vehicle_access import AccessStatus

class VehicleAccessRequestCreate(BaseModel):
    """Schema for creating a vehicle access request"""
    vehicle_id: int
    message: Optional[str] = None

class VehicleAccessRequestUpdate(BaseModel):
    """Schema for updating access request status"""
    status: AccessStatus
    
class VehicleAccessRequestResponse(BaseModel):
    """Schema for access request response"""
    id: int
    mechanic_id: int
    vehicle_id: int
    owner_id: int
    status: AccessStatus
    message: Optional[str]
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    
    # Additional info for frontend
    mechanic_name: Optional[str] = None
    mechanic_phone: Optional[str] = None
    workshop_name: Optional[str] = None  # Workshop/Service center name
    vehicle_registration: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    
    class Config:
        from_attributes = True

class AccessibleVehicleResponse(BaseModel):
    """Schema for vehicles accessible by mechanic"""
    id: int
    registration_number: str
    make: str
    model: str
    year: int
    fuel_type: str
    owner_id: int
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    qr_code_url: Optional[str] = None
    primary_photo_url: Optional[str] = None
    access_granted_at: datetime
    
    class Config:
        from_attributes = True
