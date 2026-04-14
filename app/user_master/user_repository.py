import asyncpg


# ======================================================
# TENANT USER REPOSITORY
# ======================================================

class TenantUserRepository:

    @staticmethod
    async def get_creator(conn, email):

        return await conn.fetchrow(
            """
            SELECT user_id
            FROM ik_payops_b1.ik_global_users
            WHERE email=$1
            """,
            email,
        )

    @staticmethod
    async def get_users_by_schema(conn, schema_id):

        return await conn.fetch(
            f"""
            SELECT
                user_id,
                first_name,
                last_name,
                email,
                role,
                mobile_number,
                branch,
                branch_id,
                is_active,
                created_at
            FROM "{schema_id}".ik_users
            ORDER BY created_at DESC
            """
        )

    @staticmethod
    async def check_email_exists(conn, email):

        return await conn.fetchrow(
            """
            SELECT 1
            FROM ik_payops_b1.ik_global_users
            WHERE email=$1
            """,
            email,
        )
    @staticmethod
    async def get_user(conn, tenant_schema, user_id):

        return await conn.fetchrow(
            f'''
            SELECT user_id
            FROM "{tenant_schema}".ik_users
            WHERE user_id = $1
            ''',
            user_id
        )

    # =========================
    # VALIDATE BRANCH
    # =========================
    @staticmethod
    async def validate_branch(conn, tenant_schema, branch_id):

        return await conn.fetchrow(
            f'''
            SELECT branch_id
            FROM "{tenant_schema}".ik_branch
            WHERE branch_id = $1
            ''',
            branch_id
        )

    # =========================
    # UPDATE TENANT USER
    # =========================
    @staticmethod
    async def update_tenant_user(conn, tenant_schema, user_id, data_dict):

        update_fields = []
        values = []
        index = 1

        for key, value in data_dict.items():
            update_fields.append(f"{key}=${index}")
            values.append(value)
            index += 1

        values.append(user_id)

        query = f"""
            UPDATE "{tenant_schema}".ik_users
            SET {", ".join(update_fields)},
                updated_at = NOW()
            WHERE user_id = ${index}
        """

        await conn.execute(query, *values)

    # =========================
    # UPDATE GLOBAL USER
    # =========================
    @staticmethod
    async def update_global_user(conn, user_id, data_dict):

        allowed_fields = ["first_name", "last_name", "mobile_number", "role"]

        update_fields = []
        values = []
        index = 1

        for key in allowed_fields:
            if key in data_dict:
                update_fields.append(f"{key}=${index}")
                values.append(data_dict[key])
                index += 1

        if not update_fields:
            return

        values.append(user_id)

        query = f"""
            UPDATE ik_payops_b1.ik_global_users
            SET {", ".join(update_fields)},
                updated_at = NOW()
            WHERE user_id = ${index}
        """

        await conn.execute(query, *values)

    @staticmethod
    async def get_user(conn, tenant_schema, user_id):

        return await conn.fetchrow(
            f'''
            SELECT user_id
            FROM "{tenant_schema}".ik_users
            WHERE user_id = $1
            ''',
            user_id
        )

    # =========================
    # UPDATE ACTIVE STATUS (TENANT)
    # =========================
    @staticmethod
    async def update_user_active_status(conn, tenant_schema, user_id, is_active):

        await conn.execute(
            f'''
            UPDATE "{tenant_schema}".ik_users
            SET is_active = $1,
                updated_at = NOW()
            WHERE user_id = $2
            ''',
            is_active,
            user_id
        )

    # =========================
    # UPDATE ACTIVE STATUS (GLOBAL)
    # =========================
    @staticmethod
    async def update_global_user_status(conn, user_id, is_active):

        await conn.execute(
            """
            UPDATE ik_payops_b1.ik_global_users
            SET is_active = $1,
                updated_at = NOW()
            WHERE user_id = $2
            """,
            is_active,
            user_id
        )
# ======================================================
# GLOBAL USER REPOSITORY
# ======================================================

class UserRepository:

    # -----------------------------
    # LOGIN LOOKUP
    # -----------------------------
    @staticmethod
    async def get_global_user_by_email(conn: asyncpg.Connection, email: str):

        return await conn.fetchrow(
            """
            SELECT global_user_id,
                   user_id,
                   password,
                   role,
                   schema_id,
                   is_password_changed,
                   is_active
            FROM ik_payops_b1.ik_global_users
            WHERE LOWER(email) = LOWER($1) AND is_active=TRUE
            """,
            email,
        )

    # -----------------------------
    # GET GLOBAL USER BY ID
    # -----------------------------
    @staticmethod
    async def get_global_user(conn, user_id: str):

        return await conn.fetchrow(
            """
            SELECT user_id, schema_id
            FROM ik_payops_b1.ik_global_users
            WHERE user_id=$1
            """,
            user_id,
        )

    # -----------------------------
    # TENANT USER CHECK
    # -----------------------------
    @staticmethod
    async def get_tenant_user(conn, schema_id, user_id):

        return await conn.fetchrow(
            f"""
            SELECT user_id
            FROM "{schema_id}".ik_users
            WHERE user_id=$1 AND is_active=TRUE
            """,
            user_id,
        )

    # -----------------------------
    # GET TENANT PASSWORD
    # -----------------------------
    @staticmethod
    async def get_tenant_user_password(conn, schema_id, user_id):

        return await conn.fetchrow(
            f"""
            SELECT password
            FROM "{schema_id}".ik_users
            WHERE user_id=$1 AND is_active=TRUE
            """,
            user_id,
        )

    # -----------------------------
    # UPDATE TENANT PASSWORD
    # -----------------------------
    @staticmethod
    async def update_tenant_password(
        conn,
        schema_id,
        user_id,
        password,
    ):

        await conn.execute(
            f"""
            UPDATE "{schema_id}".ik_users
            SET password=$1,
                is_password_changed=TRUE
            WHERE user_id=$2
            """,
            password,
            user_id,
        )

    # -----------------------------
    # UPDATE GLOBAL PASSWORD
    # -----------------------------
    @staticmethod
    async def update_global_password(conn, user_id, password):

        await conn.execute(
            """
            UPDATE ik_payops_b1.ik_global_users
            SET password=$1,
                is_password_changed=TRUE
            WHERE user_id=$2
            """,
            password,
            user_id,
        )

    # -----------------------------
    # STORE RESET OTP
    # -----------------------------
    @staticmethod
    async def store_reset_otp(conn, email, otp, expiry):

        await conn.execute(
            """
            UPDATE ik_payops_b1.ik_global_users
            SET token=$1
            WHERE email=$2
            """,
            otp,
            email,
        )

    # -----------------------------
    # GET USER BY OTP
    # -----------------------------
    @staticmethod
    async def get_user_by_otp(conn, email, otp):

        return await conn.fetchrow(
            """
            SELECT user_id, schema_id
            FROM ik_payops_b1.ik_global_users
            WHERE email=$1 AND token=$2
            """,
            email,
            otp,
        )

    # -----------------------------
    # CLEAR OTP
    # -----------------------------
    @staticmethod
    async def clear_reset_otp(conn, user_id):

        await conn.execute(
            """
            UPDATE ik_payops_b1.ik_global_users
            SET token=NULL
            WHERE user_id=$1
            """,
            user_id,
        )

    # -----------------------------
    # ADMIN FIND USER
    # -----------------------------
    @staticmethod
    async def get_tenant_user_by_email(conn, schema_id, email):

        return await conn.fetchrow(
            f"""
            SELECT user_id
            FROM "{schema_id}".ik_users
            WHERE email=$1 AND is_active=TRUE
            """,
            email,
        )

    # -----------------------------
    # ADMIN RESET PASSWORD
    # -----------------------------
    @staticmethod
    async def admin_update_tenant_password(
        conn,
        schema_id,
        user_id,
        password,
    ):

        await conn.execute(
            f"""
            UPDATE "{schema_id}".ik_users
            SET password=$1,
                is_password_changed=FALSE
            WHERE user_id=$2
            """,
            password,
            user_id,
        )

    @staticmethod
    async def admin_update_global_password(
        conn,
        user_id,
        password,
    ):

        await conn.execute(
            """
            UPDATE ik_payops_b1.ik_global_users
            SET password=$1,
                is_password_changed=FALSE
            WHERE user_id=$2
            """,
            password,
            user_id,
        )

    