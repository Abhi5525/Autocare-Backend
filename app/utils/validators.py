# app/utils/validators.py
"""
Validation utilities for common data validation patterns
"""
from sqlmodel import Session, select, or_, and_
from typing import Optional
from .exceptions import raise_bad_request


def validate_password_strength(password: str):
    """
    Validate password meets minimum requirements
    
    Args:
        password: Password to validate
        
    Raises:
        HTTPException: 400 if password doesn't meet requirements
    """
    if len(password) < 8:
        raise_bad_request("Password must be at least 8 characters long")


def validate_unique_user_credentials(
    db: Session,
    email: str,
    phone: str,
    user_id: Optional[int] = None
):
    """
    Validate user email and phone are unique
    
    Args:
        db: Database session
        email: Email to check
        phone: Phone to check
        user_id: Optional user ID to exclude from check (for updates)
        
    Raises:
        HTTPException: 400 if email or phone already exists
    """
    from app.models.user import User
    
    query = select(User).where(
        or_(User.email == email, User.phone == phone)
    )
    
    if user_id:
        query = query.where(User.id != user_id)
    
    existing_user = db.exec(query).first()
    
    if existing_user:
        if existing_user.email == email:
            raise_bad_request("Email already registered")
        if existing_user.phone == phone:
            raise_bad_request("Phone number already registered")


def validate_mechanic_credentials(
    db: Session,
    citizen_number: Optional[str],
    garage_registration: Optional[str],
    pan_number: Optional[str],
    user_id: Optional[int] = None
):
    """
    Validate mechanic credentials are unique
    
    Args:
        db: Database session
        citizen_number: Citizen number to check
        garage_registration: Garage registration to check
        pan_number: PAN number to check
        user_id: Optional user ID to exclude from check (for updates)
        
    Raises:
        HTTPException: 400 if any credential already exists
    """
    from app.models.user import User
    
    conditions = []
    if citizen_number:
        conditions.append(User.citizen_number == citizen_number)
    if garage_registration:
        conditions.append(User.garage_registration == garage_registration)
    if pan_number:
        conditions.append(User.pan_number == pan_number)
    
    if not conditions:
        return
    
    query = select(User).where(or_(*conditions))
    
    if user_id:
        query = query.where(User.id != user_id)
    
    existing = db.exec(query).first()
    
    if existing:
        if citizen_number and existing.citizen_number == citizen_number:
            raise_bad_request("Citizen number already registered")
        if garage_registration and existing.garage_registration == garage_registration:
            raise_bad_request("Garage registration already registered")
        if pan_number and existing.pan_number == pan_number:
            raise_bad_request("PAN number already registered")


def validate_unique_vehicle_registration(
    db: Session,
    registration_number: str,
    vehicle_id: Optional[int] = None
):
    """
    Validate vehicle registration number is unique
    
    Args:
        db: Database session
        registration_number: Registration number to check
        vehicle_id: Optional vehicle ID to exclude from check (for updates)
        
    Raises:
        HTTPException: 400 if registration already exists
    """
    from app.models.vehicle import Vehicle
    
    query = select(Vehicle).where(Vehicle.registration_number == registration_number)
    
    if vehicle_id:
        query = query.where(Vehicle.id != vehicle_id)
    
    existing = db.exec(query).first()
    
    if existing:
        raise_bad_request("Vehicle with this registration number already exists")


def validate_service_status_transition(
    current_status: str,
    new_status: str,
    allowed_transitions: dict
):
    """
    Validate service status transition is allowed
    
    Args:
        current_status: Current service status
        new_status: Desired new status
        allowed_transitions: Dict of allowed transitions
        
    Raises:
        HTTPException: 400 if transition not allowed
    """
    if new_status not in allowed_transitions.get(current_status, []):
        raise_bad_request(f"Cannot transition from {current_status} to {new_status}")
