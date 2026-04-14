"""
Authentication Module
Handles JWT authentication, authorization, and security
"""

from .jwt_entity import JWTResponse, JWTUpdate
from .jwt_filter import get_current_user, require_role
from .jwt_repository import JWTRepository
from .jwt_service import JWTService
from .jwt_utils import JWTUtility
from .security import PasswordEncoder, configure_cors
from .sequence_generator import generate_prefixed_id

__all__ = [
    "JWTResponse",
    "JWTUpdate",
    "get_current_user",
    "require_role",
    "JWTRepository",
    "JWTService",
    "JWTUtility",
    "PasswordEncoder",
    "configure_cors",
    "generate_prefixed_id",
]