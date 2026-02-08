# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, func
from typing import Optional
import os
from PIL import Image
import io
from datetime import datetime, timedelta
import secrets
import hashlib

from app.core.database import get_session
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User, UserCreate, UserLogin, Token, TokenWithUser, UserUpdate
from app.dependencies.deps import get_current_user
from app.utils import (
    require_admin, validate_password_strength,
    validate_unique_user_credentials, validate_mechanic_credentials,
    raise_bad_request, get_or_404
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenWithUser, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_session)
):
    """
    Register a new user.
    Mechanics require admin approval before they can use the system.
    """
    # Check email and phone uniqueness
    validate_unique_user_credentials(db, user_data.email, user_data.phone)
    
    # Validate mechanic-specific fields
    if user_data.role == "mechanic":
        if not all([user_data.citizen_number, user_data.garage_registration, 
                   user_data.pan_number, user_data.garage_address]):
            raise_bad_request("Mechanics must provide citizen number, garage registration, PAN number, and garage address")
        
        # Check for duplicate mechanic credentials
        validate_mechanic_credentials(
            db,
            user_data.citizen_number,
            user_data.garage_registration,
            user_data.pan_number
        )
    
    hashed_password = get_password_hash(user_data.password)

    user = User(
        email=user_data.email,
        phone=user_data.phone,
        full_name=user_data.full_name,
        password_hash=hashed_password,
        is_verified=False,
        role=user_data.role,
        # Address fields
        address=user_data.address,
        city=user_data.city,
        state=user_data.state,
        municipality=user_data.municipality,
        ward_no=user_data.ward_no,
        # Mechanic-specific fields
        citizen_number=user_data.citizen_number,
        garage_registration=user_data.garage_registration,
        pan_number=user_data.pan_number,
        garage_address=user_data.garage_address,
        workshop_name=user_data.workshop_name,  # Optional workshop/service center name
        # Mechanics start as active but need admin approval
        is_active=True,  # Always true so mechanics show as "Pending" not "Rejected"
        is_approved=True if user_data.role != "mechanic" else False  # Only mechanics need approval
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Don't create token for unapproved mechanics
    if user.role == "mechanic" and not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Your registration is pending admin approval. You will receive a notification once approved."
        )
    
    access_token = create_access_token(data={"user_id": user.id, "role": user.role})
    
    return TokenWithUser(
        access_token=access_token,
        token_type="bearer",
        user=user
    )

@router.post("/login", response_model=TokenWithUser)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
):
    """
    Login with email/phone and password
    """
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.phone == form_data.username)
    ).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/phone or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account has been deactivated"
        )
    
    # Check if mechanic is approved
    if user.role == "mechanic" and not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your mechanic account is under review and will be activated within 24 hours. Please check back later or contact support if you need immediate assistance."
        )
    
    access_token = create_access_token(data={"user_id": user.id, "role": user.role})
    
    return TokenWithUser(
        access_token=access_token,
        token_type="bearer",
        user=user
    )

@router.post("/login-json", response_model=TokenWithUser)
async def login_json(
    login_data: UserLogin,
    db: Session = Depends(get_session)
):
    """
    Alternative login endpoint that accepts JSON
    """
    if login_data.email:
        user = db.query(User).filter(User.email == login_data.email).first()
    elif login_data.phone:
        user = db.query(User).filter(User.phone == login_data.phone).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone must be provided"
        )
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account has been deactivated"
        )
    
    # Check if mechanic is approved
    if user.role == "mechanic" and not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your mechanic account is under review and will be activated within 24 hours. Please check back later or contact support if you need immediate assistance."
        )
    
    access_token = create_access_token(data={"user_id": user.id, "role": user.role})
    
    return TokenWithUser(
        access_token=access_token,
        token_type="bearer",
        user=user
    )

@router.get("/me", response_model=User)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@router.put("/me", response_model=User)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Update user profile"""
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if value is not None:
            setattr(current_user, field, value)
    
    current_user.updated_at = datetime.now()
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/me/profile-picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Upload profile picture"""
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed. Use JPG, PNG, or GIF"
        )
    
    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
        image.verify()
        await file.seek(0)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file"
        )
    
    upload_dir = "app/uploads/profiles"
    os.makedirs(upload_dir, exist_ok=True)
    
    filename = f"profile_{current_user.id}{file_ext}"
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as buffer:
        contents = await file.read()
        buffer.write(contents)
    
    current_user.profile_pic_url = f"/uploads/profiles/{filename}"
    current_user.updated_at = datetime.now()
    
    db.add(current_user)
    db.commit()
    
    return {"message": "Profile picture uploaded", "url": current_user.profile_pic_url}

@router.post("/verify-phone")
async def verify_phone(
    otp: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Verify phone number with OTP (placeholder)"""
    current_user.is_verified = True
    current_user.updated_at = datetime.now()
    
    db.add(current_user)
    db.commit()
    
    return {"message": "Phone verified successfully"}

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Change user password"""
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.password_hash = get_password_hash(new_password)
    current_user.updated_at = datetime.now()
    
    db.add(current_user)
    db.commit()
    
    return {"message": "Password changed successfully"}

@router.get("/admin/pending-mechanics")
async def get_pending_mechanics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get all pending mechanic registrations (admin only)"""
    require_admin(current_user)
    
    pending_mechanics = db.query(User).filter(
        User.role == "mechanic",
        User.is_approved == False
    ).all()
    
    return pending_mechanics

@router.put("/admin/approve-mechanic/{mechanic_id}")
async def approve_mechanic(
    mechanic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Approve a mechanic registration (admin only)"""
    require_admin(current_user)
    
    mechanic = get_or_404(db, User, mechanic_id, "Mechanic")
    
    if mechanic.role != "mechanic":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a mechanic"
        )
    
    mechanic.is_approved = True
    mechanic.is_active = True
    mechanic.approved_by = current_user.id
    mechanic.approved_at = datetime.now()
    mechanic.updated_at = datetime.now()
    
    db.add(mechanic)
    db.commit()
    
    return {"message": f"Mechanic {mechanic.full_name} approved successfully"}

@router.put("/admin/reject-mechanic/{mechanic_id}")
async def reject_mechanic(
    mechanic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    reason: Optional[str] = None,
    comments: Optional[str] = None
):
    """Reject a mechanic registration (admin only)"""
    require_admin(current_user)
    
    mechanic = db.query(User).filter(User.id == mechanic_id).first()
    if not mechanic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mechanic not found"
        )
    
    # Mark as rejected instead of deleting
    mechanic.is_active = False
    mechanic.is_approved = False
    mechanic.updated_at = datetime.now()
    # Store rejection reason in a field (you could add a rejection_reason field)
    
    db.add(mechanic)
    db.commit()
    
    return {"message": f"Mechanic {mechanic.full_name} rejected", "reason": reason}

# ===== COMPREHENSIVE ADMIN ENDPOINTS =====

@router.get("/admin/statistics")
async def get_admin_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get comprehensive system statistics (admin only)"""
    require_admin(current_user)
    
    # Count users by role
    total_users = db.query(User).count()
    total_owners = db.query(User).filter(User.role == "owner").count()
    total_mechanics = db.query(User).filter(User.role == "mechanic", User.is_approved == True).count()
    pending_mechanics = db.query(User).filter(User.role == "mechanic", User.is_approved == False).count()
    
    # Import Vehicle and ServiceRecord
    from app.models.vehicle import Vehicle
    from app.models.service import ServiceRecord
    
    total_vehicles = db.query(Vehicle).count()
    total_services = db.query(ServiceRecord).count()
    pending_services = db.query(ServiceRecord).filter(ServiceRecord.status == "pending_approval").count()
    
    # Calculate revenue (mock for now)
    total_revenue = db.query(ServiceRecord).filter(ServiceRecord.total_cost.isnot(None)).count() * 1500  # Mock calculation
    
    return {
        "total_users": total_users,
        "total_owners": total_owners,
        "total_mechanics": total_mechanics,
        "total_vehicles": total_vehicles,
        "total_services": total_services,
        "pending_mechanics": pending_mechanics,
        "pending_services": pending_services,
        "total_revenue": total_revenue,
        "system_uptime": 99.8,
        "user_satisfaction": 87
    }

@router.get("/admin/all-mechanics")
async def get_all_mechanics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    filter_status: Optional[str] = None
):
    """Get all mechanics with optional status filter (admin only)"""
    require_admin(current_user)
    
    query = db.query(User).filter(User.role == "mechanic")
    
    if filter_status == "pending":
        query = query.filter(User.is_approved == False)
    elif filter_status == "approved":
        query = query.filter(User.is_approved == True)
    elif filter_status == "rejected":
        query = query.filter(User.is_approved == False, User.is_active == False)
    
    mechanics = query.order_by(User.created_at.desc()).all()
    return mechanics

@router.get("/admin/mechanic/{mechanic_id}")
async def get_mechanic_details(
    mechanic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get detailed mechanic information (admin only)"""
    require_admin(current_user)
    
    mechanic = db.query(User).filter(User.id == mechanic_id, User.role == "mechanic").first()
    if not mechanic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mechanic not found"
        )
    
    return mechanic

@router.get("/admin/all-users")
async def get_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    role: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """Get all users with optional role filter (admin only)"""
    require_admin(current_user)
    
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return users

@router.delete("/admin/user/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Delete a user (admin only)"""
    require_admin(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user.full_name} deleted successfully"}


@router.get("/admin/all-vehicles")
async def get_all_vehicles_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """Get all vehicles with comprehensive information (admin only)"""
    require_admin(current_user)
    
    from app.models.vehicle import Vehicle
    
    vehicles = db.query(Vehicle).join(User, Vehicle.owner_id == User.id).offset(skip).limit(limit).all()
    
    result = []
    for vehicle in vehicles:
        owner = db.query(User).filter(User.id == vehicle.owner_id).first()
        
        # Calculate service status
        service_status = "Up to date"
        days_since_service = None
        if vehicle.last_service_date:
            days_since_service = (datetime.now().date() - vehicle.last_service_date).days
            if days_since_service > 180:  # 6 months
                service_status = "Service due"
            elif days_since_service > 365:  # 1 year
                service_status = "Overdue"
        else:
            service_status = "No service record"
        
        # Calculate document status
        documents_status = "Valid"
        if vehicle.insurance_expiry and vehicle.insurance_expiry < datetime.now().date():
            documents_status = "Insurance expired"
        elif vehicle.pollution_expiry and vehicle.pollution_expiry < datetime.now().date():
            documents_status = "Pollution expired"
        elif not vehicle.insurance_expiry or not vehicle.pollution_expiry:
            documents_status = "Documents missing"

        result.append({
            "id": vehicle.id,
            "registration_number": vehicle.registration_number,
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "color": vehicle.color,
            "vehicle_type": vehicle.vehicle_type,
            "fuel_type": vehicle.fuel_type,
            "transmission": vehicle.transmission,
            "vin": vehicle.vin,
            "engine_number": vehicle.engine_number,
            "current_odometer": vehicle.current_odometer,
            "insurance_expiry": vehicle.insurance_expiry,
            "pollution_expiry": vehicle.pollution_expiry,
            "primary_photo_url": vehicle.primary_photo_url,
            "last_service_date": vehicle.last_service_date,
            "last_service_km": vehicle.last_service_km,
            "next_service_date": vehicle.next_service_date,
            "next_service_km": vehicle.next_service_km,
            "qr_code_url": vehicle.qr_code_url,
            "service_status": service_status,
            "days_since_service": days_since_service,
            "documents_status": documents_status,
            "created_at": vehicle.created_at,
            "updated_at": vehicle.updated_at,
            "owner_name": owner.full_name,
            "owner_email": owner.email,
            "owner_phone": owner.phone,
            "owner_id": owner.id
        })
    
    return result


@router.get("/admin/vehicle/{vehicle_id}")
async def get_vehicle_details_admin(
    vehicle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get detailed vehicle information with service history (admin only)"""
    require_admin(current_user)
    
    from app.models.vehicle import Vehicle
    from app.models.service import ServiceRecord
    
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    owner = db.query(User).filter(User.id == vehicle.owner_id).first()
    
    # Get service history
    service_records = db.query(ServiceRecord).filter(
        ServiceRecord.vehicle_id == vehicle_id
    ).order_by(ServiceRecord.service_date.desc()).limit(10).all()
    
    # Calculate comprehensive stats
    total_services = db.query(ServiceRecord).filter(ServiceRecord.vehicle_id == vehicle_id).count()
    total_service_cost = db.query(ServiceRecord).filter(
        ServiceRecord.vehicle_id == vehicle_id,
        ServiceRecord.total_cost.isnot(None)
    ).with_entities(func.sum(ServiceRecord.total_cost)).scalar() or 0
    
    return {
        "vehicle": {
            "id": vehicle.id,
            "registration_number": vehicle.registration_number,
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "color": vehicle.color,
            "vehicle_type": vehicle.vehicle_type,
            "fuel_type": vehicle.fuel_type,
            "transmission": vehicle.transmission,
            "vin": vehicle.vin,
            "engine_number": vehicle.engine_number,
            "current_odometer": vehicle.current_odometer,
            "insurance_expiry": vehicle.insurance_expiry,
            "pollution_expiry": vehicle.pollution_expiry,
            "primary_photo_url": vehicle.primary_photo_url,
            "last_service_date": vehicle.last_service_date,
            "next_service_date": vehicle.next_service_date,
            "qr_code_url": vehicle.qr_code_url,
            "created_at": vehicle.created_at,
            "updated_at": vehicle.updated_at,
        },
        "owner": {
            "id": owner.id,
            "full_name": owner.full_name,
            "email": owner.email,
            "phone": owner.phone,
            "address": owner.address,
            "city": owner.city,
        },
        "service_history": [
            {
                "id": service.id,
                "service_type": service.service_type,
                "description": service.description,
                "service_date": service.service_date,
                "total_cost": service.total_cost,
                "status": service.status,
                "mechanic_id": service.mechanic_id
            } for service in service_records
        ],
        "statistics": {
            "total_services": total_services,
            "total_service_cost": total_service_cost,
            "avg_service_cost": total_service_cost / total_services if total_services > 0 else 0,
            "days_since_last_service": (
                (datetime.now().date() - vehicle.last_service_date).days 
                if vehicle.last_service_date else None
            )
        }
    }


@router.get("/admin/vehicle-statistics")
async def get_vehicle_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get comprehensive vehicle statistics (admin only)"""
    require_admin(current_user)
    
    from app.models.vehicle import Vehicle
    from sqlmodel import func
    
    # Basic counts
    total_vehicles = db.query(Vehicle).count()
    
    # By fuel type
    fuel_stats = db.query(
        Vehicle.fuel_type, func.count(Vehicle.id).label('count')
    ).group_by(Vehicle.fuel_type).all()
    
    # By vehicle type
    type_stats = db.query(
        Vehicle.vehicle_type, func.count(Vehicle.id).label('count')
    ).group_by(Vehicle.vehicle_type).all()
    
    # By year (last 10 years)
    current_year = datetime.now().year
    year_stats = db.query(
        Vehicle.year, func.count(Vehicle.id).label('count')
    ).filter(Vehicle.year >= current_year - 10).group_by(Vehicle.year).order_by(Vehicle.year.desc()).all()
    
    # Service status calculation
    vehicles_with_service = db.query(Vehicle).filter(Vehicle.last_service_date.isnot(None)).all()
    service_due_count = 0
    overdue_count = 0
    up_to_date_count = 0
    
    for vehicle in vehicles_with_service:
        if vehicle.last_service_date:
            days_since = (datetime.now().date() - vehicle.last_service_date).days
            if days_since > 365:
                overdue_count += 1
            elif days_since > 180:
                service_due_count += 1
            else:
                up_to_date_count += 1
    
    no_service_count = total_vehicles - len(vehicles_with_service)
    
    return {
        "total_vehicles": total_vehicles,
        "fuel_distribution": [{"fuel_type": item.fuel_type, "count": item.count} for item in fuel_stats],
        "type_distribution": [{"vehicle_type": item.vehicle_type, "count": item.count} for item in type_stats],
        "year_distribution": [{"year": item.year, "count": item.count} for item in year_stats],
        "service_status": {
            "up_to_date": up_to_date_count,
            "service_due": service_due_count,
            "overdue": overdue_count,
            "no_service_record": no_service_count
        },
        "avg_vehicle_age": current_year - (sum(item.year * item.count for item in year_stats) / sum(item.count for item in year_stats)) if year_stats else 0
    }


@router.get("/admin/enhanced-statistics")
async def get_enhanced_admin_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get comprehensive admin statistics with analytics (admin only)"""
    require_admin(current_user)
    
    from app.models.vehicle import Vehicle
    from app.models.service import ServiceRecord
    from sqlmodel import func
    from datetime import datetime, timedelta
    
    # User statistics
    total_users = db.query(User).count()
    total_owners = db.query(User).filter(User.role == "owner").count()
    total_mechanics = db.query(User).filter(User.role == "mechanic", User.is_approved == True).count()
    pending_mechanics = db.query(User).filter(User.role == "mechanic", User.is_approved == False).count()
    
    # Vehicle statistics
    total_vehicles = db.query(Vehicle).count()
    recent_vehicles = db.query(Vehicle).filter(
        Vehicle.created_at >= datetime.now() - timedelta(days=30)
    ).count()
    
    # Service statistics
    total_services = db.query(ServiceRecord).count()
    pending_services = db.query(ServiceRecord).filter(ServiceRecord.status == "pending_approval").count()
    completed_services = db.query(ServiceRecord).filter(ServiceRecord.status == "approved").count()
    
    # Revenue calculation (from completed services)
    total_revenue = db.query(func.sum(ServiceRecord.final_cost)).filter(
        ServiceRecord.status == "approved",
        ServiceRecord.final_cost.isnot(None)
    ).scalar() or 0
    
    # Recent activity
    recent_services = db.query(ServiceRecord).filter(
        ServiceRecord.created_at >= datetime.now() - timedelta(days=30)
    ).count()
    
    # User registrations by month
    monthly_users = db.query(
        func.extract('month', User.created_at).label('month'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= datetime.now() - timedelta(days=365)
    ).group_by(func.extract('month', User.created_at)).all()
    
    return {
        "users": {
            "total": total_users,
            "owners": total_owners,
            "mechanics": total_mechanics,
            "pending_mechanics": pending_mechanics
        },
        "vehicles": {
            "total": total_vehicles,
            "recent": recent_vehicles
        },
        "services": {
            "total": total_services,
            "completed": completed_services,
            "pending": pending_services,
            "recent": recent_services
        },
        "revenue": {
            "total": float(total_revenue),
            "monthly_avg": float(total_revenue) / 12
        },
        "analytics": {
            "monthly_users": [{
                "month": int(item.month),
                "count": item.count
            } for item in monthly_users]
        }
    }


# Password Reset Endpoints

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: Session = Depends(get_session)
):
    """
    Request password reset - generates a reset token.
    In a production environment, this would send an email with the reset link.
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Generate reset token (expires in 1 hour)
    reset_token = secrets.token_urlsafe(32)
    reset_token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
    
    # Store hashed token and expiry
    user.reset_token_hash = reset_token_hash
    user.reset_token_expires_at = datetime.now() + timedelta(hours=1)
    user.updated_at = datetime.now()
    
    db.add(user)
    db.commit()
    
    # In production, send email with reset link here
    # For now, return the token (REMOVE IN PRODUCTION!)
    return {
        "message": "Password reset token generated",
        "reset_token": reset_token,  # Remove this in production!
        "expires_in": "1 hour",
        "note": "In production, this token would be sent via email"
    }


@router.post("/reset-password")
async def reset_password(
    email: str,
    reset_token: str,
    new_password: str,
    db: Session = Depends(get_session)
):
    """
    Reset password using the reset token
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset request"
        )
    
    # Check if token exists and is not expired
    if not user.reset_token_hash or not user.reset_token_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active password reset request"
        )
    
    if datetime.now() > user.reset_token_expires_at:
        # Clear expired token
        user.reset_token_hash = None
        user.reset_token_expires_at = None
        db.add(user)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Verify token
    provided_token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
    if provided_token_hash != user.reset_token_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    # Validate new password (add your own validation rules)
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Update password and clear reset token
    user.password_hash = get_password_hash(new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    user.updated_at = datetime.now()
    
    db.add(user)
    db.commit()
    
    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Change password for authenticated user
    """
    # Verify current password
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    if new_password == current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(new_password)
    current_user.updated_at = datetime.now()
    
    db.add(current_user)
    db.commit()
    
    return {"message": "Password changed successfully"}
