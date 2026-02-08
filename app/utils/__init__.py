# app/utils/__init__.py
"""
Utility functions for common operations
"""
from .exceptions import (
    raise_not_found,
    raise_forbidden,
    raise_bad_request,
    raise_unauthorized,
    raise_conflict,
    raise_unprocessable,
)
from .db_helpers import (
    get_or_404,
    get_by_field_or_404,
    check_exists,
    ensure_unique,
    get_multi,
)
from .permissions import (
    require_admin,
    require_owner,
    require_mechanic,
    require_mechanic_approved,
    check_vehicle_ownership,
    require_vehicle_access,
    can_edit_service,
    require_service_edit_permission,
)
from .validators import (
    validate_password_strength,
    validate_unique_user_credentials,
    validate_mechanic_credentials,
    validate_unique_vehicle_registration,
    validate_service_status_transition,
)
from .response_helpers import (
    enrich_access_request_response,
    enrich_access_requests_list,
)

__all__ = [
    # Exceptions
    "raise_not_found",
    "raise_forbidden",
    "raise_bad_request",
    "raise_unauthorized",
    "raise_conflict",
    "raise_unprocessable",
    # DB Helpers
    "get_or_404",
    "get_by_field_or_404",
    "check_exists",
    "ensure_unique",
    "get_multi",
    # Permissions
    "require_admin",
    "require_owner",
    "require_mechanic",
    "require_mechanic_approved",
    "check_vehicle_ownership",
    "require_vehicle_access",
    "can_edit_service",
    "require_service_edit_permission",
    # Validators
    "validate_password_strength",
    "validate_unique_user_credentials",
    "validate_mechanic_credentials",
    "validate_unique_vehicle_registration",
    "validate_service_status_transition",
    # Response Helpers
    "enrich_access_request_response",
    "enrich_access_requests_list",
]
