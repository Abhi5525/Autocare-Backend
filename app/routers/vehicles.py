# app/routers/vehicles.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from sqlmodel import Session, select, or_
from typing import List, Optional
import os

from app.core.database import get_session
from app.dependencies.deps import get_current_user, get_current_owner
from app.models.user import User
from app.models.vehicle import Vehicle, VehicleCreate, VehicleUpdate, VehicleType, FuelType, TransmissionType
from app.models.vehicle_photo import VehiclePhoto, VehiclePhotoCreate
from app.models.vehicle_access import VehicleAccessRequest, AccessStatus
from app.services.upload_service import UploadService, UPLOAD_DIRS
from app.services.qr_service import QRService
from app.utils import (
    get_or_404, raise_not_found, raise_forbidden, raise_bad_request,
    check_vehicle_ownership, validate_unique_vehicle_registration
)

router = APIRouter(prefix="/api/vehicles", tags=["Vehicles"])

@router.post("/", response_model=Vehicle, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    vehicle_data: VehicleCreate,
    current_user: User = Depends(get_current_owner),
    db: Session = Depends(get_session)
):
    """
    Create a new vehicle (for vehicle owners)
    """
    # Check if vehicle with same registration already exists
    validate_unique_vehicle_registration(db, vehicle_data.registration_number)
    
    # Create vehicle with authenticated user as owner
    vehicle = Vehicle(**vehicle_data.dict(), owner_id=current_user.id)
    
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    
    # Generate QR code
    qr_url = QRService.generate_vehicle_qr(vehicle.id, vehicle.registration_number)
    vehicle.qr_code_url = qr_url
    
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    
    return vehicle

@router.get("/search", response_model=List[Vehicle])
async def search_vehicles(
    query: str = Query(..., description="Search by registration number, VIN, or vehicle ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    limit: int = 10
):
    """
    Search vehicles by registration number, VIN, or ID
    For mechanics: Only return vehicles they have access to
    For owners: Return only their vehicles
    For admins: Return all matching vehicles
    """
    if not query.strip():
        return []
    
    # Base search query
    search_query = select(Vehicle).where(
        or_(
            Vehicle.registration_number.ilike(f"%{query}%"),
            Vehicle.vin.ilike(f"%{query}%"),
            Vehicle.id == int(query) if query.isdigit() else False
        )
    ).limit(limit)
    
    # Apply role-based filtering
    if current_user.role == "owner":
        # Owners can only see their own vehicles
        search_query = search_query.where(Vehicle.owner_id == current_user.id)
    elif current_user.role == "mechanic":
        # Mechanics can only see vehicles they have approved access to
        accessible_vehicle_ids = db.exec(
            select(VehicleAccessRequest.vehicle_id).where(
                VehicleAccessRequest.mechanic_id == current_user.id,
                VehicleAccessRequest.status == AccessStatus.APPROVED
            )
        ).all()
        
        if not accessible_vehicle_ids:
            return []
        
        search_query = search_query.where(Vehicle.id.in_(accessible_vehicle_ids))
    # Admins see all vehicles (no additional filtering)
    
    vehicles = db.exec(search_query).all()
    return vehicles

@router.get("/my-vehicles", response_model=List[Vehicle])
async def get_my_vehicles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    vehicle_type: Optional[VehicleType] = None,
    make: Optional[str] = None
):
    """
    Get all vehicles for the current user with optional filters
    """
    query = select(Vehicle).where(Vehicle.owner_id == current_user.id)
    
    # Apply filters
    if vehicle_type:
        query = query.where(Vehicle.vehicle_type == vehicle_type)
    
    if make:
        query = query.where(Vehicle.make.ilike(f"%{make}%"))
    
    # Order by creation date (newest first)
    query = query.order_by(Vehicle.created_at.desc())
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    vehicles = db.exec(query).all()
    return vehicles

@router.get("/{vehicle_id}", response_model=Vehicle)
async def get_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get specific vehicle by ID
    """
    vehicle = get_or_404(db, Vehicle, vehicle_id, "Vehicle")
    check_vehicle_ownership(current_user, vehicle)
    
    return vehicle

@router.get("/registration/{registration}", response_model=Vehicle)
async def get_vehicle_by_registration(
    registration: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get vehicle by registration number
    """
    vehicle = db.exec(
        select(Vehicle).where(Vehicle.registration_number == registration)
    ).first()
    
    if not vehicle:
        raise_not_found("Vehicle")
    
    # Check permissions
    check_vehicle_ownership(current_user, vehicle)
    
    return vehicle

@router.put("/{vehicle_id}", response_model=Vehicle)
async def update_vehicle(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update vehicle details
    """
    vehicle = get_or_404(db, Vehicle, vehicle_id, "Vehicle")
    check_vehicle_ownership(current_user, vehicle)
    
    # Update fields
    update_data = vehicle_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(vehicle, field, value)
    
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    
    return vehicle

@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete a vehicle (soft delete - just mark as inactive)
    """
    vehicle = get_or_404(db, Vehicle, vehicle_id, "Vehicle")
    
    # Check ownership
    if vehicle.owner_id != current_user.id and current_user.role != "admin":
        raise_forbidden("You don't have permission to delete this vehicle")
    
    # For now, just delete (later we can implement soft delete)
    db.delete(vehicle)
    db.commit()
    
    return None

@router.post("/{vehicle_id}/photos", response_model=VehiclePhoto)
async def upload_vehicle_photo(
    vehicle_id: int,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Upload a photo for a vehicle
    """
    # Get vehicle
    vehicle = db.get(Vehicle, vehicle_id)
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Check ownership
    if vehicle.owner_id != current_user.id and current_user.role not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to upload photos for this vehicle"
        )
    
    # Validate and process image
    upload_service = UploadService()
    image, file_ext = upload_service.validate_image(file)
    
    # Get file size before processing
    file.file.seek(0)
    file_contents = file.file.read()
    file_size = len(file_contents)
    file.file.seek(0)
    
    # Save image
    filename = upload_service.save_image(
        image, 
        file_ext, 
        UPLOAD_DIRS["vehicles"]
    )
    
    # Create photo record
    photo = VehiclePhoto(
        vehicle_id=vehicle_id,
        photo_url=f"/uploads/vehicles/{filename}",
        uploaded_by=current_user.id,
        caption=caption,
        is_primary=is_primary,
        file_size=file_size,
        file_type=file.content_type or "image/jpeg",
        width=image.width,
        height=image.height
    )
    
    # Check if this is the first photo for the vehicle
    existing_photos = db.exec(
        select(VehiclePhoto).where(VehiclePhoto.vehicle_id == vehicle_id)
    ).all()
    
    # If no existing photos or is_primary is True, set as primary
    if len(existing_photos) == 0 or is_primary:
        photo.is_primary = True
        is_primary = True
    
    # If this is primary, unset other primary photos
    if is_primary:
        # Get existing primary photo
        existing_primary = db.exec(
            select(VehiclePhoto).where(
                VehiclePhoto.vehicle_id == vehicle_id,
                VehiclePhoto.is_primary == True
            )
        ).first()
        
        if existing_primary:
            existing_primary.is_primary = False
            db.add(existing_primary)
        
        # Update vehicle's primary photo URL
        vehicle.primary_photo_url = f"/uploads/vehicles/{filename}"
        db.add(vehicle)
    
    db.add(photo)
    db.commit()
    db.refresh(photo)
    
    if is_primary:
        db.refresh(vehicle)
    
    return photo
    return photo

@router.get("/{vehicle_id}/photos", response_model=List[VehiclePhoto])
async def get_vehicle_photos(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get all photos for a vehicle
    """
    # Get vehicle
    vehicle = get_or_404(db, Vehicle, vehicle_id, "Vehicle")
    check_vehicle_ownership(current_user, vehicle)
    
    photos = db.exec(
        select(VehiclePhoto)
        .where(VehiclePhoto.vehicle_id == vehicle_id)
        .order_by(VehiclePhoto.is_primary.desc(), VehiclePhoto.uploaded_at.desc())
    ).all()
    
    return photos

@router.get("/{vehicle_id}/qr")
async def get_vehicle_qr(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get vehicle QR code (regenerate if missing)
    """
    vehicle = get_or_404(db, Vehicle, vehicle_id, "Vehicle")
    check_vehicle_ownership(current_user, vehicle)
    
    # Generate QR if not exists
    if not vehicle.qr_code_url or not os.path.exists(vehicle.qr_code_url.replace("/uploads/", "app/uploads/")):
        qr_url = QRService.generate_vehicle_qr(vehicle.id, vehicle.registration_number)
        vehicle.qr_code_url = qr_url
        db.add(vehicle)
        db.commit()
    
    return {
        "qr_code_url": vehicle.qr_code_url,
        "vehicle_id": vehicle.id,
        "registration": vehicle.registration_number
    }

@router.post("/scan-qr")
async def scan_vehicle_qr(
    qr_data: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Scan QR code to get vehicle information
    """
    parsed = QRService.parse_qr_data(qr_data)
    
    if not parsed or parsed["type"] != "vehicle":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid QR code"
        )
    
    vehicle = get_or_404(db, Vehicle, parsed["vehicle_id"], "Vehicle")
    check_vehicle_ownership(current_user, vehicle)
    
    return vehicle