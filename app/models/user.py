# app/models/user.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from pydantic import EmailStr, constr, field_validator
import re

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle
    from app.models.service import ServiceRecord

# ===== Base Schemas =====
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True)
    phone: str = Field(unique=True, index=True)
    full_name: str

    @field_validator("phone")
    def validate_phone(cls, v):
        if not re.match(r"^98\d{8}$", v):
            raise ValueError("Phone number must start with 98 and be 10 digits")
        return v

# ===== Pydantic Models for API =====
class UserCreate(UserBase):
    """For user registration"""
    password: str = Field(min_length=8, max_length=72)
    role: str = "owner"  # Default role
    
    # Address fields (for all users)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    municipality: Optional[str] = None
    ward_no: Optional[str] = None
    
    # Mechanic-specific fields (required only for mechanics)
    citizen_number: Optional[str] = None
    garage_registration: Optional[str] = None
    pan_number: Optional[str] = None
    garage_address: Optional[str] = None
    workshop_name: Optional[str] = None  # Optional workshop/service center name

class UserUpdate(SQLModel):
    """For updating user profile"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    profile_pic_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    municipality: Optional[str] = None
    ward_no: Optional[str] = None
    garage_address: Optional[str] = None
    workshop_name: Optional[str] = None

class UserLogin(SQLModel):
    """For login"""
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str

    @field_validator("email")
    def email_or_phone(cls, v, info):
        values = info.data
        if not v and not values.get("phone"):
            raise ValueError("Either email or phone must be provided")
        return v

class Token(SQLModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str

class TokenWithUser(SQLModel):
    """Token response with full user data"""
    access_token: str
    token_type: str = "bearer"
    user: "User"

# ===== DB Model =====
class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str
    is_verified: bool = False
    is_active: bool = True
    role: str = "owner"

    # Profile
    profile_pic_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    municipality: Optional[str] = None
    ward_no: Optional[str] = None

    # Mechanic-specific fields
    citizen_number: Optional[str] = Field(default=None, unique=True, index=True)  # National ID/Citizenship number
    garage_registration: Optional[str] = Field(default=None, unique=True, index=True)  # Garage registration number
    pan_number: Optional[str] = Field(default=None, unique=True, index=True)  # PAN number for tax
    mechanic_certificate_url: Optional[str] = None  # Photo/certificate upload
    garage_address: Optional[str] = None  # Garage location
    workshop_name: Optional[str] = None  # Service center/workshop name (optional)
    is_approved: bool = False  # Admin approval for mechanics
    approved_by: Optional[int] = None  # Admin who approved
    approved_at: Optional[datetime] = None  # When approved

    # Password reset fields
    reset_token_hash: Optional[str] = None  # Hashed reset token
    reset_token_expires_at: Optional[datetime] = None  # Token expiry

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    vehicles: List["Vehicle"] = Relationship(back_populates="owner")
    service_records: List["ServiceRecord"] = Relationship(
        back_populates="mechanic",
        sa_relationship_kwargs={"foreign_keys": "ServiceRecord.mechanic_id"}
    )
    approved_services: List["ServiceRecord"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "ServiceRecord.approver_id"}
    )
