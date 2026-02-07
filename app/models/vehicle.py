# app/models/vehicle.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, date
from enum import Enum
from pydantic import field_validator

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.service import ServiceRecord
    from app.models.vehicle_photo import VehiclePhoto


# ===== Enums =====
class VehicleType(str, Enum):
    CAR = "car"
    BIKE = "bike"
    SCOOTER = "scooter"
    TRUCK = "truck"
    SUV = "suv"
    OTHER = "other"

class FuelType(str, Enum):
    PETROL = "petrol"
    DIESEL = "diesel"
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    CNG = "cng"

class TransmissionType(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    CVT = "cvt"

class ChargingPortType(str, Enum):
    TYPE1 = "type1"
    TYPE2 = "type2"
    CCS = "ccs"
    CHAdeMO = "chademo"
    TESLA = "tesla"

class EmissionStandard(str, Enum):
    BS4 = "bs4"
    BS6 = "bs6"
    EURO4 = "euro4"
    EURO5 = "euro5"
    EURO6 = "euro6"


# ===== Base Schemas =====
class VehicleBase(SQLModel):
    registration_number: str = Field(unique=True, index=True)
    make: str
    model: str
    year: int
    color: str

    vehicle_type: VehicleType = VehicleType.CAR
    fuel_type: FuelType = FuelType.PETROL
    transmission: TransmissionType = TransmissionType.MANUAL

    vin: Optional[str] = None
    engine_number: Optional[str] = None
    
    # Electric Vehicle specific fields
    battery_capacity_kwh: Optional[float] = None  # kWh
    electric_range_km: Optional[int] = None  # Range in km
    charging_port_type: Optional[ChargingPortType] = None
    fast_charging_supported: Optional[bool] = None
    motor_power_kw: Optional[float] = None  # Motor power in kW
    
    # Fuel Vehicle specific fields  
    engine_displacement_cc: Optional[int] = None  # Engine displacement in CC
    fuel_tank_capacity_l: Optional[float] = None  # Fuel tank capacity in liters
    mileage_kmpl: Optional[float] = None  # Mileage in km/liter
    emission_standard: Optional[EmissionStandard] = None

    @field_validator("year")
    def validate_year(cls, v):
        current_year = datetime.now().year
        if v < 1900 or v > current_year + 1:
            raise ValueError("Year must be between 1900 and next year")
        return v


# ===== Pydantic Schemas for API =====
class VehicleCreate(VehicleBase):
    """For creating a new vehicle"""
    current_odometer: Optional[int] = 0  # Initial odometer reading


class VehicleUpdate(SQLModel):
    """For updating vehicle details"""
    color: Optional[str] = None
    current_odometer: Optional[int] = None
    insurance_expiry: Optional[date] = None
    pollution_expiry: Optional[date] = None
    primary_photo_url: Optional[str] = None
    last_service_date: Optional[date] = None
    last_service_km: Optional[int] = None
    next_service_date: Optional[date] = None
    next_service_km: Optional[int] = None
    qr_code_url: Optional[str] = None
    
    # Electric Vehicle updates
    battery_capacity_kwh: Optional[float] = None
    electric_range_km: Optional[int] = None
    charging_port_type: Optional[ChargingPortType] = None
    fast_charging_supported: Optional[bool] = None
    motor_power_kw: Optional[float] = None
    
    # Fuel Vehicle updates
    engine_displacement_cc: Optional[int] = None
    fuel_tank_capacity_l: Optional[float] = None
    mileage_kmpl: Optional[float] = None
    emission_standard: Optional[EmissionStandard] = None


# ===== DB Model =====
class Vehicle(VehicleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign key
    owner_id: int = Field(foreign_key="user.id")

    # Odometer tracking
    current_odometer: int = 0

    # Document dates
    insurance_expiry: Optional[date] = None
    pollution_expiry: Optional[date] = None

    # Photos
    primary_photo_url: Optional[str] = None

    # Service tracking
    last_service_date: Optional[date] = None
    last_service_km: Optional[int] = None
    next_service_date: Optional[date] = None
    next_service_km: Optional[int] = None

    # QR Code
    qr_code_url: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    owner: "User" = Relationship(back_populates="vehicles")
    service_records: List["ServiceRecord"] = Relationship(back_populates="vehicle")
    photos: List["VehiclePhoto"] = Relationship(back_populates="vehicle")


# Optional: Response Model (for API)
class VehicleResponse(VehicleBase):
    id: int
    owner_id: int
    current_odometer: int
    insurance_expiry: Optional[date]
    pollution_expiry: Optional[date]
    primary_photo_url: Optional[str]
    last_service_date: Optional[date]
    last_service_km: Optional[int]
    next_service_date: Optional[date]
    next_service_km: Optional[int]
    qr_code_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Electric Vehicle fields
    battery_capacity_kwh: Optional[float]
    electric_range_km: Optional[int]
    charging_port_type: Optional[ChargingPortType]
    fast_charging_supported: Optional[bool]
    motor_power_kw: Optional[float]
    
    # Fuel Vehicle fields
    engine_displacement_cc: Optional[int]
    fuel_tank_capacity_l: Optional[float]
    mileage_kmpl: Optional[float]
    emission_standard: Optional[EmissionStandard]

    class Config:
        from_attributes = True
