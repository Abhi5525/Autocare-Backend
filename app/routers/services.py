# app/routers/services.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import List, Optional
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
from app.utils import (
    get_or_404, raise_not_found, raise_forbidden, raise_bad_request,
    require_vehicle_access, check_vehicle_ownership, require_service_edit_permission
)

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
    # Check vehicle exists and permissions
    vehicle = get_or_404(db, Vehicle, service_data.vehicle_id, "Vehicle")
    check_vehicle_ownership(current_user, vehicle)
    
    # Prepare service data dict
    service_dict = service_data.dict(exclude={'parts_replaced', 'labor_cost', 'parts_cost', 'notes'})
    
    # Map 'notes' to 'service_notes' if provided
    if service_data.notes:
        service_dict['service_notes'] = service_data.notes
    
    # Create service record
    service = ServiceRecord(**service_dict)
    
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
    
    # Handle parts_replaced if provided (store in service_notes or as separate records)
    if service_data.parts_replaced:
        parts_text = ", ".join(service_data.parts_replaced)
        if service.service_notes:
            service.service_notes += f"\nParts replaced: {parts_text}"
        else:
            service.service_notes = f"Parts replaced: {parts_text}"
        
        # Store labor and parts cost info
        cost_details = []
        if service_data.labor_cost:
            cost_details.append(f"Labor: Rs {service_data.labor_cost}")
        if service_data.parts_cost:
            cost_details.append(f"Parts: Rs {service_data.parts_cost}")
        
        if cost_details:
            service.service_notes += f"\nCost breakdown: {', '.join(cost_details)}"
        
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
        raise_not_found("Service record", service_id)
    
    # Check vehicle permissions
    vehicle = get_or_404(db, Vehicle, service.vehicle_id, "Vehicle")
    check_vehicle_ownership(current_user, vehicle)
    
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
    service = get_or_404(db, ServiceRecord, service_id, "Service record")
    
    if service.status != ServiceStatus.DRAFT:
        raise_bad_request("Only draft records can be approved")
    
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
    service = get_or_404(db, ServiceRecord, service_id, "Service record")
    
    if service.status != ServiceStatus.DRAFT:
        raise_bad_request("Only draft records can be rejected")
    
    service.status = ServiceStatus.REJECTED
    service.voice_transcript = f"{service.voice_transcript or ''}\n\nREJECTED: {reason}"
    service.updated_at = datetime.now()
    
    db.add(service)
    db.commit()
    
    return {"message": "Service draft rejected", "service_id": service_id}

@router.delete("/{service_id}")
async def delete_service_record(
    service_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete a service record (only drafts can be deleted, only by creator or admin)
    """
    service = get_or_404(db, ServiceRecord, service_id, "Service record")
    
    # Check permissions - only allow deleting drafts
    if service.status != ServiceStatus.DRAFT:
        raise_bad_request("Only draft services can be deleted")
    
    # Check if user can delete (creator or admin)
    require_service_edit_permission(current_user, service.mechanic_id, service.status)
    
    db.delete(service)
    db.commit()
    
    return {"message": "Service record deleted successfully", "service_id": service_id}

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

@router.put("/{service_id}/draft-update", response_model=ServiceRecordResponse)
async def update_draft_service(
    service_id: int,
    draft_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update a draft service record from voice entry review
    """
    service = get_or_404(db, ServiceRecord, service_id, "Service record")
    
    # Only allow updating drafts
    if service.status != ServiceStatus.DRAFT:
        raise_bad_request("Can only update draft services")
    
    # Check permissions
    require_service_edit_permission(current_user, service.mechanic_id, service.status)
    
    # Update allowed fields
    if 'description' in draft_update:
        service.description = draft_update['description']
    if 'service_notes' in draft_update:
        service.service_notes = draft_update['service_notes']
    if 'cost_estimate' in draft_update:
        service.cost_estimate = float(draft_update['cost_estimate'])
    if 'odometer_reading' in draft_update:
        service.odometer_reading = int(draft_update['odometer_reading'])
    
    service.updated_at = datetime.now()
    
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return service

@router.put("/{service_id}/submit-draft", response_model=ServiceRecordResponse)
async def submit_draft_service(
    service_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Submit a draft service for approval/completion
    """
    service = get_or_404(db, ServiceRecord, service_id, "Service record")
    
    # Only allow submitting drafts
    if service.status != ServiceStatus.DRAFT:
        raise_bad_request("Can only submit draft services")
    
    # Check permissions
    require_service_edit_permission(current_user, service.mechanic_id, service.status)
    
    # Update vehicle odometer if provided
    if service.odometer_reading:
        vehicle = db.get(Vehicle, service.vehicle_id)
        if vehicle and service.odometer_reading > vehicle.current_odometer:
            vehicle.current_odometer = service.odometer_reading
            vehicle.last_service_date = service.service_date
            vehicle.last_service_km = service.odometer_reading
            db.add(vehicle)
    
    # Mechanics can self-approve their service records
    service.status = ServiceStatus.APPROVED
    service.approver_id = current_user.id
    service.approved_at = datetime.now()
    service.completion_date = datetime.now()
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
    service = get_or_404(db, ServiceRecord, service_id, "Service record")
    
    # Check if mechanic owns this service
    if service.mechanic_id != current_user.id and current_user.role != "admin":
        raise_forbidden("You can only upload photos for your own service records")
    
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
    vehicle = get_or_404(db, Vehicle, vehicle_id, "Vehicle")
    check_vehicle_ownership(current_user, vehicle)
    
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


@router.get("/admin/vehicle/{vehicle_id}/full-history")
async def get_vehicle_full_history(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get complete service history for a vehicle (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access full vehicle history"
        )
    
    from app.models.vehicle import Vehicle
    
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Get all service records for this vehicle
    services = db.query(ServiceRecord).filter(
        ServiceRecord.vehicle_id == vehicle_id
    ).order_by(ServiceRecord.created_at.desc()).all()
    
    # Get owner information
    owner = db.query(User).filter(User.id == vehicle.owner_id).first()
    
    # Calculate statistics
    total_services = len(services)
    total_spent = sum(
        (s.final_cost or s.cost_estimate or 0) + 
        sum(p.total_price for p in s.parts_used) if s.parts_used else 0
        for s in services
    )
    
    return {
        "vehicle": {
            "id": vehicle.id,
            "registration": vehicle.registration_number,
            "brand": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "color": vehicle.color
        },
        "owner": {
            "id": owner.id,
            "full_name": owner.full_name,
            "email": owner.email,
            "phone": owner.phone
        },
        "statistics": {
            "total_services": total_services,
            "total_spent": round(total_spent, 2),
            "avg_service_cost": round(total_spent / total_services if total_services > 0 else 0, 2)
        },
        "services": services
    }