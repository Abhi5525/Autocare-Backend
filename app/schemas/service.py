# app/schemas/service.py
from pydantic import BaseModel, computed_field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from app.models.service import ServiceStatus, ServiceType, PaymentStatus

# Request schemas
class VoiceProcessingRequest(BaseModel):
    vehicle_registration: str
    transcript: Optional[str] = None
    audio_data: Optional[str] = None  # Base64 encoded audio

class ServicePartCreate(BaseModel):
    part_name: str
    part_number: Optional[str] = None
    quantity: int = 1
    unit_price: float
    total_price: float
    installation_notes: Optional[str] = None
    warranty_months: Optional[int] = None

class ServicePartResponse(BaseModel):
    id: int
    service_id: int
    part_name: str
    part_number: Optional[str] = None
    quantity: int
    unit_price: float
    total_price: float
    installation_notes: Optional[str] = None
    warranty_months: Optional[int] = None
    warranty_start_date: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Response schemas
class ServiceRecordResponse(BaseModel):
    id: int
    vehicle_id: int
    mechanic_id: Optional[int] = None
    approver_id: Optional[int] = None
    service_type: ServiceType
    description: str
    service_notes: Optional[str] = None
    cost_estimate: Optional[float] = None
    final_cost: Optional[float] = None
    payment_status: PaymentStatus
    status: ServiceStatus
    service_date: Optional[date] = None
    completion_date: Optional[date] = None
    voice_transcript: Optional[str] = None
    ai_parsed_data: Optional[str] = None
    confidence_score: Optional[float] = None
    odometer_reading: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None
    parts_used: List[ServicePartResponse] = []

    class Config:
        from_attributes = True
    
    @computed_field
    @property
    def total_cost(self) -> Optional[float]:
        """Calculate total cost including base cost and parts"""
        base_cost = self.final_cost if self.final_cost is not None else (self.cost_estimate or 0)
        parts_cost = sum(part.total_price for part in self.parts_used) if self.parts_used else 0
        total = base_cost + parts_cost
        return round(total, 2) if total > 0 else None

class VoiceProcessingResponse(BaseModel):
    draft_id: int
    transcript: str
    parsed_data: Dict[str, Any]
    confidence_score: float
    message: str
    service_record: ServiceRecordResponse

class ServiceStatsResponse(BaseModel):
    total_services: int
    draft_services: int
    approved_services: int
    completed_services: int
    pending_approval: int
    total_revenue: float
    avg_service_cost: float
    most_common_service_type: str