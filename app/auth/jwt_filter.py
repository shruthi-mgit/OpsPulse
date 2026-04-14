"""
JWT Filter — SAFE OPTIONAL AUTH
"""

from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import logging
import jwt

from app.database import get_db_pool
from app.auth.jwt_utils import JWTUtility
from app.auth.jwt_service import JWTService

logger = logging.getLogger("jwt-filter")

# ⭐ allow requests without token
security = HTTPBearer(auto_error=False)


class JWTFilter:

    @staticmethod
    async def verify_token(
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
    ) -> dict:

        # ⭐ No token → treat as anonymous
        if credentials is None:
            return {
                "username": None,
                "user_id": None,
                "company_schema": "ik_payops_b1",
                "role": None,
                "roles": [],
                "token": None,
            }

        try:
            token = credentials.credentials

            claims = JWTUtility.get_all_claims_from_token(token)

            if not claims:
                raise HTTPException(status_code=401, detail="Invalid token")

            role_claim = claims.get("role") or claims.get("roles")

            if isinstance(role_claim, list):
                role = role_claim[0]
                roles = role_claim
            else:
                role = role_claim
                roles = [role_claim] if role_claim else []

            username = claims.get("sub")
            user_id = claims.get("userId")
            company_schema = claims.get("company_schema")

            if not username or not user_id or not company_schema:
                raise HTTPException(status_code=401, detail="Invalid token structure")

            if JWTUtility.is_token_expired(token):
                raise HTTPException(status_code=401, detail="Session Expired")

            db_pool = await get_db_pool()
            jwt_service = JWTService(db_pool)

            user_data = await jwt_service.validate_and_get_user(token, company_schema)

            if not user_data:
                raise HTTPException(status_code=401, detail="Invalid session")

            return {
                "username": username,
                "user_id": user_id,
                "company_schema": company_schema,
                "role": role,
                "roles": roles,
                "token": token,
            }

        except Exception as e:
            logger.error(f"JWT error: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> dict:
    return await JWTFilter.verify_token(credentials)


def require_role(required_roles: List[str]):

    async def role_checker(current_user: dict = Depends(get_current_user)):

        user_roles = current_user.get("roles", [])

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return current_user

    return role_checker