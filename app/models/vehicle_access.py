# app/models/vehicle_access.py
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
from enum import Enum

class AccessStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class VehicleAccessRequest(SQLModel, table=True):
    """Model for mechanic requesting access to customer vehicles"""
    __tablename__ = "vehicle_access_request"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    mechanic_id: int = Field(foreign_key="user.id", index=True)
    vehicle_id: int = Field(foreign_key="vehicle.id", index=True)
    owner_id: int = Field(foreign_key="user.id", index=True)  # Vehicle owner
    
    # Status
    status: AccessStatus = Field(default=AccessStatus.PENDING)
    
    # Additional info
    message: Optional[str] = Field(default=None, max_length=500)  # Optional message from mechanic
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = Field(default=None)
    
    # Relationships (will be set up with back_populates)
    # mechanic: "User" = Relationship(back_populates="access_requests_sent")
    # vehicle: "Vehicle" = Relationship(back_populates="access_requests")
    # owner: "User" = Relationship(back_populates="access_requests_received")
