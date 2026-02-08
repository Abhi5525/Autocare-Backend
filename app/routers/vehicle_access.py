# app/routers/vehicle_access.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, and_, or_
from typing import List
from datetime import datetime

from app.core.database import get_session
from app.dependencies.deps import get_current_user
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_access import VehicleAccessRequest, AccessStatus
from app.schemas.vehicle_access import (
    VehicleAccessRequestCreate,
    VehicleAccessRequestUpdate,
    VehicleAccessRequestResponse,
    AccessibleVehicleResponse
)
from app.utils import (
    require_mechanic, get_or_404, raise_bad_request, raise_forbidden,
    enrich_access_request_response, enrich_access_requests_list
)

router = APIRouter(prefix="/api/vehicle-access", tags=["Vehicle Access"])

@router.post("/request", response_model=VehicleAccessRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_vehicle_access(
    request_data: VehicleAccessRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Mechanic requests access to a customer's vehicle
    """
    # Only mechanics can request access
    require_mechanic(current_user)
    
    # Check if vehicle exists
    vehicle = get_or_404(db, Vehicle, request_data.vehicle_id, "Vehicle")
    
    # Can't request access to own vehicle
    if vehicle.owner_id == current_user.id:
        raise_bad_request("You cannot request access to your own vehicle")
    
    # Check if request already exists
    existing_request = db.exec(
        select(VehicleAccessRequest).where(
            and_(
                VehicleAccessRequest.mechanic_id == current_user.id,
                VehicleAccessRequest.vehicle_id == request_data.vehicle_id,
                or_(
                    VehicleAccessRequest.status == AccessStatus.PENDING,
                    VehicleAccessRequest.status == AccessStatus.APPROVED
                )
            )
        )
    ).first()
    
    if existing_request:
        if existing_request.status == AccessStatus.APPROVED:
            raise_bad_request("You already have access to this vehicle")
        else:
            raise_bad_request("You already have a pending request for this vehicle")
    
    # Create new request
    access_request = VehicleAccessRequest(
        mechanic_id=current_user.id,
        vehicle_id=request_data.vehicle_id,
        owner_id=vehicle.owner_id,
        message=request_data.message,
        status=AccessStatus.PENDING
    )
    
    db.add(access_request)
    db.commit()
    db.refresh(access_request)
    
    # Add mechanic and vehicle info for response
    return enrich_access_request_response(db, access_request)

@router.get("/requests/pending", response_model=List[VehicleAccessRequestResponse])
async def get_pending_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get all pending access requests for the current user's vehicles
    """
    # Get pending requests where user is the vehicle owner
    requests = db.exec(
        select(VehicleAccessRequest).where(
            and_(
                VehicleAccessRequest.owner_id == current_user.id,
                VehicleAccessRequest.status == AccessStatus.PENDING
            )
        ).order_by(VehicleAccessRequest.created_at.desc())
    ).all()
    
    # Enrich with mechanic and vehicle info
    return enrich_access_requests_list(db, requests)

@router.get("/requests/all", response_model=List[VehicleAccessRequestResponse])
async def get_all_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get all access requests (pending, approved, rejected) for the current user's vehicles
    """
    requests = db.exec(
        select(VehicleAccessRequest).where(
            VehicleAccessRequest.owner_id == current_user.id
        ).order_by(VehicleAccessRequest.created_at.desc())
    ).all()
    
    # Enrich with mechanic and vehicle info
    return enrich_access_requests_list(db, requests)

@router.put("/requests/{request_id}/approve", response_model=VehicleAccessRequestResponse)
async def approve_access_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Approve a mechanic's access request
    """
    access_request = get_or_404(db, VehicleAccessRequest, request_id, "Access request")
    
    # Only vehicle owner can approve
    if access_request.owner_id != current_user.id:
        raise_forbidden("You can only approve requests for your own vehicles")
    
    # Can only approve pending requests
    if access_request.status != AccessStatus.PENDING:
        raise_bad_request(f"Cannot approve request with status: {access_request.status}")
    
    # Update status
    access_request.status = AccessStatus.APPROVED
    access_request.approved_at = datetime.utcnow()
    access_request.updated_at = datetime.utcnow()
    
    db.add(access_request)
    db.commit()
    db.refresh(access_request)
    
    # TODO: Send confirmation notification to mechanic
    # This could be implemented with a notification service in the future
    # For now, we log the approval which can be checked by the mechanic through API
    
    return enrich_access_request_response(db, access_request)

@router.put("/requests/{request_id}/reject", response_model=VehicleAccessRequestResponse)
async def reject_access_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Reject a mechanic's access request
    """
    access_request = get_or_404(db, VehicleAccessRequest, request_id, "Access request")
    
    # Only vehicle owner can reject
    if access_request.owner_id != current_user.id:
        raise_forbidden("You can only reject requests for your own vehicles")
    
    # Can only reject pending requests
    if access_request.status != AccessStatus.PENDING:
        raise_bad_request(f"Cannot reject request with status: {access_request.status}")
    
    # Update status
    access_request.status = AccessStatus.REJECTED
    access_request.updated_at = datetime.utcnow()
    
    db.add(access_request)
    db.commit()
    db.refresh(access_request)
    
    return enrich_access_request_response(db, access_request)
    if vehicle:
        response.vehicle_registration = vehicle.registration_number
        response.vehicle_make = vehicle.make
        response.vehicle_model = vehicle.model
    
    return response

@router.delete("/vehicles/{vehicle_id}/revoke/{mechanic_id}")
async def revoke_vehicle_access(
    vehicle_id: int,
    mechanic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Revoke a mechanic's access to a vehicle
    """
    # Check vehicle ownership
    vehicle = get_or_404(db, Vehicle, vehicle_id, "Vehicle")
    
    if vehicle.owner_id != current_user.id:
        raise_forbidden("You can only revoke access for your own vehicles")
    
    # Find approved access request
    access_request = db.exec(
        select(VehicleAccessRequest).where(
            and_(
                VehicleAccessRequest.vehicle_id == vehicle_id,
                VehicleAccessRequest.mechanic_id == mechanic_id,
                VehicleAccessRequest.status == AccessStatus.APPROVED
            )
        )
    ).first()
    
    if not access_request:
        raise_not_found("No approved access found for this mechanic")
    
    # Update to rejected (effectively revoking access)
    access_request.status = AccessStatus.REJECTED
    access_request.updated_at = datetime.utcnow()
    
    db.add(access_request)
    db.commit()
    
    return {"message": "Access revoked successfully"}

@router.get("/accessible-vehicles", response_model=List[AccessibleVehicleResponse])
async def get_accessible_vehicles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get all vehicles that the current mechanic has access to
    """
    # Only mechanics can access this endpoint
    require_mechanic(current_user)
    
    # Get all approved access requests for this mechanic
    approved_requests = db.exec(
        select(VehicleAccessRequest).where(
            and_(
                VehicleAccessRequest.mechanic_id == current_user.id,
                VehicleAccessRequest.status == AccessStatus.APPROVED
            )
        ).order_by(VehicleAccessRequest.approved_at.desc())
    ).all()
    
    # Build response with vehicle details
    accessible_vehicles = []
    for req in approved_requests:
        vehicle = db.get(Vehicle, req.vehicle_id)
        if not vehicle:
            continue
        
        owner = db.get(User, vehicle.owner_id)
        
        accessible_vehicles.append(AccessibleVehicleResponse(
            id=vehicle.id,
            registration_number=vehicle.registration_number,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            fuel_type=vehicle.fuel_type,
            owner_id=vehicle.owner_id,
            owner_name=owner.full_name if owner else None,
            owner_phone=owner.phone if owner else None,
            qr_code_url=vehicle.qr_code_url,
            primary_photo_url=vehicle.primary_photo_url,
            access_granted_at=req.approved_at or req.updated_at
        ))
    
    return accessible_vehicles

@router.get("/check-access/{vehicle_id}")
async def check_vehicle_access(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Check if current user has access to a specific vehicle
    """
    vehicle = get_or_404(db, Vehicle, vehicle_id, "Vehicle")
    
    # Owner always has access
    if vehicle.owner_id == current_user.id:
        return {
            "has_access": True,
            "access_type": "owner",
            "can_request": False
        }
    
    # Check if mechanic
    if current_user.role != "mechanic":
        return {
            "has_access": False,
            "access_type": None,
            "can_request": False
        }
    
    # Check for existing request
    existing_request = db.exec(
        select(VehicleAccessRequest).where(
            and_(
                VehicleAccessRequest.mechanic_id == current_user.id,
                VehicleAccessRequest.vehicle_id == vehicle_id
            )
        ).order_by(VehicleAccessRequest.created_at.desc())
    ).first()
    
    if not existing_request:
        return {
            "has_access": False,
            "access_type": None,
            "can_request": True,
            "request_status": None
        }
    
    return {
        "has_access": existing_request.status == AccessStatus.APPROVED,
        "access_type": "mechanic" if existing_request.status == AccessStatus.APPROVED else None,
        "can_request": existing_request.status == AccessStatus.REJECTED,
        "request_status": existing_request.status,
        "request_id": existing_request.id
    }
