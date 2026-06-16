"""
Security Configuration — SAFE VERSION (Strict Multi-Tenant JWT)
"""

import bcrypt
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.jwt_utils import JWTUtility

logger = logging.getLogger("security")

SYSTEM_SCHEMA = "ik_opspulse_b1"

# Public but OPTIONAL AUTH endpoints
OPTIONAL_AUTH_ENDPOINTS = {
    "/Opspulseb1/api/add_onboarding_form",
    "/Opspulseb1/api/user_master/forgot-password",
    "/Opspulseb1/api/user_master/verify-otp-reset",
    

}

# Fully public endpoints (no auth processing at all)
PUBLIC_ENDPOINTS = {
    "/Opspulseb1/api/user_master/login-authenticate",
    "/api/onboarding_form/basic_onboarding/company-logo",
    "/Opspulseb1/api/payment/incoming/patch_paymeans_lines_by_payment_id/{payment_id}",
}

PUBLIC_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/Opspulseb1/api/payment/incoming/patch_paymeans_lines_by_payment_id", 
)


# ==========================================================
# CORS
# ==========================================================
def configure_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ==========================================================
# JWT Authentication Middleware
# ==========================================================
class JWTAuthenticationMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        # ✅ FIX CORS PRE-FLIGHT
        if request.method == "OPTIONS":
            return await call_next(request)

        # Always initialize request state
        request.state.role = "ANONYMOUS"
        request.state.schema = SYSTEM_SCHEMA
        request.state.user = None
        request.state.token = None

        path = request.url.path.rstrip("/")

        # ------------------------------------------------------
        # FULLY PUBLIC ROUTES (no token processing)
        # ------------------------------------------------------
        if (
            any(path.startswith(endpoint) for endpoint in PUBLIC_ENDPOINTS)
            or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)
        ):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        # ------------------------------------------------------
        # OPTIONAL AUTH ROUTES
        # ------------------------------------------------------
        if path in OPTIONAL_AUTH_ENDPOINTS:

            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

                try:
                    claims = JWTUtility.get_all_claims_from_token(token)

                    if claims and not JWTUtility.is_token_expired(token):

                        role = self._extract_role(claims)
                        schema = claims.get("company_schema")

                        if role == "SuperAdmin":
                            schema = SYSTEM_SCHEMA

                        request.state.role = role
                        request.state.schema = schema or SYSTEM_SCHEMA
                        request.state.user = claims
                        request.state.token = token

                        logger.info(
                            f"Optional Auth OK | Role={role} | Schema={schema}"
                        )

                except Exception:
                    logger.warning("Optional token invalid")

            return await call_next(request)
        
        # ------------------------------------------------------
        # PROTECTED ROUTES (Token REQUIRED)
        # ------------------------------------------------------
        if not auth_header or not auth_header.startswith("Bearer "):
            return self._unauthorized("Missing token")

        token = auth_header.split(" ")[1]

        try:
            claims = JWTUtility.get_all_claims_from_token(token)

            if not claims:
                return self._unauthorized("Invalid token")

            if JWTUtility.is_token_expired(token):
                return self._unauthorized("Token expired")

            role = self._extract_role(claims)
            schema = claims.get("company_schema")

            if role == "SuperAdmin":
                schema = SYSTEM_SCHEMA

            if role != "SuperAdmin" and not schema:
                return self._unauthorized("Invalid token schema")

            # STRICT TOKEN TRUST (Never trust frontend schema)
            request.state.role = role
            request.state.schema = schema
            request.state.user = claims
            request.state.token = token

            logger.info(
                f"Protected Auth OK | Role={role} | Schema={schema}"
            )

        except Exception:
            logger.exception("JWT middleware failure")
            return self._unauthorized("Authentication failed")

        return await call_next(request)

    # ------------------------------------------------------
    # Extract role safely
    # ------------------------------------------------------
    def _extract_role(self, claims: dict) -> str:

        roles = claims.get("roles")

        if isinstance(roles, list) and roles:
            return roles[0]

        return claims.get("role") or "USER"

    # ------------------------------------------------------
    # Safe 401 response
    # ------------------------------------------------------
    def _unauthorized(self, message: str):
        return JSONResponse(
            status_code=401,
            content={"detail": message}
        )


# ==========================================================
# Password Encoder
# ==========================================================
# ==========================================================
# Password Encoder
# ==========================================================
class PasswordEncoder:

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    @staticmethod
    def matches(plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
            )
        except Exception:
            return False

    # ✅ Optional: backward compatibility (if any old code uses encode)
    @staticmethod
    def encode(password: str) -> str:
        return PasswordEncoder.hash_password(password)

# ==========================================================
# Security Config
# ==========================================================
def configure_security(app: FastAPI):
    configure_cors(app)
    app.add_middleware(JWTAuthenticationMiddleware)
    logger.info("🔒 Security Enabled")