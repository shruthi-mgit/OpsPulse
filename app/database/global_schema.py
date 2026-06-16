import logging

logger = logging.getLogger("database")

GLOBAL_SCHEMA = "ik_opspulse_b1"


# ==========================================================
# CREATE GLOBAL SCHEMA
# ==========================================================

async def create_global_schema(conn):

    await conn.execute("""
        CREATE SCHEMA IF NOT EXISTS ik_opspulse_b1;
    """)


# ==========================================================
# CREATE GLOBAL SEQUENCES
# ==========================================================

async def create_global_sequences(conn):

    await conn.execute("""

        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.onboarding_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.global_user_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.company_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.user_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.success_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.error_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.vendor_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.jwt_id_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.config_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.notification_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.notification_line_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.ik_error_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.ik_inc_payment_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS ik_opspulse_b1.ik_inc_payment_line_seq START 1;


    """)


# ==========================================================
# GLOBAL USERS TABLE
# ==========================================================

async def create_global_users_table(conn):

    await conn.execute("""

        CREATE TABLE IF NOT EXISTS ik_opspulse_b1.ik_global_users (

            global_user_id VARCHAR(50) PRIMARY KEY,

            user_id VARCHAR(255) NOT NULL UNIQUE,
            email VARCHAR(100) UNIQUE NOT NULL,
            role VARCHAR(100) NOT NULL,
            password VARCHAR(255) NOT NULL,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            token VARCHAR(200),

            company_name VARCHAR(255) NOT NULL,
            mobile_number VARCHAR(15) NOT NULL,

            schema_id VARCHAR(255) NOT NULL,

            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(50) NOT NULL,

            is_password_changed BOOLEAN DEFAULT FALSE

        );

    """)


# ==========================================================
# CONFIG TABLE
# ==========================================================

async def create_config_table(conn):

    await conn.execute("""

        CREATE TABLE IF NOT EXISTS ik_opspulse_b1.ik_config (

            config_id VARCHAR(255) PRIMARY KEY,

            schema_id VARCHAR(255) NOT NULL UNIQUE,

            email_id VARCHAR(100) NOT NULL,
            email_pwd VARCHAR(100) NOT NULL,

            smtp_server VARCHAR(100) NOT NULL,
            smtp_port VARCHAR(4) NOT NULL,

            -- 🔥 NEW SAP FIELDS (ADD THESE)
            base_url VARCHAR(255) NOT NULL,
            sap_username VARCHAR(100) NOT NULL,
            sap_password VARCHAR(100) NOT NULL,
            sap_db VARCHAR(100) NOT NULL,

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(50) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(50) NOT NULL,

            CONSTRAINT fk_config_created_user
                FOREIGN KEY (created_by)
                REFERENCES ik_opspulse_b1.ik_global_users(user_id),

            CONSTRAINT fk_config_updated_user
                FOREIGN KEY (updated_by)
                REFERENCES ik_opspulse_b1.ik_global_users(user_id)

        );

    """)

# ==========================================================
# JWT TABLE
# ==========================================================

async def create_jwt_table(conn):

    await conn.execute("""

        CREATE TABLE IF NOT EXISTS ik_opspulse_b1.jwtresponse (

            jwt_id VARCHAR(255) PRIMARY KEY,
            jwt_token VARCHAR(999) NOT NULL,
            user_id VARCHAR(255),
            role VARCHAR(255) NOT NULL

        );

    """)


# ==========================================================
# ONBOARDING COMPANY TABLE
# ==========================================================

async def create_onboarding_company_table(conn):

    await conn.execute("""

        CREATE TABLE IF NOT EXISTS ik_opspulse_b1.ik_onboarding_company (

            onboard_company_id VARCHAR(50) PRIMARY KEY,

            company_phone_no VARCHAR(15) NOT NULL,
            company_street VARCHAR(255) NOT NULL,
            company_city VARCHAR(255) NOT NULL,
            company_state VARCHAR(255) NOT NULL,
            company_zipcode VARCHAR(6) NOT NULL,
            company_website VARCHAR(255) NOT NULL,
            industry_type VARCHAR(255) NOT NULL,
            headoffice_location VARCHAR(255) NOT NULL,
            company_gst VARCHAR(255) NOT NULL,
            registration_number VARCHAR(255) NOT NULL,

            is_active BOOLEAN DEFAULT FALSE,

            schema_id VARCHAR(255),

            user_name VARCHAR(255) NOT NULL,
            company_name VARCHAR(255) NOT NULL,
            email VARCHAR(100) NOT NULL,
            user_phone_no VARCHAR(15) NOT NULL,

            is_approved BOOLEAN DEFAULT FALSE,

            email_id VARCHAR(100) NOT NULL,
            email_pwd VARCHAR(100) NOT NULL,
            smtp_server VARCHAR(100) NOT NULL,
            smtp_port VARCHAR(4) NOT NULL,

            -- 🔥 NEW SAP FIELDS (ADD THESE)
            base_url VARCHAR(255),
            sap_username VARCHAR(100),
            sap_password VARCHAR(100),
            sap_db VARCHAR(100),

            company_logo TEXT,

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255),

            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(255),

            CONSTRAINT fk_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id),

            CONSTRAINT fk_created_user
                FOREIGN KEY (created_by)
                REFERENCES ik_opspulse_b1.ik_global_users(user_id),

            CONSTRAINT fk_updated_user
                FOREIGN KEY (updated_by)
                REFERENCES ik_opspulse_b1.ik_global_users(user_id)

        );

    """)

# ==========================================================
# INITIALIZE GLOBAL DATABASE
# ==========================================================

async def init_global_database(conn):

    await create_global_schema(conn)
    await create_global_sequences(conn)

    await create_global_users_table(conn)
    await create_config_table(conn)
    await create_jwt_table(conn)
    await create_onboarding_company_table(conn)

    logger.info("✅ Global schema initialized")