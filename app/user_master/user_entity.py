from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date


class CreateTenantUserRequest(BaseModel):

    first_name: str
    last_name: str
    email: EmailStr
    role: str
    mobile_number: str
    branch: str | None = None
    branch_id: str | None = None
# ==================================================
# LOGIN
# ==================================================

class LoginRequest(BaseModel):
    email: str
    password: str

# ==================================================
# CHANGE PASSWORD
# ==================================================

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ==================================================
# FORGOT PASSWORD
# ==================================================

class ForgotPasswordRequest(BaseModel):
    email: str


# ==================================================
# VERIFY OTP RESET
# ==================================================

class VerifyOtpResetRequest(BaseModel):
    email: str
    otp: str
    new_password: str


# ==================================================
# ADMIN RESET PASSWORD
# ==================================================

class SuperAdminResetPasswordRequest(BaseModel):
    user_id: str
    new_password: str

class UpdateTenantUserRequest(BaseModel):

    first_name: str | None = None
    last_name: str | None = None
    mobile_number: str | None = None
    role: str | None = None
    branch_id: str | None = None
    is_active: bool | None = None
    email: str | None = None
    branch: str | None = None