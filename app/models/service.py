# app/models/service.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, date
from enum import Enum
from pydantic import field_validator
import json

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle
    from app.models.user import User

# ===== Enums =====
class ServiceStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class ServiceType(str, Enum):
    REGULAR_SERVICE = "regular_service"
    REPAIR = "repair"
    INSPECTION = "inspection"
    WARRANTY = "warranty"
    EMERGENCY = "emergency"
    CUSTOM = "custom"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    CANCELLED = "cancelled"

# ===== Create / Update Schemas =====
class ServiceRecordCreate(SQLModel):
    vehicle_id: int
    service_type: ServiceType = ServiceType.REGULAR_SERVICE
    description: str
    service_notes: Optional[str] = None
    cost_estimate: Optional[float] = None
    service_date: Optional[date] = None
    mechanic_id: Optional[int] = None

class ServiceRecordUpdate(SQLModel):
    service_type: Optional[ServiceType] = None
    description: Optional[str] = None
    service_notes: Optional[str] = None
    cost_estimate: Optional[float] = None
    final_cost: Optional[float] = None
    payment_status: Optional[PaymentStatus] = None
    status: Optional[ServiceStatus] = None
    service_date: Optional[date] = None
    completion_date: Optional[date] = None

# ===== DB Model =====
class ServiceRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vehicle_id: int = Field(foreign_key="vehicle.id")
    mechanic_id: Optional[int] = Field(default=None, foreign_key="user.id")
    approver_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    service_type: ServiceType = ServiceType.REGULAR_SERVICE
    description: str
    service_notes: Optional[str] = None
    cost_estimate: Optional[float] = None
    final_cost: Optional[float] = None
    payment_status: PaymentStatus = PaymentStatus.PENDING
    status: ServiceStatus = ServiceStatus.DRAFT
    
    service_date: Optional[date] = None
    completion_date: Optional[date] = None
    
    # Voice processing fields
    voice_transcript: Optional[str] = None
    ai_parsed_data: Optional[str] = None
    confidence_score: Optional[float] = None
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None

    # Relationships
    vehicle: "Vehicle" = Relationship(back_populates="service_records")
    mechanic: Optional["User"] = Relationship(
        back_populates="service_records",
        sa_relationship_kwargs={"foreign_keys": "ServiceRecord.mechanic_id"}
    )
    approver: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "ServiceRecord.approver_id"}
    )
    parts_used: List["ServicePart"] = Relationship(back_populates="service")

    # Helpers
    def get_parsed_data(self) -> Optional[Dict]:
        if self.ai_parsed_data:
            return json.loads(self.ai_parsed_data)
        return None

    def set_parsed_data(self, data: Dict):
        self.ai_parsed_data = json.dumps(data)

# ===== Service Parts =====
class ServicePart(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="servicerecord.id")
    part_name: str
    part_number: Optional[str] = None
    quantity: int = 1
    unit_price: float
    total_price: float
    installed_by: Optional[int] = Field(default=None, foreign_key="user.id")
    installation_notes: Optional[str] = None
    warranty_months: Optional[int] = None
    warranty_start_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    service: "ServiceRecord" = Relationship(back_populates="parts_used")
    installer: Optional["User"] = Relationship()
    class Config:
        from_attributes = True