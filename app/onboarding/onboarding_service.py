import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.join(os.path.dirname(sys.executable), "_internal")
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_ROOT = r"D:\PayOpsUploads"
os.makedirs(UPLOAD_ROOT, exist_ok=True)
print("UPLOAD ROOT:", UPLOAD_ROOT)

import asyncpg
from fastapi import HTTPException, Request, BackgroundTasks

from app.database import create_tenant_schema
from app.auth.security import PasswordEncoder
from app.onboarding.onboarding_email_service import send_activation_email
from app.onboarding.onboarding_repository import OnboardingRepository
from datetime import datetime
import base64
from app.scheduler.scheduler import trigger_single_tenant_sync


GLOBAL_SCHEMA = "ik_payops_b1"




class OnboardingService:

    # ==================================================
    # COMPANY ONBOARDING
    # ==================================================

    @staticmethod
    async def create_company_onboarding(request, data, background_tasks, db_pool):

        role = getattr(request.state, "role", "ANONYMOUS")
        user_claims = getattr(request.state, "user", None)

        email = data.email

        first_name = data.user_name.split(" ")[0]
        last_name = " ".join(data.user_name.split(" ")[1:]) if len(data.user_name.split(" ")) > 1 else ""

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                created_by = None

                token_email = None
                if user_claims:
                    token_email = user_claims.get("sub")

                if token_email:
                    user_row = await OnboardingRepository.get_global_user_by_email(
                        conn,
                        token_email
                    )

                    if user_row:
                        created_by = user_row["user_id"]

                # -------------------------
                # Check duplicate
                # -------------------------

                exists = await OnboardingRepository.check_company_email_exists(
                    conn,
                    email
                )

                if exists:
                    raise HTTPException(400, "Email already exists")

                
                # -------------------------
                # Company Name Validation
                # -------------------------

                company_name = " ".join(data.company_name.strip().split())

                exact_match = await conn.fetchrow("""
                    SELECT company_name
                    FROM ik_payops_b1.ik_onboarding_company
                    WHERE LOWER(TRIM(company_name)) = LOWER(TRIM($1))
                """, company_name)

                if exact_match:
                    raise HTTPException(400, "Company name already exists")

                

                # -------------------------
                # Generate onboarding id
                # -------------------------

                seq_val = await OnboardingRepository.get_next_onboarding_seq(conn)

                onboard_company_id = f"CMPNY_{seq_val:014d}"

                # -------------------------
                # Insert onboarding
                # -------------------------
                data.company_name = company_name

                await OnboardingRepository.insert_onboarding_company(
                    conn,
                    data,
                    onboard_company_id,
                    created_by
                )

                tenant_schema = None
                tenant_admin_credentials = None

                # ==================================================
                # SUPER ADMIN FLOW
                # ==================================================

                if role == "SuperAdmin" and created_by:

                    tenant_schema = f"ik_po_c{seq_val:05d}"

                    await create_tenant_schema(conn, tenant_schema)

                    default_password = "Companyadmin@123"
                    hashed_password = PasswordEncoder.encode(default_password)

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

                    tenant_admin_id = f"USERS_{user_seq:014d}"
                    global_user_id = f"GUSER_{guser_seq:014d}"

                    # -------------------------
                    # Tenant admin
                    # -------------------------

                    await OnboardingRepository.insert_tenant_admin(
                        conn,
                        tenant_schema,
                        tenant_admin_id,
                        first_name,
                        last_name,
                        email,
                        hashed_password,
                        data.user_phone_no,
                        created_by
                    )

                    # -------------------------
                    # Global user
                    # -------------------------

                    await OnboardingRepository.insert_global_user(
                        conn,
                        global_user_id,
                        tenant_admin_id,
                        email,
                        "Admin",
                        hashed_password,
                        data.company_name,
                        data.user_phone_no,
                        tenant_schema,
                        first_name,
                        last_name,
                        created_by
                    )

                    # -------------------------
                    # Config
                    # -------------------------

                    config_seq = await conn.fetchval(
                        "SELECT nextval('ik_payops_b1.config_seq')"
                    )

                    config_id = f"CONFG_{config_seq:014d}"

                    await OnboardingRepository.insert_config(
                        conn,
                        config_id,
                        tenant_schema,
                        data.email_id,
                        data.email_pwd,
                        data.smtp_server,
                        data.smtp_port,
                        data.base_url,
                        data.sap_username,
                        data.sap_password,
                        data.sap_db,
                        tenant_admin_id
                    )

                    # -------------------------
                    # Activate company
                    # -------------------------

                    await OnboardingRepository.activate_company(
                        conn,
                        tenant_schema,
                        created_by,
                        onboard_company_id
                    )
                    
                    tenant_admin_credentials = {
                        "username": email,
                        "password": default_password,
                    }

                    background_tasks.add_task(
                        send_activation_email,
                        email,
                        data.company_name,
                        tenant_schema,
                        email,
                        default_password,
                    )

                if tenant_schema:
                    background_tasks.add_task(
                        trigger_single_tenant_sync,
                        db_pool,
                        tenant_schema
                    )


        return {
            "message": "Company onboarding completed",
            "status": "success",
            "onboard_company_id": onboard_company_id,
            "tenant_schema": tenant_schema,
            "tenant_admin_credentials": tenant_admin_credentials
            }
    # ==================================================
    # APPROVE COMPANY
    # ==================================================

    @staticmethod
    async def approve_company(onboard_company_id, request, background_tasks, db_pool):

        role = getattr(request.state, "role", "ANONYMOUS")
        user_claims = getattr(request.state, "user", None)

        if role != "SuperAdmin":
            raise HTTPException(403, "Only Super Admin can approve company")

        token_email = None
        if user_claims:
            token_email = user_claims.get("sub")

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                # -------------------------
                # Get approver
                # -------------------------

                user_row = await OnboardingRepository.get_global_user_by_email(
                    conn,
                    token_email
                )

                if not user_row:
                    raise HTTPException(401, "User not found")

                approved_by = user_row["user_id"]

                # -------------------------
                # Get company
                # -------------------------

                company = await OnboardingRepository.get_company_by_id(
                    conn,
                    onboard_company_id
                )

                if not company:
                    raise HTTPException(404, "Company not found")

                if company["is_approved"]:
                    raise HTTPException(400, "Company already approved")

                # -------------------------
                # Names
                # -------------------------

                first_name = company["user_name"].split(" ")[0]
                last_name = " ".join(company["user_name"].split(" ")[1:]) if len(company["user_name"].split(" ")) > 1 else ""

                # -------------------------
                # Generate tenant schema
                # -------------------------

                seq_val = int(onboard_company_id.split("_")[1])

                tenant_schema = f"ik_po_c{seq_val:05d}"

                await create_tenant_schema(conn, tenant_schema)

                # -------------------------
                # Password
                # -------------------------

                default_password = "Companyadmin@123"
                hashed_password = PasswordEncoder.encode(default_password)

                # -------------------------
                # Generate IDs
                # -------------------------
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

                tenant_admin_id = f"USERS_{user_seq:014d}"
                global_user_id = f"GUSER_{guser_seq:014d}"

                # -------------------------
                # Insert tenant admin
                # -------------------------

                await OnboardingRepository.insert_tenant_admin(
                    conn,
                    tenant_schema,
                    tenant_admin_id,
                    first_name,
                    last_name,
                    company["email"],
                    hashed_password,
                    company["user_phone_no"],
                    approved_by
                )

                # -------------------------
                # Insert global user
                # -------------------------

                await OnboardingRepository.insert_global_user(
                    conn,
                    global_user_id,
                    tenant_admin_id,
                    company["email"],
                    "Admin",
                    hashed_password,
                    company["company_name"],
                    company["user_phone_no"],
                    tenant_schema,
                    first_name,
                    last_name,
                    approved_by
                )
                # -------------------------
                # Insert config
                # -------------------------

                config_seq = await conn.fetchval(
                    "SELECT nextval('ik_payops_b1.config_seq')"
                )

                config_id = f"CONFG_{config_seq:014d}"

                await OnboardingRepository.insert_config(
                    conn,
                    config_id,
                    tenant_schema,
                    company["email_id"],
                    company["email_pwd"],
                    company["smtp_server"],
                    company["smtp_port"],
                    company["base_url"],
                    company["sap_username"],
                    company["sap_password"],
                    company["sap_db"],
                    tenant_admin_id
                )

                # -------------------------
                # Activate company
                # -------------------------

                await OnboardingRepository.activate_company(
                    conn,
                    tenant_schema,
                    approved_by,
                    onboard_company_id
                )

                # -------------------------
                # Email
                # -------------------------

                background_tasks.add_task(
                    send_activation_email,
                    company["email"],
                    company["company_name"],
                    tenant_schema,
                    company["email"],
                    default_password
                )
            if tenant_schema:
                background_tasks.add_task(
                    trigger_single_tenant_sync,
                    db_pool,
                    tenant_schema
                )

        return {
            "message": "Company approved successfully",
            "status": "success",
            "tenant_schema": tenant_schema,
            "tenant_admin_credentials": {
                    "username": company["email"],
                    "password": default_password
                }
            }
        
    @staticmethod
    async def get_all_companies(request, db_pool):

        role = getattr(request.state, "role", "ANONYMOUS")

        if role != "SuperAdmin":
            raise HTTPException(
                status_code=403,
                detail="Only Super Admin can view all companies"
            )

        async with db_pool.acquire() as conn:
            rows = await OnboardingRepository.get_all_companies(conn)

        base_url = str(request.base_url).rstrip("/")

        companies = []

        for row in rows:
            data = dict(row)

            logo_path = data.get("company_logo")

            if logo_path and os.path.exists(logo_path):
                try:
                    with open(logo_path, "rb") as f:
                        base64_string = base64.b64encode(f.read()).decode("utf-8")
                        data["logo"] = f"data:image/png;base64,{base64_string}"
                except Exception:
                    data["logo"] = None
            else:
                data["logo"] = None

            companies.append(data)
        return {
            "message": "Companies fetched successfully",
            "data": {
                "total": len(companies),
                "companies": companies
            }
        }


    # ==================================================
    # GET COMPANY BY ID
    # ==================================================
    @staticmethod
    async def get_company_by_id(request, onboard_company_id, db_pool):

        role = getattr(request.state, "role", "ANONYMOUS")

        if role != "SuperAdmin":
            raise HTTPException(
                status_code=403,
                detail="Only Super Admin can view company"
            )

        async with db_pool.acquire() as conn:

            company = await OnboardingRepository.get_company_by_id(
                conn,
                onboard_company_id
            )

            if not company:
                raise HTTPException(404, "Company not found")

        data = dict(company)

        logo_path = data.get("company_logo")

        # ✅ convert file → base64
        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f:
                    base64_string = base64.b64encode(f.read()).decode("utf-8")
                    data["logo"] = f"data:image/png;base64,{base64_string}"
            except Exception:
                data["logo"] = None
        else:
            data["logo"] = None

        return {
            "message": "Company fetched successfully",
            "data": data
        }
    # ==================================================
    # UPDATE COMPANY
    # ==================================================
    @staticmethod
    async def update_company(request, onboard_company_id, data, db_pool):

        role = getattr(request.state, "role", "ANONYMOUS")

        if role != "SuperAdmin":
            raise HTTPException(
                status_code=403,
                detail="Only Super Admin can update company"
            )

        data_dict = {
            k: v for k, v in data.dict(exclude_unset=True).items()
            if v is not None and v != ""
        }

        if not data_dict:
            raise HTTPException(400, "No fields to update")

        update_fields = []
        values = []
        index = 1

        for key, value in data_dict.items():
            update_fields.append(f"{key} = ${index}")
            values.append(value)
            index += 1

        values.append(onboard_company_id)

        query = f"""
            UPDATE ik_payops_b1.ik_onboarding_company
            SET {", ".join(update_fields)},
                updated_at = NOW()
            WHERE onboard_company_id = ${index}
            RETURNING *
        """

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                existing = await conn.fetchrow(
                    """
                    SELECT 1 FROM ik_payops_b1.ik_onboarding_company
                    WHERE onboard_company_id = $1
                    """,
                    onboard_company_id
                )

                if not existing:
                    raise HTTPException(404, "Company not found")

                updated = await conn.fetchrow(query, *values)

        return {
            "message": "Company updated successfully",
            "data": dict(updated)
        }


    # ==================================================
    # UPLOAD LOGO (SAVE FILE + STORE URL)
    # ==================================================
    @staticmethod
    async def upload_logo(onboard_company_id, schema_id, file, db_pool):

        if not onboard_company_id:
            raise HTTPException(400, "onboard_company_id required")

        if not file:
            raise HTTPException(400, "File required")

        # ✅ folder per company
        company_folder = os.path.join(
            UPLOAD_ROOT,
            f"{schema_id}",
            "COMPANY_LOGO"
        )

        os.makedirs(company_folder, exist_ok=True)   # 🔥 AUTO CREATE

        file_extension = ".png" if "png" in file.content_type else ".jpg"
        file_name = f"{onboard_company_id}{file_extension}"

        file_path = os.path.join(company_folder, file_name)

        file_bytes = await file.read()

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # ✅ store path in DB
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ik_payops_b1.ik_onboarding_company
                SET company_logo = $1
                WHERE onboard_company_id = $2
                """,
                file_path,
                onboard_company_id
            )

        return {
            "status": "success",
            "file_path": file_path
        }
    # ==================================================
    # UPDATE LOGO
    # ==================================================
    @staticmethod
    async def update_logo(onboard_company_id, schema_id, file, db_pool):

        if not onboard_company_id:
            raise HTTPException(400, "onboard_company_id required")

        if not file:
            raise HTTPException(400, "File is required")

        if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
            raise HTTPException(400, "Only PNG/JPG images allowed")

        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(400, "Empty file not allowed")

        # ✅ folder per company
        company_folder = os.path.join(
            UPLOAD_ROOT,
            f"{schema_id}",
            "COMPANY_LOGO"
        )

        os.makedirs(company_folder, exist_ok=True)

        file_extension = ".png" if "png" in file.content_type else ".jpg"
        file_name = f"{onboard_company_id}{file_extension}"

        file_path = os.path.join(company_folder, file_name)

        # replace file
        if os.path.exists(file_path):
            os.remove(file_path)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # ✅ store FILE PATH (not URL)
        async with db_pool.acquire() as conn:
            async with conn.transaction():

                existing = await conn.fetchrow(
                    """
                    SELECT company_logo
                    FROM ik_payops_b1.ik_onboarding_company
                    WHERE onboard_company_id = $1
                    """,
                    onboard_company_id
                )

                if not existing:
                    raise HTTPException(404, "Company not found")

                if not existing["company_logo"]:
                    raise HTTPException(
                        400,
                        "No existing logo found. Use upload API first."
                    )

                await conn.execute(
                    """
                    UPDATE ik_payops_b1.ik_onboarding_company
                    SET company_logo = $1,
                        updated_at = NOW()
                    WHERE onboard_company_id = $2
                    """,
                    file_path,
                    onboard_company_id
                )

        return {
            "status": "success",
            "message": "Logo updated successfully",
            "file_path": file_path
        }