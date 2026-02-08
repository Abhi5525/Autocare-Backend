# app/utils/response_helpers.py
"""
Response enrichment utilities for adding related data to responses
"""
from sqlmodel import Session
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.vehicle_access import VehicleAccessRequestResponse
from app.models.vehicle_access import VehicleAccessRequest


def enrich_access_request_response(
    db: Session,
    access_request: VehicleAccessRequest
) -> VehicleAccessRequestResponse:
    """
    Enrich access request with mechanic and vehicle information
    
    Args:
        db: Database session
        access_request: VehicleAccessRequest instance
        
    Returns:
        VehicleAccessRequestResponse with enriched data
    """
    response = VehicleAccessRequestResponse.model_validate(access_request)
    
    # Add mechanic info
    mechanic = db.get(User, access_request.mechanic_id)
    if mechanic:
        response.mechanic_name = mechanic.full_name
        response.mechanic_phone = mechanic.phone
        response.workshop_name = mechanic.workshop_name
    
    # Add vehicle info
    vehicle = db.get(Vehicle, access_request.vehicle_id)
    if vehicle:
        response.vehicle_registration = vehicle.registration_number
        response.vehicle_make = vehicle.make
        response.vehicle_model = vehicle.model
    
    return response


def enrich_access_requests_list(
    db: Session,
    access_requests: list[VehicleAccessRequest]
) -> list[VehicleAccessRequestResponse]:
    """
    Enrich multiple access requests with mechanic and vehicle information
    
    Args:
        db: Database session
        access_requests: List of VehicleAccessRequest instances
        
    Returns:
        List of VehicleAccessRequestResponse with enriched data
    """
    return [enrich_access_request_response(db, req) for req in access_requests]
