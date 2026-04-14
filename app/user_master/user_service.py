import asyncpg
import random
from datetime import datetime, timedelta
from fastapi import HTTPException
import os

from app.auth.security import PasswordEncoder
from app.auth.jwt_utils import JWTUtility
from app.auth.jwt_service import JWTService
from app.user_master.user_repository import TenantUserRepository
from app.user_master.user_repository import UserRepository
from app.user_master.user_email_service import send_user_onboard_email
from app.user_master.user_email_service import send_reset_otp_email


class UserService:

    # ==================================================
    # LOGIN
    # ==================================================

    @staticmethod
    async def login(payload, db_pool):

        email = payload.email.strip()
        password = payload.password.strip()

        if not email or not password:
            raise HTTPException(400, "Email and password required")

        jwt_service = JWTService(db_pool)

        async with db_pool.acquire() as conn:

            # -----------------------------
            # GLOBAL USER FETCH
            # -----------------------------
            global_user = await UserRepository.get_global_user_by_email(
                conn,
                email
            )

            if not global_user:
                raise HTTPException(401, "Invalid credentials")

            # -----------------------------
            # GLOBAL USER ACTIVE CHECK
            # -----------------------------
            if not global_user.get("is_active", True):
                raise HTTPException(403, "User is inactive. Contact admin.")

            # -----------------------------
            # PASSWORD CHECK
            # -----------------------------
            is_match = PasswordEncoder.matches(
                password,
                global_user["password"]
            )

            if not is_match:
                raise HTTPException(401, "Invalid credentials")

            role = global_user["role"]
            schema_id = global_user["schema_id"]

            # ==========================================================
            # SUPER ADMIN LOGIN (NO COMPANY CHECK)
            # ==========================================================
            if role == "SuperAdmin":

                system_schema = "ik_payops_b1"

                token = JWTUtility.generate_token(
                    username=email,
                    user_id=global_user["user_id"],
                    company_schema=system_schema,
                    roles=[role]
                )

                await jwt_service.store_or_update_jwt(
                    user_id=global_user["user_id"],
                    token=token,
                    role=role,
                    schema=system_schema
                )

                return {
                    "message": "Login successful",
                    "status": "success",
                    "token": token,
                    "token_type": "Bearer",
                    "role": role,
                    "schema": system_schema,
                    "global_user_id": global_user["global_user_id"]
                }

            # ==========================================================
            # COMPANY VALIDATION (ONLY FOR TENANT USERS)
            # ==========================================================
            company = await conn.fetchrow("""
                SELECT is_active, is_approved
                FROM ik_payops_b1.ik_onboarding_company
                WHERE schema_id = $1
            """, schema_id)

            if not company:
                raise HTTPException(404, "Company not found")

            if not company["is_approved"]:
                raise HTTPException(403, "Company not approved")

            if not company["is_active"]:
                raise HTTPException(403, "Company is inactive. Contact admin")

            # ==========================================================
            # TENANT USER FETCH
            # ==========================================================
            tenant_user = await UserRepository.get_tenant_user(
                conn,
                schema_id,
                global_user["user_id"]
            )

            if not tenant_user:
                raise HTTPException(401, "Tenant user not found")

            # -----------------------------
            # TENANT USER ACTIVE CHECK
            # -----------------------------
            if not tenant_user.get("is_active", True):
                raise HTTPException(403, "User is inactive in tenant")

            # ==========================================================
            # TOKEN GENERATION
            # ==========================================================
            token = JWTUtility.generate_token(
                username=email,
                user_id=global_user["user_id"],
                company_schema=schema_id,
                roles=[role]
            )

            await jwt_service.store_or_update_jwt(
                user_id=global_user["user_id"],
                token=token,
                role=role,
                schema=schema_id
            )

            # ==========================================================
            # FORCE PASSWORD CHANGE
            # ==========================================================
            if not global_user.get("is_password_changed", True):
                return {
                    "message": "Password change required",
                    "status": "success",
                    "force_password_change": True,
                    "token": token,
                    "role": role,
                    "schema": schema_id,
                    "global_user_id": global_user["global_user_id"]
                }

            # ==========================================================
            # SUCCESS RESPONSE
            # ==========================================================
            return {
                "message": "Login successful",
                "status": "success",
                "token": token,
                "token_type": "Bearer",
                "role": role,
                "schema": schema_id,
                "global_user_id": global_user["global_user_id"]
            }
            
                    
    # ==================================================
    # CHANGE PASSWORD
    # ==================================================

    @staticmethod
    async def change_password(request, data, db_pool):

        claims = getattr(request.state, "user", None)

        if not claims:
            raise HTTPException(401, "Unauthorized")

        tenant_schema = claims.get("company_schema")
        user_id = claims.get("userId")

        if not tenant_schema:
            raise HTTPException(400, "Schema missing in token")

        if not user_id:
            raise HTTPException(400, "User id missing in token")

        async with db_pool.acquire() as conn:

            user = await UserRepository.get_tenant_user_password(
                conn,
                tenant_schema,
                user_id
            )

            if not user:
                raise HTTPException(404, "User not found")

            if not PasswordEncoder.matches(
                data.old_password,
                user["password"]
            ):
                raise HTTPException(401, "Old password incorrect")

            new_hashed = PasswordEncoder.hash_password(data.new_password)

            await UserRepository.update_tenant_password(
                conn,
                tenant_schema,
                user_id,
                new_hashed
            )

            await UserRepository.update_global_password(
                conn,
                user_id,
                new_hashed
            )

        return {"message": "Password changed successfully"}

    # ==================================================
    # LOGOUT
    # ==================================================

    @staticmethod
    async def logout(request, db_pool):

        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(401, "Unauthorized")

        token = auth_header.split(" ")[1]

        user = getattr(request.state, "user", None)

        if not user:
            raise HTTPException(401, "Unauthorized")

        schema = user.get("company_schema")

        jwt_service = JWTService(db_pool)

        await jwt_service.delete_jwt(
            token=token,
            schema=schema
        )

        return {"message": "Logged out successfully"}

    # ==================================================
    # FORGOT PASSWORD
    # ==================================================

    @staticmethod
    async def forgot_password(payload, background_tasks, db_pool):

        email = payload.email

        async with db_pool.acquire() as conn:

            user = await conn.fetchrow("""
                SELECT user_id
                FROM ik_payops_b1.ik_global_users
                WHERE email=$1 AND is_active=TRUE
            """, email)

            if not user:
                return {"message": "If email exists, OTP sent"}

            otp = str(random.randint(100000, 999999))
            expiry = datetime.utcnow() + timedelta(minutes=10)

            await UserRepository.store_reset_otp(
                conn,
                email,
                otp,
                expiry
            )

            background_tasks.add_task(
                send_reset_otp_email,
                email,
                otp
            )

        return {"message": "If email exists, OTP sent"}

    # ==================================================
    # VERIFY OTP RESET
    # ==================================================

    @staticmethod
    async def verify_otp_reset(payload, db_pool):

        email = payload.email
        otp = payload.otp
        new_password = payload.new_password

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                user = await UserRepository.get_user_by_otp(
                    conn,
                    email,
                    otp
                )

                if not user:
                    raise HTTPException(400, "Invalid OTP")


                hashed = PasswordEncoder.hash_password(new_password)

                await UserRepository.update_global_password(
                    conn,
                    user["user_id"],
                    hashed
                )

                await UserRepository.clear_reset_otp(
                    conn,
                    user["user_id"]
                )

                await conn.execute(f"""
                    UPDATE "{user['schema_id']}".ik_users
                    SET password=$1,
                        is_password_changed=TRUE
                    WHERE user_id=$2
                """, hashed, user["user_id"])

        return {"message": "Password reset successful"}
    
    
    @staticmethod
    async def super_admin_reset_password(
        data,
        request,
        db_pool,
    ):

        role = getattr(request.state, "role", "ANONYMOUS")

        if role != "SuperAdmin":
            raise HTTPException(
                403,
                "Only Super Admin can reset password",
            )

        user_id = data.user_id
        new_password = data.new_password

        hashed = PasswordEncoder.hash_password(new_password)

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                # -------------------------
                # get user
                # -------------------------
                user = await UserRepository.get_global_user(
                    conn,
                    user_id,
                )

                if not user:
                    raise HTTPException(
                        404,
                        "User not found",
                    )

                schema_id = user["schema_id"]

                # -------------------------
                # update global
                # -------------------------
                await UserRepository.update_global_password(
                    conn,
                    user_id,
                    hashed,
                )

                # -------------------------
                # update tenant
                # -------------------------
                if schema_id:

                    await UserRepository.update_tenant_password(
                        conn,
                        schema_id,
                        user_id,
                        hashed,
                    )

        return {
            "message": "Password reset successfully",
            "user_id": user_id,
        }

    @staticmethod
    async def update_tenant_user(
        user_id,
        payload,
        request,
        db_pool
    ):

        role = getattr(request.state, "role", None)
        tenant_schema = getattr(request.state, "schema", None)

        if role not in ["Admin", "SuperAdmin"]:
            raise HTTPException(403, "Permission denied")

        # ✅ clean payload
        data_dict = {
            k: v for k, v in payload.dict(exclude_unset=True).items()
            if v is not None
        }

        if not data_dict:
            raise HTTPException(400, "No fields to update")

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                # -----------------------------
                # check user exists
                # -----------------------------
                user = await TenantUserRepository.get_user(
                    conn,
                    tenant_schema,
                    user_id
                )

                if not user:
                    raise HTTPException(404, "User not found")

                # -----------------------------
                # role validation
                # -----------------------------
                if "role" in data_dict:
                    if data_dict["role"] not in ["Admin", "Finance"]:
                        raise HTTPException(400, "Invalid role")

                # -----------------------------
                # branch validation
                # -----------------------------
                if "branch_id" in data_dict:

                    branch = await TenantUserRepository.validate_branch(
                        conn,
                        tenant_schema,
                        data_dict["branch_id"]
                    )

                    if not branch:
                        raise HTTPException(400, "Invalid branch_id")

                # -----------------------------
                # update tenant user
                # -----------------------------
                await TenantUserRepository.update_tenant_user(
                    conn,
                    tenant_schema,
                    user_id,
                    data_dict
                )

                # -----------------------------
                # update global user
                # -----------------------------
                await TenantUserRepository.update_global_user(
                    conn,
                    user_id,
                    data_dict
                )

        return {
            "status": "success",
            "message": "Tenant user updated successfully"
        }




class TenantUserService:

    @staticmethod
    async def create_tenant_user(
        tenant_schema,
        data,
        request,
        background_tasks,
        db_pool,
    ):

        user_claims = getattr(request.state, "user", {})
        token_email = user_claims.get("sub")
        token_schema = user_claims.get("company_schema")
        role = getattr(request.state, "role", "ANONYMOUS")

        if role not in ["Admin", "SuperAdmin"]:
            raise HTTPException(403, "Permission denied")

        if role != "SuperAdmin" and tenant_schema != token_schema:
            raise HTTPException(403, "Cross-tenant access denied")

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                # -----------------------------
                # creator
                # -----------------------------
                creator = await TenantUserRepository.get_creator(
                    conn,
                    token_email,
                )

                if not creator:
                    raise HTTPException(401, "Invalid user")

                created_by = creator["user_id"]
                updated_by = created_by
                # -----------------------------
                # duplicate check
                # -----------------------------
                exists = await TenantUserRepository.check_email_exists(
                    conn,
                    data.email,
                )

                if exists:
                    raise HTTPException(400, "Email already exists") 

                if data.role not in ["Admin", "Finance"]:
                    raise HTTPException(400, "Invalid role")           
                # -----------------------------
                # branch validation
                # -----------------------------

                branch_id = str(data.branch_id).strip()

                branch = await conn.fetchrow(
                    f'''
                    SELECT branch_id
                    FROM "{tenant_schema}".ik_branch
                    WHERE branch_id = $1
                    ''',
                    branch_id
                )

                if not branch:
                    raise HTTPException(400, "Invalid branch_id")
                    
                # create users_seq if not exists
                await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_class
                        WHERE relkind = 'S'
                        AND relname = 'users_seq'
                    ) THEN
                        CREATE SEQUENCE ik_payops_b1.users_seq START 1;
                    END IF;
                END$$;
                """)

                # create global_user_seq if not exists
                await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_class
                        WHERE relkind = 'S'
                        AND relname = 'global_user_seq'
                    ) THEN
                        CREATE SEQUENCE ik_payops_b1.global_user_seq START 1;
                    END IF;
                END$$;
                """)

                user_seq = await conn.fetchval(
                    "SELECT nextval('ik_payops_b1.users_seq')"
                )

                guser_seq = await conn.fetchval(
                    "SELECT nextval('ik_payops_b1.global_user_seq')"
                )

                user_id = f"USERS_{user_seq:014d}"
                global_user_id = f"GUSER_{guser_seq:014d}"
    
                raw_password = data.password
                hashed_password = PasswordEncoder.hash_password(raw_password)

                # -----------------------------
                # insert tenant user
                # -----------------------------
                await conn.execute(
                    f"""
                    INSERT INTO "{tenant_schema}".ik_users
                    (
                        user_id,
                        first_name,
                        last_name,
                        email,
                        role,
                        password,
                        is_active,
                        mobile_number,
                        schema_id,
                        branch,
                        branch_id,
                        created_by,
                        updated_by
                    )
                    VALUES
                    ($1,$2,$3,$4,$5,$6,TRUE,$7,$8,$9,$10,$11,$12)
                    """,
                    user_id,
                    data.first_name,
                    data.last_name,
                    data.email,
                    data.role,
                    hashed_password,
                    data.mobile_number,
                    tenant_schema,
                    data.branch,
                    data.branch_id,
                    created_by,
                    updated_by,
                )

                # -----------------------------
                # insert global user
                # -----------------------------
                await conn.execute(
                    """
                    INSERT INTO ik_payops_b1.ik_global_users
                    (
                        global_user_id,
                        user_id,
                        email,
                        role,
                        password,
                        company_name,
                        mobile_number,
                        schema_id,
                        first_name,
                        last_name,
                        created_by,
                        updated_by
                    )
                    VALUES
                    ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                    """,
                    global_user_id,
                    user_id,
                    data.email,
                    data.role,
                    hashed_password,
                    "Tenant Company",
                    data.mobile_number,
                    tenant_schema,
                    data.first_name,
                    data.last_name,
                    created_by,
                    updated_by,
                )

                # -----------------------------
                # get tenant SMTP config
                # -----------------------------
                config = await conn.fetchrow(
                    """
                    SELECT
                        email_id,
                        email_pwd,
                        smtp_server,
                        smtp_port
                    FROM ik_payops_b1.ik_config
                    WHERE schema_id=$1
                    """,
                    tenant_schema,
                )

                # -----------------------------
                # send email (no password)
                # -----------------------------
                if config:

                    background_tasks.add_task(
                    send_user_onboard_email,
                    data.email,
                    data.first_name,
                    tenant_schema,
                    raw_password,   # ✅ FIX: correct password
                    f"{os.getenv('FRONTEND_URL')}/login",  # ✅ login url
                    config["smtp_server"],
                    config["smtp_port"],
                    config["email_id"],
                    config["email_pwd"],
                    )

        return {
            "message": "Tenant user created successfully",
            "status": "success",
            "tenant_user_id": user_id,
            "global_user_id": global_user_id,
            "password": raw_password
            }



    @staticmethod
    async def get_users_by_schema(schema_id, request, db_pool):

        role = getattr(request.state, "role", "ANONYMOUS")
        user_claims = getattr(request.state, "user", {})

        token_schema = user_claims.get("company_schema")

        if role not in ["SuperAdmin", "Admin"]:
            raise HTTPException(403, "Permission denied")

        if role != "SuperAdmin" and schema_id != token_schema:
            raise HTTPException(403, "Cross tenant access denied")

        async with db_pool.acquire() as conn:

            rows = await TenantUserRepository.get_users_by_schema(
                conn,
                schema_id,
            )

        users = [dict(r) for r in rows]

        return {
            "message": "Users fetched successfully",
            "schema_id": schema_id,
            "count": len(users),
            "users": users
            }      


    