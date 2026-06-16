import uuid


class SapUserService:

    ALLOWED_ROLES = {"Admin", "Finance"}

    @staticmethod
    async def save_user(conn, tenant_schema: str, data: dict):

        user_id = data.get("user_id") or str(uuid.uuid4())[:25]

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        role = data.get("role")
        password = data.get("password")

        schema_id = data.get("schema_id")
        created_by = data.get("created_by")
        updated_by = data.get("updated_by")

        branch_id = data.get("branch_id")

        if not first_name:
            raise ValueError("first_name required")

        if not last_name:
            raise ValueError("last_name required")

        if not email:
            raise ValueError("email required")

        if role not in SapUserService.ALLOWED_ROLES:
            raise ValueError("role must be Admin or Finance")

        if not password:
            raise ValueError("password required")

        if not schema_id:
            raise ValueError("schema_id required")

        # -------------------------
        # check branch
        # -------------------------
        if branch_id:

            branch_check = await conn.fetchval(
                f"""
                SELECT 1
                FROM "{tenant_schema}".ik_branch
                WHERE branch_id=$1
                """,
                branch_id,
            )

            if not branch_check:
                raise ValueError("branch not found")

        # -------------------------
        # insert / update
        # -------------------------

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
                is_password_changed,
                created_at,
                created_by,
                updated_at,
                updated_by
            )
            VALUES
            (
                $1,$2,$3,$4,$5,$6,
                TRUE,
                $7,$8,$9,$10,
                FALSE,
                NOW(),$11,NOW(),$12
            )

            ON CONFLICT (user_id)
            DO UPDATE SET

                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                email = EXCLUDED.email,
                role = EXCLUDED.role,
                mobile_number = EXCLUDED.mobile_number,
                branch = EXCLUDED.branch,
                branch_id = EXCLUDED.branch_id,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            user_id,
            first_name,
            last_name,
            email,
            role,
            password,
            data.get("mobile_number"),
            schema_id,
            data.get("branch"),
            branch_id,
            created_by,
            updated_by,
        )