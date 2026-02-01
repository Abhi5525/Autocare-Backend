# app/services/qr_service.py
import qrcode
import os
import uuid
from typing import Optional

class QRService:
    @staticmethod
    def generate_vehicle_qr(vehicle_id: int, registration: str) -> str:
        """Generate QR code for a vehicle"""
        # Data to encode in QR
        qr_data = f"VEHICLE:{vehicle_id}:{registration}"
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to file
        upload_dir = "app/uploads/qr_codes"
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"qr_{vehicle_id}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(upload_dir, filename)
        
        qr_img.save(filepath)
        
        return f"/uploads/qr_codes/{filename}"
    
    @staticmethod
    def parse_qr_data(qr_data: str) -> Optional[dict]:
        """Parse QR code data"""
        try:
            if qr_data.startswith("VEHICLE:"):
                parts = qr_data.split(":")
                if len(parts) == 3:
                    return {
                        "type": "vehicle",
                        "vehicle_id": int(parts[1]),
                        "registration": parts[2]
                    }
        except:
            pass
        return None