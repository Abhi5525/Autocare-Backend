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
from app.models.user import User, UserCreate, UserLogin, Token, UserUpdate
from app.dependencies.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_session)
):
    """
    Register a new user
    """
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.phone == user_data.phone)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)

    user = User(
        email=user_data.email,
        phone=user_data.phone,
        full_name=user_data.full_name,
        password_hash=hashed_password,
        is_verified=False,
        role=user_data.role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(data={"user_id": user.id, "role": user.role})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
    )

@router.post("/login", response_model=Token)
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
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
    )

@router.post("/login-json", response_model=Token)
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
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
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
