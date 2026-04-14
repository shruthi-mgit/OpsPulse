import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("jwt-utils")

# ==========================================================
# JWT Configuration
# ==========================================================

JWT_SECRET = os.getenv("JWT_SECRET", "S4th!Sh.M@!ky4m.c0m")
JWT_ALGORITHM = "HS256"
JWT_TOKEN_VALIDITY_HOURS = 8


class JWTUtility:
    """JWT Utility class for token operations"""

    # ==========================================================
    # TOKEN GENERATION
    # ==========================================================

    @staticmethod
    def generate_token(
        username: str,
        user_id: str,
        company_schema: str,
        roles: List[str],
        company_db: Optional[str] = None
    ) -> str:

        if isinstance(roles, str):
            roles = [roles]

        issued_at = datetime.now(timezone.utc)
        expiration = issued_at + timedelta(hours=JWT_TOKEN_VALIDITY_HOURS)

        payload = {
            "sub": username,
            "userId": user_id,
            "company_schema": company_schema,
            "roles": roles,
            "company_db": company_db,
            "iat": int(issued_at.timestamp()),
            "exp": int(expiration.timestamp())
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        logger.info(
            f"✅ Token generated | User: {username} | Company: {company_schema} | Roles: {roles}"
        )

        return token

    # ==========================================================
    # INTERNAL DECODE HELPER
    # ==========================================================

    @staticmethod
    def _decode_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Invalid token: {e}")
            return None

    # ==========================================================
    # CLAIM EXTRACTORS
    # ==========================================================

    @staticmethod
    def get_username_from_token(token: str) -> Optional[str]:
        payload = JWTUtility._decode_token(token)
        return payload.get("sub") if payload else None

    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[str]:
        payload = JWTUtility._decode_token(token)
        return payload.get("userId") if payload else None

    @staticmethod
    def get_company_schema_from_token(token: str) -> Optional[str]:
        payload = JWTUtility._decode_token(token)
        return payload.get("company_schema") if payload else None

    @staticmethod
    def get_roles_from_token(token: str) -> List[str]:
        payload = JWTUtility._decode_token(token)
        if not payload:
            return []
        roles = payload.get("roles", [])
        return roles if isinstance(roles, list) else [roles]


    @staticmethod
    def get_expiration_date_from_token(token: str) -> Optional[datetime]:
        payload = JWTUtility._decode_token(token)
        if not payload:
            return None

        exp = payload.get("exp")
        if not exp:
            return None

        return datetime.fromtimestamp(exp, tz=timezone.utc)

    # ==========================================================
    # VALIDATION METHODS
    # ==========================================================

    @staticmethod
    def is_token_expired(token: str) -> bool:
        exp_date = JWTUtility.get_expiration_date_from_token(token)
        if not exp_date:
            return True
        return exp_date < datetime.now(timezone.utc)

    @staticmethod
    def validate_token(token: str, username: str) -> bool:
        payload = JWTUtility._decode_token(token)
        if not payload:
            return False

        return (
            payload.get("sub") == username and
            not JWTUtility.is_token_expired(token)
        )

    @staticmethod
    def get_all_claims_from_token(token: str) -> Optional[Dict[str, Any]]:
        return JWTUtility._decode_token(token)