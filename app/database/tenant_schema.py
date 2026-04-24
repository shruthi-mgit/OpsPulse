import logging

logger = logging.getLogger("database")


# ==========================================================
# CREATE TENANT SCHEMA + TABLES
# ==========================================================

async def create_tenant_schema(conn, tenant_schema: str):

    # ------------------------------------------------------
    # CREATE SCHEMA
    # ------------------------------------------------------
    await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{tenant_schema}"')

    # ------------------------------------------------------
    # USER SEQUENCE
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".user_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_line_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_acct_line_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_acct_line_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_paymeans_seq START 1;
    ''')

    await conn.execute(f'''
    CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_out_payment_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_out_payment_line_seq START 1;
        ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_out_payment_acct_line_seq START 1;
        ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_out_payment_paymeans_seq START 1;
        ''')
    # ------------------------------------------------------
    # BRANCH TABLE
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_branch (

            branch_id VARCHAR(255) PRIMARY KEY,
            branch_name VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE

        );
    ''')

    # ------------------------------------------------------
    # TENANT USERS
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_users (

            user_id VARCHAR(255) PRIMARY KEY,

            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,

            email VARCHAR(100) NOT NULL,
            role VARCHAR(50),

            password VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,

            mobile_number VARCHAR(20),
            schema_id VARCHAR(255),

            branch VARCHAR(255),
            branch_id VARCHAR(255),

            is_password_changed BOOLEAN DEFAULT FALSE,

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255),

            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(255),

            CONSTRAINT fk_user_branch
                FOREIGN KEY (branch_id)
                REFERENCES "{tenant_schema}".ik_branch(branch_id)

        );
    ''')

    
    # ------------------------------------------------------
    # BUSINESS PARTNER
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_bp (

            bp_id VARCHAR(50) PRIMARY KEY,
            bp_name VARCHAR(255) NOT NULL,
            bp_type VARCHAR(10),

            city VARCHAR(255),
            zipcode VARCHAR(15),
            street_name VARCHAR(255),
            telephone_number VARCHAR(15),

            country VARCHAR(255),
            email VARCHAR(100) NOT NULL,
            mobile_number VARCHAR(13),

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            gst_number VARCHAR(255),
            pan_number VARCHAR(255),

            balance NUMERIC(18,2) DEFAULT 0   -- ✅ added

        );
    ''')

    # ------------------------------------------------------
    # BANK TABLE
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_bank (

            bank_id VARCHAR(255) PRIMARY KEY,
            bank_name VARCHAR(100) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE

        );
    ''')

    # ------------------------------------------------------
    # GL ACCOUNT
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_glaccount (

            account_id VARCHAR(255) PRIMARY KEY,
            account_name VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            balance NUMERIC(18,2) DEFAULT 0

        );
    ''')
    # ------------------------------------------------------
    # JWT TABLE
    # ------------------------------------------------------
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".jwtresponse (

            jwt_id VARCHAR(255) PRIMARY KEY,
            jwt_token VARCHAR(999) NOT NULL,
            user_id VARCHAR(255),
            role VARCHAR(255) NOT NULL
        );
    """)

    # ------------------------------------------------------
    # NOTIFICATION TABLE
    # ------------------------------------------------------
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_notification (

            notification_id VARCHAR(25) PRIMARY KEY,

            from_user_id VARCHAR(255) NOT NULL,

            status VARCHAR(10) NOT NULL,

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(255) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_notification_from_user
                FOREIGN KEY (from_user_id)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_notification_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_notification_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_notification_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id)

        );
    """)

    # ------------------------------------------------------
    # NOTIFICATION LINE TABLE
    # ------------------------------------------------------
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_notification_line (

            notification_line_id VARCHAR(25) PRIMARY KEY,

            notification_id VARCHAR(25) NOT NULL,

            to_user_id VARCHAR(255) NOT NULL,

            message VARCHAR(255),

            status VARCHAR(10) NOT NULL,

            CONSTRAINT fk_notification_line_notification
                FOREIGN KEY (notification_id)
                REFERENCES "{tenant_schema}".ik_notification(notification_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_notification_line_user
                FOREIGN KEY (to_user_id)
                REFERENCES "{tenant_schema}".ik_users(user_id)

        );
    """)

    # ------------------------------------------------------
    # ERROR + SUCCESS LOG TABLES
    # ------------------------------------------------------

    await conn.execute(f"""

        -- =========================
        -- SEQUENCES
        -- =========================
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_error_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_success_seq START 1;

        -- =========================
        -- ERROR TABLE
        -- =========================
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_error (

            error_id VARCHAR(30) PRIMARY KEY,

            schema_id VARCHAR(255) NOT NULL,

            module VARCHAR(100),
            operation VARCHAR(100),
            ref_id VARCHAR(100),

            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            error_desc TEXT,
            success_desc TEXT,

            payload JSONB,

            CONSTRAINT fk_error_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id)

        
        );



        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_success (

            success_id VARCHAR(255) PRIMARY KEY,

            schema_id VARCHAR(255) NOT NULL,

            executed_at DATE NOT NULL,

            type VARCHAR(250) NOT NULL,

            last_sync_at DATE NOT NULL,

            success_desc TEXT,

            CONSTRAINT fk_success_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id)

        );

    """)


    logger.info(f"✅ Tenant schema initialized: {tenant_schema}")

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_header (

            payment_id VARCHAR(25) PRIMARY KEY,

            payment_date DATE DEFAULT CURRENT_DATE,

            customer_id VARCHAR(50),
            customer_name VARCHAR(100),

            payment_type VARCHAR(100),
            remarks TEXT,

            status VARCHAR(25) NOT NULL DEFAULT 'Open',

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(255) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            sap_docentry VARCHAR(25),

            is_payment_onaccount BOOLEAN DEFAULT FALSE,
            payment_on_account DECIMAL(19,6),
            document_total DECIMAL(19,6),

            CONSTRAINT fk_payment_customer
                FOREIGN KEY (customer_id)
                REFERENCES "{tenant_schema}".ik_bp(bp_id),

            CONSTRAINT fk_payment_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id),

            CONSTRAINT fk_payment_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_payment_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id)

        );
    ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_inv_line (

            payment_line_id VARCHAR(25) PRIMARY KEY,

            payment_id VARCHAR(25) NOT NULL,

            doc_type VARCHAR(100),
            doc_entry VARCHAR(25),
            doc_num VARCHAR(25),

            balance_due DECIMAL(19,6),
            total_amount DECIMAL(19,6),
            overdue_days INT,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_inv_payment
                FOREIGN KEY (payment_id)
                REFERENCES "{tenant_schema}".ik_inc_payment_header(payment_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_inv_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id)

        );
    ''')

    await conn.execute(f'''
    CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_acct_line (

        payment_line_id VARCHAR(25) PRIMARY KEY,

        payment_id VARCHAR(25) NOT NULL,

        account_id VARCHAR(255) NOT NULL,
        account_name VARCHAR(100) NOT NULL,

        remarks TEXT,
        total_amount DECIMAL(19,6),

        schema_id VARCHAR(25) NOT NULL,

        CONSTRAINT fk_acct_payment
            FOREIGN KEY (payment_id)
            REFERENCES "{tenant_schema}".ik_inc_payment_header(payment_id)
            ON DELETE CASCADE,

        CONSTRAINT fk_acct_gl
            FOREIGN KEY (account_id)
            REFERENCES "{tenant_schema}".ik_glaccount(account_id),

        CONSTRAINT fk_acct_schema
            FOREIGN KEY (schema_id)
            REFERENCES ik_payops_b1.ik_config(schema_id)

    );
''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_paymeans_line (

            payment_line_id VARCHAR(25) PRIMARY KEY,

            payment_id VARCHAR(25) NOT NULL,

            cheque_account VARCHAR(255),
            cheque_no VARCHAR(100),
            cheque_duedate DATE,
            bank_name VARCHAR(100),
            cheque_amount DECIMAL(19,6),

            cash_account VARCHAR(255),
            cash_amount DECIMAL(19,6),

            bank_account VARCHAR(255),
            transfer_date DATE,
            bank_amount DECIMAL(19,6),

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_paymeans_payment
                FOREIGN KEY (payment_id)
                REFERENCES "{tenant_schema}".ik_inc_payment_header(payment_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_paymeans_cheque
                FOREIGN KEY (cheque_account)
                REFERENCES "{tenant_schema}".ik_glaccount(account_id),

            CONSTRAINT fk_paymeans_cash
                FOREIGN KEY (cash_account)
                REFERENCES "{tenant_schema}".ik_glaccount(account_id),

            CONSTRAINT fk_paymeans_bank
                FOREIGN KEY (bank_account)
                REFERENCES "{tenant_schema}".ik_glaccount(account_id),

            CONSTRAINT fk_paymeans_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id)

        );
        ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_out_payment_header (

            payment_id VARCHAR(25) PRIMARY KEY,

            payment_date DATE DEFAULT CURRENT_DATE,

            vendor_id VARCHAR(50),
            vendor_name VARCHAR(100),

            payment_type VARCHAR(100),
            remarks TEXT,

            status VARCHAR(25) NOT NULL DEFAULT 'Open',

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(255) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            sap_docentry VARCHAR(25),

            is_payment_onaccount BOOLEAN DEFAULT FALSE,
            payment_onaccount DECIMAL(19,6),
            document_total DECIMAL(19,6),

            CONSTRAINT fk_out_vendor
                FOREIGN KEY (vendor_id)
                REFERENCES "{tenant_schema}".ik_bp(bp_id),

            CONSTRAINT fk_out_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id)

        );
        ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_out_payment_inv_line (

            payment_line_id VARCHAR(25) PRIMARY KEY,

            payment_id VARCHAR(25) NOT NULL,

            doc_type VARCHAR(100),
            doc_entry VARCHAR(25),
            doc_num VARCHAR(25),

            balance_due DECIMAL(19,6),
            total_amount DECIMAL(19,6),
            overdue_days INT,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_out_inv_payment
                FOREIGN KEY (payment_id)
                REFERENCES "{tenant_schema}".ik_out_payment_header(payment_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_out_inv_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id)

        );
        ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_out_payment_acct_line (

            payment_line_id VARCHAR(25) PRIMARY KEY,

            payment_id VARCHAR(25) NOT NULL,

            account_id VARCHAR(255) NOT NULL,
            account_name VARCHAR(100) NOT NULL,

            remarks TEXT,
            total_amount DECIMAL(19,6),

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_out_acct_payment
                FOREIGN KEY (payment_id)
                REFERENCES "{tenant_schema}".ik_out_payment_header(payment_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_out_acct_gl
                FOREIGN KEY (account_id)
                REFERENCES "{tenant_schema}".ik_glaccount(account_id),

            CONSTRAINT fk_out_acct_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id)

        );
        ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_out_payment_paymeans_line (

            payment_line_id VARCHAR(25) PRIMARY KEY,

            payment_id VARCHAR(25) NOT NULL,

            cheque_account VARCHAR(255),
            cheque_no VARCHAR(100),
            cheque_duedate DATE,
            bank_name VARCHAR(100),
            cheque_amount DECIMAL(19,6),

            cash_account VARCHAR(255),
            cash_amount DECIMAL(19,6),

            bank_account VARCHAR(255),
            transfer_date DATE,
            bank_amount DECIMAL(19,6),

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_out_paymeans_payment
                FOREIGN KEY (payment_id)
                REFERENCES "{tenant_schema}".ik_out_payment_header(payment_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_out_paymeans_cheque
                FOREIGN KEY (cheque_account)
                REFERENCES "{tenant_schema}".ik_glaccount(account_id),

            CONSTRAINT fk_out_paymeans_cash
                FOREIGN KEY (cash_account)
                REFERENCES "{tenant_schema}".ik_glaccount(account_id),

            CONSTRAINT fk_out_paymeans_bank
                FOREIGN KEY (bank_account)
                REFERENCES "{tenant_schema}".ik_glaccount(account_id),

            CONSTRAINT fk_out_paymeans_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_payops_b1.ik_config(schema_id)

        );
        ''')

    