# app/utils/exceptions.py
"""
Centralized exception handlers for consistent error responses
"""
from fastapi import HTTPException, status


def raise_not_found(entity_name: str = "Resource", entity_id: int = None):
    """Raise 404 Not Found with consistent message"""
    detail = f"{entity_name} not found"
    if entity_id:
        detail = f"{entity_name} with ID {entity_id} not found"
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail
    )


def raise_forbidden(message: str = "You don't have permission to perform this action"):
    """Raise 403 Forbidden with custom message"""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message
    )


def raise_bad_request(message: str):
    """Raise 400 Bad Request with custom message"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )


def raise_unauthorized(message: str = "Could not validate credentials"):
    """Raise 401 Unauthorized with custom message"""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def raise_conflict(message: str):
    """Raise 409 Conflict with custom message"""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=message
    )


def raise_unprocessable(message: str):
    """Raise 422 Unprocessable Entity with custom message"""
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=message
    )
