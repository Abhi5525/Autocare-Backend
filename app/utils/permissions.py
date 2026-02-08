# app/utils/permissions.py
"""
Permission checking utilities for role-based access control
"""
from app.models.user import User
from app.models.vehicle import Vehicle
from sqlmodel import Session
from .exceptions import raise_forbidden, raise_bad_request
from .db_helpers import get_or_404


def require_admin(user: User, message: str = "Only administrators can perform this action"):
    """
    Ensure user is an admin
    
    Args:
        user: Current user
        message: Custom error message
        
    Raises:
        HTTPException: 403 if not admin
    """
    if user.role != "admin":
        raise_forbidden(message)


def require_owner(user: User, message: str = "Only vehicle owners can perform this action"):
    """
    Ensure user is a vehicle owner
    
    Args:
        user: Current user
        message: Custom error message
        
    Raises:
        HTTPException: 403 if not owner
    """
    if user.role != "owner":
        raise_forbidden(message)


def require_mechanic(user: User, message: str = "Only mechanics can perform this action"):
    """
    Ensure user is a mechanic
    
    Args:
        user: Current user
        message: Custom error message
        
    Raises:
        HTTPException: 403 if not mechanic
    """
    if user.role != "mechanic":
        raise_forbidden(message)


def require_mechanic_approved(user: User):
    """
    Ensure mechanic account is approved
    
    Args:
        user: Current user
        
    Raises:
        HTTPException: 400 if mechanic not approved
    """
    if user.role == "mechanic" and not user.is_approved:
        raise_bad_request("Your mechanic account is pending approval")


def check_vehicle_ownership(user: User, vehicle: Vehicle):
    """
    Check if user owns the vehicle or is admin
    
    Args:
        user: Current user
        vehicle: Vehicle to check
        
    Raises:
        HTTPException: 403 if user doesn't own vehicle and is not admin
    """
    if vehicle.owner_id != user.id and user.role != "admin":
        raise_forbidden("You don't have permission to access this vehicle")


def require_vehicle_access(
    db: Session,
    user: User,
    vehicle_id: int,
    allow_mechanic: bool = False
) -> Vehicle:
    """
    Get vehicle and ensure user has access
    
    Args:
        db: Database session
        user: Current user
        vehicle_id: Vehicle ID
        allow_mechanic: Whether to allow mechanic access
        
    Returns:
        Vehicle instance
        
    Raises:
        HTTPException: 403 if user doesn't have access
        HTTPException: 404 if vehicle not found
    """
    vehicle = get_or_404(db, Vehicle, vehicle_id, "Vehicle")
    
    # Admin has access to all vehicles
    if user.role == "admin":
        return vehicle
    
    # Owner has access to their vehicles
    if vehicle.owner_id == user.id:
        return vehicle
    
    # Mechanic access check (if allowed)
    if allow_mechanic and user.role == "mechanic":
        # Check if mechanic has active access request
        from app.models.vehicle_access import VehicleAccessRequest, AccessStatus
        from sqlmodel import select, and_
        
        access_check = db.exec(
            select(VehicleAccessRequest).where(
                and_(
                    VehicleAccessRequest.vehicle_id == vehicle_id,
                    VehicleAccessRequest.mechanic_id == user.id,
                    VehicleAccessRequest.status == AccessStatus.APPROVED
                )
            )
        ).first()
        
        if access_check:
            return vehicle
    
    raise_forbidden("You don't have permission to access this vehicle")


def can_edit_service(user: User, service_mechanic_id: int, service_status: str) -> bool:
    """
    Check if user can edit a service record
    
    Args:
        user: Current user
        service_mechanic_id: ID of mechanic who created service
        service_status: Current service status
        
    Returns:
        True if user can edit, False otherwise
    """
    # Admin can edit any service
    if user.role == "admin":
        return True
    
    # Mechanic can edit their own draft services
    if user.role == "mechanic" and service_mechanic_id == user.id and service_status == "draft":
        return True
    
    return False


def require_service_edit_permission(
    user: User,
    service_mechanic_id: int,
    service_status: str
):
    """
    Ensure user can edit service record
    
    Args:
        user: Current user
        service_mechanic_id: ID of mechanic who created service
        service_status: Current service status
        
    Raises:
        HTTPException: 403 if user cannot edit
    """
    if not can_edit_service(user, service_mechanic_id, service_status):
        raise_forbidden("You don't have permission to edit this service record")
