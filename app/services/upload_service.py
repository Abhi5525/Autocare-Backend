# app/services/upload_service.py
import os
import uuid
from fastapi import UploadFile, HTTPException
from PIL import Image
import io
from typing import Tuple
from app.core.config import settings

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_FILE_SIZE = settings.max_upload_size  # 5MB

class UploadService:
    @staticmethod
    def validate_image(file: UploadFile) -> Tuple[Image.Image, str]:
        """Validate and read image file"""
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Read file content
        contents = file.file.read()
        
        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB"
            )
        
        try:
            # Open and verify image
            image = Image.open(io.BytesIO(contents))
            image.verify()  # Verify it's a valid image
            
            # Reset file pointer
            file.file.seek(0)
            
            # Get image dimensions
            image = Image.open(io.BytesIO(contents))
            
            return image, file_ext
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image file: {str(e)}"
            )
    
    @staticmethod
    def save_image(
        image: Image.Image,
        file_ext: str,
        upload_dir: str,
        max_width: int = 1200,
        max_height: int = 800
    ) -> str:
        """Save image with proper sizing"""
        # Create upload directory if not exists
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"{uuid.uuid4()}{file_ext}"
        filepath = os.path.join(upload_dir, filename)
        
        # Resize image if too large
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save image
        if file_ext in ['.jpg', '.jpeg']:
            image.save(filepath, 'JPEG', quality=85, optimize=True)
        elif file_ext == '.png':
            image.save(filepath, 'PNG', optimize=True)
        elif file_ext == '.webp':
            image.save(filepath, 'WEBP', quality=85)
        
        return filename
    
    @staticmethod
    def get_upload_info(filename: str, upload_type: str) -> dict:
        """Get upload information"""
        base_url = f"/uploads/{upload_type}"
        return {
            "url": f"{base_url}/{filename}",
            "filename": filename
        }

# Create upload directories
UPLOAD_DIRS = {
    "vehicles": "app/uploads/vehicles",
    "profiles": "app/uploads/profiles",
    "service_photos": "app/uploads/service_photos"
}

for dir_path in UPLOAD_DIRS.values():
    os.makedirs(dir_path, exist_ok=True)