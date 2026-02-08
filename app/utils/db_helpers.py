# app/utils/db_helpers.py
"""
Database helper functions for common query patterns
"""
from typing import TypeVar, Type, Any, Optional
from sqlmodel import Session, select
from .exceptions import raise_not_found, raise_bad_request

T = TypeVar('T')


def get_or_404(
    db: Session,
    model: Type[T],
    entity_id: int,
    entity_name: Optional[str] = None
) -> T:
    """
    Get entity by ID or raise 404
    
    Args:
        db: Database session
        model: SQLModel class
        entity_id: ID to lookup
        entity_name: Custom entity name for error message
        
    Returns:
        Entity instance
        
    Raises:
        HTTPException: 404 if not found
    """
    entity = db.get(model, entity_id)
    if not entity:
        name = entity_name or model.__name__
        raise_not_found(name, entity_id)
    return entity


def get_by_field_or_404(
    db: Session,
    model: Type[T],
    field_name: str,
    field_value: Any,
    entity_name: Optional[str] = None
) -> T:
    """
    Get entity by field value or raise 404
    
    Args:
        db: Database session
        model: SQLModel class
        field_name: Field name to filter by
        field_value: Value to match
        entity_name: Custom entity name for error message
        
    Returns:
        Entity instance
        
    Raises:
        HTTPException: 404 if not found
    """
    field = getattr(model, field_name)
    statement = select(model).where(field == field_value)
    entity = db.exec(statement).first()
    
    if not entity:
        name = entity_name or model.__name__
        raise_not_found(name)
    return entity


def check_exists(
    db: Session,
    model: Type[T],
    field_name: str,
    field_value: Any,
    exclude_id: Optional[int] = None
) -> bool:
    """
    Check if entity with field value exists
    
    Args:
        db: Database session
        model: SQLModel class
        field_name: Field name to check
        field_value: Value to match
        exclude_id: Optional ID to exclude from check (for updates)
        
    Returns:
        True if exists, False otherwise
    """
    field = getattr(model, field_name)
    statement = select(model).where(field == field_value)
    
    if exclude_id:
        statement = statement.where(model.id != exclude_id)
    
    return db.exec(statement).first() is not None


def ensure_unique(
    db: Session,
    model: Type[T],
    field_name: str,
    field_value: Any,
    error_message: str,
    exclude_id: Optional[int] = None
):
    """
    Ensure field value is unique or raise 400
    
    Args:
        db: Database session
        model: SQLModel class
        field_name: Field name to check
        field_value: Value to match
        error_message: Error message if not unique
        exclude_id: Optional ID to exclude from check (for updates)
        
    Raises:
        HTTPException: 400 if not unique
    """
    if check_exists(db, model, field_name, field_value, exclude_id):
        raise_bad_request(error_message)


def get_multi(
    db: Session,
    model: Type[T],
    skip: int = 0,
    limit: int = 100
) -> list[T]:
    """
    Get multiple entities with pagination
    
    Args:
        db: Database session
        model: SQLModel class
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of entities
    """
    statement = select(model).offset(skip).limit(limit)
    return list(db.exec(statement).all())
