class OnboardingRepository:

    # ===============================
    # GET USER BY EMAIL
    # ===============================

    @staticmethod
    async def get_global_user_by_email(conn, email):

        return await conn.fetchrow(
            """
            SELECT user_id
            FROM ik_payops_b1.ik_global_users
            WHERE email=$1
            """,
            email
        )

    # ===============================
    # CHECK EMAIL EXISTS
    # ===============================

    @staticmethod
    async def check_company_email_exists(conn, email):

        return await conn.fetchrow(
            """
            SELECT 1
            FROM ik_payops_b1.ik_onboarding_company
            WHERE email=$1
            """,
            email
        )

    # ===============================
    # NEXT ONBOARD SEQ
    # ===============================

    @staticmethod
    async def get_next_onboarding_seq(conn):

        return await conn.fetchval(
            "SELECT nextval('ik_payops_b1.onboarding_seq')"
        )

    # ===============================
    # INSERT ONBOARD COMPANY
    # ===============================

    @staticmethod
    async def insert_onboarding_company(
        conn,
        data,
        onboard_company_id,
        created_by
    ):

        await conn.execute(
            """
            INSERT INTO ik_payops_b1.ik_onboarding_company
            (
                onboard_company_id,
                company_phone_no,
                company_street,
                company_city,
                company_state,
                company_zipcode,
                company_website,
                industry_type,
                headoffice_location,
                company_gst,
                registration_number,
                user_name,
                company_name,
                email,
                user_phone_no,
                email_id,
                email_pwd,
                smtp_server,
                smtp_port,

                base_url,
                sap_username,
                sap_password,
                sap_db,

                created_by,
                updated_by
            )
            VALUES
            (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
                $11,$12,$13,$14,$15,$16,$17,$18,$19,
                $20,$21,$22,$23,
                $24,$25
            )
            """,

            # ✅ 25 VALUES (IMPORTANT)

            onboard_company_id,
            data.company_phone_no,
            data.company_street,
            data.company_city,
            data.company_state,
            data.company_zipcode,
            data.company_website,
            data.industry_type,
            data.headoffice_location,
            data.company_gst,
            data.registration_number,
            data.user_name,
            data.company_name,
            data.email,
            data.user_phone_no,
            data.email_id,
            data.email_pwd,
            data.smtp_server,
            data.smtp_port,

            data.base_url,
            data.sap_username,
            data.sap_password,
            data.sap_db,

            created_by,
            created_by
        )
    # ===============================
    # INSERT TENANT ADMIN
    # ===============================

    @staticmethod
    async def insert_tenant_admin(
        conn,
        tenant_schema,
        tenant_admin_id,
        first_name,
        last_name,
        email,
        password,
        phone,
        created_by
    ):

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
                mobile_number,
                schema_id,
                created_by,
                updated_by
            )
            VALUES
            ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            """,
            tenant_admin_id,
            first_name,
            last_name,
            email,
            "Admin",
            password,
            phone,
            tenant_schema,
            created_by,
            created_by
        )

    # ===============================
    # INSERT GLOBAL USER
    # ===============================

    @staticmethod
    async def insert_global_user(
        conn,
        global_user_id,
        user_id,
        email,
        role,
        password,
        company_name,
        mobile,
        schema_id,
        first_name,
        last_name,
        created_by
    ):

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
            email,
            role,
            password,
            company_name,
            mobile,
            schema_id,
            first_name,
            last_name,
            created_by,
            created_by
        )

    # ===============================
    # INSERT CONFIG
    # ===============================

    @staticmethod
    async def insert_config(
        conn,
        config_id,
        tenant_schema,
        email_id,
        email_pwd,
        smtp_server,
        smtp_port,
        base_url,
        sap_username,
        sap_password,
        sap_db,
        created_by
    ):

        await conn.execute(
            """
            INSERT INTO ik_payops_b1.ik_config
            (
                config_id,
                schema_id,
                email_id,
                email_pwd,
                smtp_server,
                smtp_port,
                base_url,
                sap_username,
                sap_password,
                sap_db,
                created_by,
                updated_by
            )
            VALUES
            ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            """,
            config_id,
            tenant_schema,
            email_id,
            email_pwd,
            smtp_server,
            smtp_port,
            base_url,
            sap_username,
            sap_password,
            sap_db,
            created_by,
            created_by
        )
    # ===============================
    # ACTIVATE COMPANY
    # ===============================

    @staticmethod
    async def activate_company(
        conn,
        tenant_schema,
        updated_by,
        company_id
    ):

        await conn.execute(
            """
            UPDATE ik_payops_b1.ik_onboarding_company
            SET
                schema_id=$1,
                is_approved=TRUE,
                is_active=TRUE,
                updated_by=$2
            WHERE onboard_company_id=$3
            """,
            tenant_schema,
            updated_by,
            company_id
        )

    # ===============================
    # GET ALL
    # ===============================

    @staticmethod
    async def get_all_companies(conn):

        async with conn.transaction():   # ✅ ADD THIS
            return await conn.fetch(
                """
                SELECT *
                FROM ik_payops_b1.ik_onboarding_company
                ORDER BY created_at DESC
                """
            )

    # ===============================
    # GET BY ID
    # ===============================

    @staticmethod
    async def get_company_by_id(conn, company_id):

        async with conn.transaction():   # ✅ ADD THIS
            return await conn.fetchrow(
                """
                SELECT *
                FROM ik_payops_b1.ik_onboarding_company
                WHERE onboard_company_id=$1
                """,
                company_id
            )
    
    @staticmethod
    async def check_company_exists(conn, onboard_company_id):
        return await conn.fetchrow(
            """
            SELECT 1
            FROM ik_payops_b1.ik_onboarding_company
            WHERE onboard_company_id = $1
            """,
            onboard_company_id
        )

    @staticmethod
    async def update_logo(conn, onboard_company_id, file_bytes):
        await conn.execute(
            """
            UPDATE ik_payops_b1.ik_onboarding_company
            SET company_logo = $1,
                updated_at = NOW()
            WHERE onboard_company_id = $2
            """,
            file_bytes,
            onboard_company_id
        )

    # -------------------------
    # GET LOGO
    # -------------------------
    @staticmethod
    async def get_logo(conn, onboard_company_id):
        return await conn.fetchrow(
            """
            SELECT company_logo
            FROM ik_payops_b1.ik_onboarding_company
            WHERE onboard_company_id = $1
            """,
            onboard_company_id
        )