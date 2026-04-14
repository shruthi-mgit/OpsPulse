import uuid


class SapNotificationService:

    ALLOWED_STATUS = {"Open", "Close"}

    # ============================
    # NOTIFICATION
    # ============================
    @staticmethod
    async def save_notification(conn, tenant_schema, data):

        notification_id = data.get("notification_id") or str(uuid.uuid4())[:25]

        from_user_id = data.get("from_user_id")
        status = data.get("status")
        created_by = data.get("created_by")
        updated_by = data.get("updated_by")
        schema_id = data.get("schema_id")

        if status not in SapNotificationService.ALLOWED_STATUS:
            raise ValueError("status must be Open or Close")

        # ✅ get user if not provided
        if not from_user_id:

            user = await conn.fetchrow(
                f'SELECT user_id FROM "{tenant_schema}".ik_users LIMIT 1'
            )

            if not user:
                print("No user found", tenant_schema)
                return

            from_user_id = user["user_id"]

        # ✅ fix NOT NULL
        if not created_by:
            created_by = from_user_id

        if not updated_by:
            updated_by = from_user_id

        await conn.execute(
            f"""
            INSERT INTO "{tenant_schema}".ik_notification
            (
                notification_id,
                from_user_id,
                status,
                created_at,
                created_by,
                updated_at,
                updated_by,
                schema_id
            )
            VALUES
            ($1,$2,$3,NOW(),$4,NOW(),$5,$6)
            """,
            notification_id,
            from_user_id,
            status,
            created_by,
            updated_by,
            schema_id,
        )

    # ============================
    # NOTIFICATION LINE
    # ============================
    @staticmethod
    async def save_notification_line(conn, tenant_schema, data):

        notification_line_id = (
            data.get("notification_line_id")
            or str(uuid.uuid4())[:25]
        )

        to_user_id = data.get("to_user_id")

        # get user if not provided
        if not to_user_id:

            user = await conn.fetchrow(
                f'SELECT user_id FROM "{tenant_schema}".ik_users LIMIT 1'
            )

            if not user:
                print("No user found", tenant_schema)
                return

            to_user_id = user["user_id"]

        await conn.execute(
            f"""
            INSERT INTO "{tenant_schema}".ik_notification_line
            (
                notification_line_id,
                notification_id,
                to_user_id,
                message,
                status
            )
            VALUES ($1,$2,$3,$4,$5)
            """,
            notification_line_id,
            data["notification_id"],
            to_user_id,
            data.get("message"),
            data["status"],
        )