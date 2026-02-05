# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from typing import Optional
import os
from PIL import Image
import io
from datetime import datetime

from app.core.database import get_session
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User, UserCreate, UserLogin, Token, TokenWithUser, UserUpdate
from app.dependencies.deps import get_current_user

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
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.phone == user_data.phone)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone already registered"
        )
    
    # Validate mechanic-specific fields
    if user_data.role == "mechanic":
        if not all([user_data.citizen_number, user_data.garage_registration, 
                   user_data.pan_number, user_data.garage_address]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mechanics must provide citizen number, garage registration, PAN number, and garage address"
            )
        
        # Check for duplicate mechanic credentials
        duplicate_mechanic = db.query(User).filter(
            (User.citizen_number == user_data.citizen_number) |
            (User.garage_registration == user_data.garage_registration) |
            (User.pan_number == user_data.pan_number)
        ).first()
        
        if duplicate_mechanic:
            if duplicate_mechanic.citizen_number == user_data.citizen_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This citizen number is already registered"
                )
            elif duplicate_mechanic.garage_registration == user_data.garage_registration:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This garage registration number is already registered"
                )
            elif duplicate_mechanic.pan_number == user_data.pan_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This PAN number is already registered"
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
        # Mechanics need admin approval
        is_active=True if user_data.role != "mechanic" else False,
        is_approved=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Don't create token for inactive mechanics
    if not user.is_active:
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
            detail="Account is inactive"
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
            detail="Account is inactive"
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
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
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
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve mechanics"
        )
    
    mechanic = db.query(User).filter(User.id == mechanic_id).first()
    if not mechanic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mechanic not found"
        )
    
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
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reject mechanics"
        )
    
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
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access statistics"
        )
    
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
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
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
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access mechanic details"
        )
    
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
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access all users"
        )
    
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
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
        )
    
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
