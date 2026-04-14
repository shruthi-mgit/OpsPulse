from fastapi import APIRouter, Depends, Request, BackgroundTasks
import asyncpg

from app.database import get_db_pool
from app.user_master.user_entity import (
    LoginRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    VerifyOtpResetRequest,
    SuperAdminResetPasswordRequest,
    CreateTenantUserRequest,
    UpdateTenantUserRequest
)
from app.user_master.user_service import (
    UserService,
    TenantUserService
)

router = APIRouter(
    tags=["User Management"]
)

# ==================================================
# LOGIN
# ==================================================

@router.post("/login-authenticate")
async def login(
    payload: LoginRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):

    return await UserService.login(payload, db_pool)


# ==================================================
# CHANGE PASSWORD
# ==================================================

@router.post("/change-password")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):

    return await UserService.change_password(request, data, db_pool)


# ==================================================
# LOGOUT
# ==================================================

@router.post("/logout")
async def logout(
    request: Request,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):

    return await UserService.logout(request, db_pool)


# ==================================================
# FORGOT PASSWORD
# ==================================================

@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):

    return await UserService.forgot_password(
        payload,
        background_tasks,
        db_pool
    )


# ==================================================
# VERIFY OTP RESET
# ==================================================

@router.post("/verify-otp-reset")
async def verify_otp_reset(
    payload: VerifyOtpResetRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):

    return await UserService.verify_otp_reset(payload, db_pool)


# ==================================================
# ADMIN RESET PASSWORD
# ==================================================

@router.post("/super-admin-reset-password")
async def super_admin_reset_password(
    data: SuperAdminResetPasswordRequest,
    request: Request,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
):

    return await UserService.super_admin_reset_password(
        data,
        request,
        db_pool,
    )

@router.post("/{tenant_schema}/create")
async def create_tenant_user(
        tenant_schema: str,
        data: CreateTenantUserRequest,
        request: Request,
        background_tasks: BackgroundTasks,
        db_pool: asyncpg.Pool = Depends(get_db_pool)
):

    return await TenantUserService.create_tenant_user(
        tenant_schema,
        data,
        request,
        background_tasks,
        db_pool
    )

@router.get("/users/{schema_id}")
async def get_users_by_schema(
    schema_id: str,
    request: Request,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
):

    return await TenantUserService.get_users_by_schema(
        schema_id,
        request,
        db_pool,
    )

@router.patch("/tenant-user/{user_id}")
async def update_tenant_user(
    user_id: str,
    payload: UpdateTenantUserRequest,
    request: Request,
    db_pool = Depends(get_db_pool)
):
    return await UserService.update_tenant_user(
        user_id,
        payload,
        request,
        db_pool
    )

@router.patch("/user/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    request: Request,
    db_pool = Depends(get_db_pool)
):
    return await UserService.update_user_active_status(
        user_id,
        False,
        request,
        db_pool
    )


@router.patch("/user/{user_id}/activate")
async def activate_user(
    user_id: str,
    request: Request,
    db_pool = Depends(get_db_pool)
):
    return await UserService.update_user_active_status(
        user_id,
        True,
        request,
        db_pool
    )