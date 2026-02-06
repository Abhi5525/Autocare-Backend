# app/routers/services.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import json

from app.core.database import get_session
from app.dependencies.deps import get_current_user, get_current_mechanic, get_current_admin
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.service import (
    ServiceRecord, ServiceRecordCreate, ServiceRecordUpdate,
    ServiceStatus, ServicePart, ServiceType
)
from app.schemas.service import (
    ServiceRecordResponse, VoiceProcessingRequest, VoiceProcessingResponse
)
from app.services.voice_service import VoiceProcessingService
from app.services.upload_service import UploadService, UPLOAD_DIRS

router = APIRouter(prefix="/api/services", tags=["Services"])
voice_service = VoiceProcessingService()

# ===== SERVICE RECORDS =====

@router.get("/", response_model=List[ServiceRecordResponse])
async def list_all_services(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """
    Get all service records (filtered by user role)
    """
    query = select(ServiceRecord).options(selectinload(ServiceRecord.parts_used))
    
    # Filter by role
    if current_user.role == "owner":
        # Owners see services for their vehicles
        query = query.join(Vehicle).where(Vehicle.owner_id == current_user.id)
    elif current_user.role == "mechanic":
        # Mechanics see services they created
        query = query.where(ServiceRecord.mechanic_id == current_user.id)
    # Admins see everything
    
    query = query.order_by(ServiceRecord.created_at.desc()).offset(skip).limit(limit)
    services = db.exec(query).all()
    return services

@router.post("/", response_model=ServiceRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_service_record(
    service_data: ServiceRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new service record (manual entry)
    """
    # Check if vehicle exists
    vehicle = db.get(Vehicle, service_data.vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Check permissions
    if vehicle.owner_id != current_user.id and current_user.role not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add services for this vehicle"
        )
    
    # Create service record
    service = ServiceRecord(**service_data.dict())
    
    # Set mechanic if not specified and current user is mechanic
    if not service.mechanic_id and current_user.role == "mechanic":
        service.mechanic_id = current_user.id
    
    # Set status: approved if owner/admin creates, draft if mechanic creates
    if current_user.role in ["owner", "admin"]:
        service.status = ServiceStatus.APPROVED
        service.approver_id = current_user.id
        service.approved_at = datetime.now()
    else:
        service.status = ServiceStatus.DRAFT
    
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return service

@router.post("/voice-draft", response_model=VoiceProcessingResponse)
async def create_voice_draft(
    voice_request: VoiceProcessingRequest,
    current_user: User = Depends(get_current_mechanic),
    db: Session = Depends(get_session)
):
    """
    Create a service draft from voice input
    """
    # Get vehicle by registration
    vehicle = db.exec(
        select(Vehicle).where(Vehicle.registration_number == voice_request.vehicle_registration)
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Process transcript
    if voice_request.transcript:
        transcript = voice_request.transcript
    else:
        # TODO: Implement audio processing
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio processing not implemented yet. Please provide transcript."
        )
    
    # Parse transcript
    try:
        parsed_data = voice_service.process_transcript(transcript)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process transcript: {str(e)}"
        )
    
    # Convert service type string to enum
    service_type_str = parsed_data.get('service_type', 'regular')
    if service_type_str == 'regular':
        service_type = ServiceType.REGULAR_SERVICE
    elif service_type_str == 'repair':
        service_type = ServiceType.REPAIR  
    elif service_type_str == 'inspection':
        service_type = ServiceType.INSPECTION
    elif service_type_str == 'emergency':
        service_type = ServiceType.EMERGENCY
    else:
        service_type = ServiceType.REGULAR_SERVICE
    
    # Create draft service record with correct field names
    try:
        service = ServiceRecord(
            vehicle_id=vehicle.id,
            service_type=service_type,
            description=parsed_data.get('work_summary', 'Voice processed service'),
            service_notes=f"Voice transcript: {transcript}",
            cost_estimate=float(parsed_data.get('total_cost', 0.0)),
            service_date=date.today(),
            
            # Voice-specific fields
            voice_transcript=transcript,
            confidence_score=float(parsed_data.get('confidence_score', 0.0)),
            status=ServiceStatus.DRAFT,
            mechanic_id=current_user.id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create service record: {str(e)}"
        )
    
    # Store parsed data as JSON
    try:
        service.set_parsed_data(parsed_data)
        
        db.add(service)
        db.commit()
        db.refresh(service)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save service record: {str(e)}"
        )
    
    # Create parts records from parsed data
    if 'parts_replaced' in parsed_data:
        all_parts = parsed_data.get('parts_replaced', []) + parsed_data.get('parts_repaired', [])
        for part_data in all_parts:
            part = ServicePart(
                service_id=service.id,
                part_name=part_data.get('name', 'Unknown Part'),
                quantity=part_data.get('quantity', 1),
                unit_price=part_data.get('estimated_price', 0.0),
                total_price=part_data.get('estimated_price', 0.0) * part_data.get('quantity', 1),
                installed_by=current_user.id
            )
            db.add(part)
        
        db.commit()
    
    # Convert service to response format
    service_response = ServiceRecordResponse(
        id=service.id,
        vehicle_id=service.vehicle_id,
        mechanic_id=service.mechanic_id,
        approver_id=service.approver_id,
        service_type=service.service_type,
        description=service.description,
        service_notes=service.service_notes,
        cost_estimate=service.cost_estimate,
        final_cost=service.final_cost,
        payment_status=service.payment_status,
        status=service.status,
        service_date=service.service_date,
        completion_date=service.completion_date,
        voice_transcript=service.voice_transcript,
        ai_parsed_data=service.ai_parsed_data,
        confidence_score=service.confidence_score,
        created_at=service.created_at,
        updated_at=service.updated_at,
        approved_at=service.approved_at,
        parts_used=[]  # Will be populated later if needed
    )
    
    return VoiceProcessingResponse(
        draft_id=service.id,
        transcript=transcript,
        parsed_data=parsed_data,
        confidence_score=parsed_data.get('confidence_score', 0.0),
        message="Voice transcript processed successfully",
        service_record=service_response
    )

@router.get("/drafts", response_model=List[ServiceRecordResponse])
async def get_draft_services(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 50
):
    """
    Get draft service records
    """
    query = select(ServiceRecord).options(selectinload(ServiceRecord.parts_used)).where(ServiceRecord.status == ServiceStatus.DRAFT)
    
    # Mechanics can only see their drafts
    if current_user.role == "mechanic":
        query = query.where(ServiceRecord.mechanic_id == current_user.id)
    # Owners can only see drafts for their vehicles
    elif current_user.role == "owner":
        query = query.join(Vehicle).where(Vehicle.owner_id == current_user.id)
    
    query = query.order_by(ServiceRecord.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    drafts = db.exec(query).all()
    return drafts

@router.get("/approved", response_model=List[ServiceRecordResponse])
async def get_approved_services(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    vehicle_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = 0,
    limit: int = 100
):
    """
    Get approved service records with filters
    """
    query = select(ServiceRecord).options(selectinload(ServiceRecord.parts_used)).where(ServiceRecord.status == ServiceStatus.APPROVED)
    
    # Apply filters
    if vehicle_id:
        query = query.where(ServiceRecord.vehicle_id == vehicle_id)
    
    if start_date:
        query = query.where(ServiceRecord.service_date >= start_date)
    
    if end_date:
        query = query.where(ServiceRecord.service_date <= end_date)
    
    # Permission filtering
    if current_user.role == "owner":
        # Owners can only see services for their vehicles
        query = query.join(Vehicle).where(Vehicle.owner_id == current_user.id)
    
    query = query.order_by(ServiceRecord.service_date.desc())
    query = query.offset(skip).limit(limit)
    
    services = db.exec(query).all()
    return services

@router.get("/{service_id}", response_model=ServiceRecordResponse)
async def get_service_record(
    service_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get specific service record
    """
    query = select(ServiceRecord).options(selectinload(ServiceRecord.parts_used)).where(ServiceRecord.id == service_id)
    service = db.exec(query).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service record not found"
        )
    
    # Check permissions
    vehicle = db.get(Vehicle, service.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    if vehicle.owner_id != current_user.id and current_user.role not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this service record"
        )
    
    return service

@router.put("/{service_id}/approve", response_model=ServiceRecordResponse)
async def approve_service_draft(
    service_id: int,
    current_user: User = Depends(get_current_admin),  # Only admins/managers can approve
    db: Session = Depends(get_session)
):
    """
    Approve a draft service record
    """
    service = db.get(ServiceRecord, service_id)
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service record not found"
        )
    
    if service.status != ServiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft records can be approved"
        )
    
    # Update service
    service.status = ServiceStatus.APPROVED
    service.approver_id = current_user.id  # Correct field name
    service.approved_at = datetime.now()
    service.updated_at = datetime.now()
    
    # Update vehicle's last service info (if we have a service date)
    vehicle = db.get(Vehicle, service.vehicle_id)
    if vehicle and service.service_date:
        vehicle.last_service_date = service.service_date
        # Note: odometer_reading field doesn't exist in our model
        # vehicle.last_service_km = service.odometer_reading
        
        # Set next service reminder (6 months or 10,000 km)
        if not vehicle.next_service_date:
            vehicle.next_service_date = service.service_date + timedelta(days=180)
        # if not vehicle.next_service_km:
        #     vehicle.next_service_km = service.odometer_reading + 10000
        
        db.add(vehicle)
    
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return service

@router.put("/{service_id}/reject")
async def reject_service_draft(
    service_id: int,
    reason: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_session)
):
    """
    Reject a draft service record
    """
    service = db.get(ServiceRecord, service_id)
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service record not found"
        )
    
    if service.status != ServiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft records can be rejected"
        )
    
    service.status = ServiceStatus.REJECTED
    service.voice_transcript = f"{service.voice_transcript or ''}\n\nREJECTED: {reason}"
    service.updated_at = datetime.now()
    
    db.add(service)
    db.commit()
    
    return {"message": "Service draft rejected", "service_id": service_id}

@router.put("/{service_id}", response_model=ServiceRecordResponse)
async def update_service_record(
    service_id: int,
    service_update: ServiceRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update a service record
    """
    service = db.get(ServiceRecord, service_id)
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service record not found"
        )
    
    # Check permissions
    vehicle = db.get(Vehicle, service.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    can_edit = (
        current_user.role == "admin" or
        (current_user.role == "mechanic" and service.mechanic_id == current_user.id) or
        (current_user.role == "owner" and vehicle.owner_id == current_user.id and service.status == ServiceStatus.DRAFT)
    )
    
    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this service record"
        )
    
    # Update fields
    update_data = service_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(service, field, value)
    
    service.updated_at = datetime.now()
    
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return service

@router.post("/{service_id}/photos")
async def upload_service_photos(
    service_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_mechanic),
    db: Session = Depends(get_session)
):
    """
    Upload photos for a service record
    """
    service = db.get(ServiceRecord, service_id)
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service record not found"
        )
    
    # Check if mechanic owns this service
    if service.mechanic_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload photos for your own service records"
        )
    
    upload_service = UploadService()
    uploaded_urls = []
    
    for file in files:
        # Validate and process image
        image, file_ext = upload_service.validate_image(file)
        
        # Save image
        filename = upload_service.save_image(
            image,
            file_ext,
            UPLOAD_DIRS["service_photos"]
        )
        
        url = f"/uploads/service_photos/{filename}"
        uploaded_urls.append(url)
    
    # Update service record with photo URLs
    existing_photos = []
    if service.work_photos:
        existing_photos = json.loads(service.work_photos)
    
    existing_photos.extend(uploaded_urls)
    service.work_photos = json.dumps(existing_photos)
    service.updated_at = datetime.now()
    
    db.add(service)
    db.commit()
    
    return {
        "message": f"{len(uploaded_urls)} photos uploaded",
        "urls": uploaded_urls,
        "total_photos": len(existing_photos)
    }

@router.get("/vehicle/{vehicle_id}/history", response_model=List[ServiceRecordResponse])
async def get_vehicle_service_history(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    limit: int = 50
):
    """
    Get service history for a vehicle
    """
    vehicle = db.get(Vehicle, vehicle_id)
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Check permissions
    if vehicle.owner_id != current_user.id and current_user.role not in ["admin", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this vehicle's service history"
        )
    
    services = db.exec(
        select(ServiceRecord)
        .options(selectinload(ServiceRecord.parts_used))
        .where(ServiceRecord.vehicle_id == vehicle_id)
        .where(ServiceRecord.status == ServiceStatus.APPROVED)
        .order_by(ServiceRecord.service_date.desc())
        .limit(limit)
    ).all()
    
    return services

# ===== STATISTICS =====

@router.get("/statistics")
async def get_service_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    """
    Get service statistics
    """
    query = select(ServiceRecord).options(selectinload(ServiceRecord.parts_used)).where(ServiceRecord.status == ServiceStatus.APPROVED)
    
    if start_date:
        query = query.where(ServiceRecord.service_date >= start_date)
    if end_date:
        query = query.where(ServiceRecord.service_date <= end_date)
    
    # Permission filtering
    if current_user.role == "owner":
        query = query.join(Vehicle).where(Vehicle.owner_id == current_user.id)
    elif current_user.role == "mechanic":
        query = query.where(ServiceRecord.mechanic_id == current_user.id)
    
    services = db.exec(query).all()
    
    # Calculate statistics including parts costs
    total_services = len(services)
    total_revenue = 0
    for s in services:
        base_cost = s.final_cost if s.final_cost is not None else (s.cost_estimate or 0)
        parts_cost = sum(part.total_price for part in s.parts_used) if s.parts_used else 0
        total_revenue += base_cost + parts_cost
    
    avg_service_cost = total_revenue / total_services if total_services > 0 else 0
    
    # Count by service type
    service_type_counts = {}
    for s in services:
        service_type_counts[s.service_type] = service_type_counts.get(s.service_type, 0) + 1
    
    # Recent services (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_services = [s for s in services if s.created_at >= thirty_days_ago]
    
    return {
        "total_services": total_services,
        "total_revenue": round(total_revenue, 2),
        "average_service_cost": round(avg_service_cost, 2),
        "recent_services_count": len(recent_services),
        "service_type_distribution": service_type_counts,
        "time_period": {
            "start_date": start_date,
            "end_date": end_date or date.today()
        }
    }