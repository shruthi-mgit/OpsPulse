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
# INVENTORY TRANSFER SEQUENCES
# ------------------------------------------------------

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inventory_transfer_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inventory_transfer_line_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inventory_transfer_serial_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inventory_transfer_batch_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inventory_transfer_request_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inventory_transfer_request_line_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inventory_transfer_request_serial_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_inventory_transfer_request_batch_seq START 1;
    ''')

    await conn.execute(f'''
        CREATE SEQUENCE IF NOT EXISTS
        "{tenant_schema}".ik_merchant_seq
        START 1;
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
            updated_by VARCHAR(255)

        );
    ''')
    
    # ------------------------------------------------------
    # BRANCH TABLE
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_branch (

            branch_id VARCHAR(25) PRIMARY KEY,
            branch_name VARCHAR(255) NOT NULL,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_branch_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_branch_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id)
        );
    ''')

    # ------------------------------------------------------
    # ADD USER BRANCH FK AFTER BOTH TABLES EXIST
    # ------------------------------------------------------

    await conn.execute(f'''
        ALTER TABLE "{tenant_schema}".ik_users
        ADD CONSTRAINT fk_user_branch
        FOREIGN KEY (branch_id)
        REFERENCES "{tenant_schema}".ik_branch(branch_id)
    ''')

    

    # ------------------------------------------------------
    # SAP B1 SESSION TABLE
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".b1_sessions (

            user_id VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            sap_user_name VARCHAR(100) NOT NULL,

            session_id TEXT NOT NULL,

            sap_db VARCHAR(100),

            password VARCHAR(200) NOT NULL,

            expires_at BIGINT NOT NULL,

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT pk_b1_sessions
                PRIMARY KEY (user_id, schema_id),

            CONSTRAINT fk_b1_session_user
                FOREIGN KEY (user_id)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_b1_session_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')
    
    # ------------------------------------------------------
    # BUSINESS PARTNER
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_bp (

            bp_id VARCHAR(50) PRIMARY KEY,

            bp_name VARCHAR(255) NOT NULL,

            bp_type VARCHAR(25) NOT NULL,

            city VARCHAR(255),

            zipcode VARCHAR(25),

            street_name VARCHAR(255),

            telephone_number VARCHAR(25),

            country VARCHAR(100),

            email VARCHAR(100) NOT NULL,

            mobile_number VARCHAR(25),

            balance NUMERIC(19,6) DEFAULT 0,
            debitor_account VARCHAR(50),

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            gst_number VARCHAR(25),

            pan_number VARCHAR(25),

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT chk_bp_type
                CHECK (bp_type IN ('C', 'S')),

            CONSTRAINT fk_bp_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_bp_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_bp_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')
    # ------------------------------------------------------
    # BANK TABLE
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_bank (

            bank_id VARCHAR(25) PRIMARY KEY,
            bank_name VARCHAR(100) NOT NULL,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_bank_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_bank_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_bank_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')

        # ------------------------------------------------------
        # GL ACCOUNT
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_glaccount (

            account_id VARCHAR(25) PRIMARY KEY,

            account_name VARCHAR(100) NOT NULL,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            is_control_act BOOLEAN NOT NULL DEFAULT FALSE,

            is_postable BOOLEAN NOT NULL DEFAULT TRUE,

            is_cash_act BOOLEAN NOT NULL DEFAULT FALSE,

            balance NUMERIC(18,2) DEFAULT 0,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_gl_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_gl_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_gl_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')
   # ------------------------------------------------------
        
    # ------------------------------------------------------
    # WAREHOUSE TABLE
    # ------------------------------------------------------
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_warehouse (

            warehouse_code VARCHAR(50) PRIMARY KEY,

            warehouse_name VARCHAR(100) NOT NULL,

            city VARCHAR(100),
            state VARCHAR(100),
            country VARCHAR(100),

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            branch_id VARCHAR(25) NOT NULL,

            is_bin_activated BOOLEAN NOT NULL DEFAULT FALSE,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_warehouse_branch
                FOREIGN KEY (branch_id)
                REFERENCES "{tenant_schema}".ik_branch(branch_id),

            CONSTRAINT fk_warehouse_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_warehouse_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_warehouse_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_item (

            item_code VARCHAR(50) PRIMARY KEY,

            item_name VARCHAR(100) NOT NULL,

            item_group_code VARCHAR(20),

            inventory_item VARCHAR(10) DEFAULT 'N',
            sales_item VARCHAR(10) DEFAULT 'N',
            purchase_item VARCHAR(10) DEFAULT 'N',

            default_warehouse VARCHAR(50),

            manage_serial VARCHAR(10) DEFAULT 'N',
            manage_batch VARCHAR(10) DEFAULT 'N',

            valid VARCHAR(10) DEFAULT 'Y',

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_item_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_item_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_item_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')
    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_bin (

            bin_id INTEGER PRIMARY KEY,

            bin_code VARCHAR(255) NOT NULL,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            warehouse_code VARCHAR(50) NOT NULL,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_bin_warehouse
                FOREIGN KEY (warehouse_code)
                REFERENCES "{tenant_schema}".ik_warehouse(warehouse_code),

            CONSTRAINT fk_bin_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_bin_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_bin_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

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
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

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

    -- =========================================
    -- SEQUENCES
    -- =========================================

        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_error_seq START 1;

        CREATE SEQUENCE IF NOT EXISTS "{tenant_schema}".ik_success_seq START 1;


        -- =========================================
        -- ERROR TABLE
        -- =========================================

        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_error (

            error_id VARCHAR(255) PRIMARY KEY,

            schema_id VARCHAR(25) NOT NULL,

            executed_at TIMESTAMP NOT NULL DEFAULT NOW(),

            type VARCHAR(250) NOT NULL,

            error_desc TEXT NOT NULL,

            success_desc TEXT,

            json TEXT,

            CONSTRAINT fk_error_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );


        -- =========================================
        -- SUCCESS TABLE
        -- =========================================

        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_success (

            success_id VARCHAR(255) PRIMARY KEY,

            schema_id VARCHAR(25) NOT NULL,

            executed_at TIMESTAMP NOT NULL DEFAULT NOW(),

            type VARCHAR(250) NOT NULL,

            last_sync_at TIMESTAMP NOT NULL DEFAULT NOW(),

            success_desc TEXT,

            json TEXT,

            CONSTRAINT fk_success_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );

    """)

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_header (

            payment_id VARCHAR(25) PRIMARY KEY,

            payment_date DATE NOT NULL DEFAULT CURRENT_DATE,

            series_id INTEGER,

            customer_id VARCHAR(50),

            customer_name VARCHAR(100),

            payment_type VARCHAR(100),

            mode_of_payment VARCHAR(50) NOT NULL,

            remarks VARCHAR(254),

            journal_remarks VARCHAR(254),

            status VARCHAR(25) NOT NULL DEFAULT 'Open',

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            sap_docentry VARCHAR(25),

            sap_docnum VARCHAR(25),

            is_pay_onaccount BOOLEAN NOT NULL DEFAULT FALSE,

            pay_onaccount_amount DECIMAL(19,6) DEFAULT 0,

            document_total DECIMAL(19,6) DEFAULT 0,

            branch VARCHAR(255),

            branch_id VARCHAR(25),

            control_account_id VARCHAR(25),

            sap_status VARCHAR(15) NOT NULL DEFAULT 'Pending',

            CONSTRAINT chk_payment_status
                CHECK (status IN ('Open','Draft','Close','Cancelled')),

            CONSTRAINT chk_sap_status
                CHECK (
                    sap_status IN (
                        'Pending',
                        'Posted',
                        'Failed',
                        'Reversed'
                    )
                ),

            CONSTRAINT fk_inc_payment_customer
                FOREIGN KEY (customer_id)
                REFERENCES "{tenant_schema}".ik_bp(bp_id),

            CONSTRAINT fk_inc_payment_branch
                FOREIGN KEY (branch_id)
                REFERENCES "{tenant_schema}".ik_branch(branch_id),

            CONSTRAINT fk_inc_payment_control_account
                FOREIGN KEY (control_account_id)
                REFERENCES "{tenant_schema}".ik_glaccount(account_id),

            CONSTRAINT fk_inc_payment_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_inc_payment_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_inc_payment_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

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
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

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
            REFERENCES ik_opspulse_b1.ik_config(schema_id)

    );
''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_inc_payment_paymeans_line (

            payment_line_id VARCHAR(25) PRIMARY KEY,

            payment_id VARCHAR(25) NOT NULL,

            cheque_account VARCHAR(25),

            cheque_no VARCHAR(100),

            cheque_duedate DATE,

            bank_name VARCHAR(100),

            cheque_amount DECIMAL(19,6) DEFAULT 0,

            cash_account VARCHAR(25),

            cash_amount DECIMAL(19,6) DEFAULT 0,

            bank_account VARCHAR(25),

            transfer_date DATE,

            bank_amount DECIMAL(19,6) DEFAULT 0,

            schema_id VARCHAR(25) NOT NULL,

            upi_status VARCHAR(20),

            upi_utr VARCHAR(50),

            upi_qr_ref VARCHAR(80),

            merchant_tran_id VARCHAR(35),

            upi_confirmed_at TIMESTAMPTZ,

            upi_retry_count SMALLINT NOT NULL DEFAULT 0,

            CONSTRAINT chk_upi_status
                CHECK (
                    upi_status IS NULL
                    OR upi_status IN (
                        'PENDING',
                        'SUCCESS',
                        'FAILURE',
                        'EXPIRED',
                        'CANCELLED'
                    )
                ),

            CONSTRAINT chk_upi_retry
                CHECK (
                    upi_retry_count >= 0
                    AND upi_retry_count <= 3
                ),

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
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

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
            sap_docnum VARCHAR(25),

            is_payment_onaccount BOOLEAN DEFAULT FALSE,
            payment_onaccount DECIMAL(19,6),
            document_total DECIMAL(19,6),

            branch VARCHAR(255),
            branch_id VARCHAR(25),

            series_id INTEGER,

            journal_remarks VARCHAR(254),

            control_account_id VARCHAR(25),


            sap_status VARCHAR(15) NOT NULL DEFAULT 'Pending',

            CONSTRAINT fk_out_vendor
                FOREIGN KEY (vendor_id)
                REFERENCES "{tenant_schema}".ik_bp(bp_id),

            CONSTRAINT fk_out_branch
                FOREIGN KEY (branch_id)
                REFERENCES "{tenant_schema}".ik_branch(branch_id),

            CONSTRAINT fk_out_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

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
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

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
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

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
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
        ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_itr_header (
            itr_id VARCHAR(25) PRIMARY KEY,
            series_id INTEGER,
            itr_date DATE NOT NULL DEFAULT CURRENT_DATE,
            due_date DATE NOT NULL DEFAULT CURRENT_DATE,
            doc_date DATE NOT NULL DEFAULT CURRENT_DATE,
            branch VARCHAR(255),
            branch_id VARCHAR(25),
            from_wh_code VARCHAR(50) NOT NULL,
            to_wh_code VARCHAR(50) NOT NULL,
            remarks VARCHAR(254),
            journal_remarks VARCHAR(254),
            driver_name VARCHAR(100),
            oil DECIMAL(12,6),
            kilometer DECIMAL(12,6),
            purpose VARCHAR(100),
            sap_docentry VARCHAR(25),
            sap_docnum VARCHAR(25),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_by VARCHAR(25) NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_by VARCHAR(25) NOT NULL,
            schema_id VARCHAR(25) NOT NULL,
            sap_status VARCHAR(15) NOT NULL DEFAULT 'Pending',
            status VARCHAR(25) NOT NULL DEFAULT 'Open',
            CONSTRAINT chk_itr_sap_status
                CHECK (
                    sap_status IN (
                        'Pending',
                        'Posted',
                        'Failed',
                        'Reversed'
                    )
                ),

            CONSTRAINT chk_itr_status
                CHECK (
                    status IN (
                        'Open',
                        'Close'
                    )
                ),

            CONSTRAINT fk_itr_branch
                FOREIGN KEY (branch_id)
                REFERENCES "{tenant_schema}".ik_branch(branch_id),

            CONSTRAINT fk_itr_from_wh
                FOREIGN KEY (from_wh_code)
                REFERENCES "{tenant_schema}".ik_warehouse(warehouse_code),

            CONSTRAINT fk_itr_to_wh
                FOREIGN KEY (to_wh_code)
                REFERENCES "{tenant_schema}".ik_warehouse(warehouse_code),

            CONSTRAINT fk_itr_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_itr_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_itr_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_itr_item_line (

            itr_item_line_id VARCHAR(25) PRIMARY KEY,

            itr_id VARCHAR(25) NOT NULL,

            item_code VARCHAR(50) NOT NULL,

            item_name VARCHAR(100),

            from_wh_code VARCHAR(50) NOT NULL,

            to_wh_code VARCHAR(50) NOT NULL,

            qty DECIMAL(19,6) NOT NULL DEFAULT 0,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            sap_status VARCHAR(15) NOT NULL DEFAULT 'Pending',

            status VARCHAR(25) NOT NULL DEFAULT 'Open',

            CONSTRAINT chk_itr_item_sap_status
                CHECK (
                    sap_status IN (
                        'Pending',
                        'Posted',
                        'Failed',
                        'Reversed'
                    )
                ),

            CONSTRAINT chk_itr_item_status
                CHECK (
                    status IN (
                        'Open',
                        'Close'
                    )
                ),

            CONSTRAINT fk_itr_item_header
                FOREIGN KEY (itr_id)
                REFERENCES "{tenant_schema}".ik_itr_header(itr_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_itr_item_code
                FOREIGN KEY (item_code)
                REFERENCES "{tenant_schema}".ik_item(item_code),

            CONSTRAINT fk_itr_item_from_wh
                FOREIGN KEY (from_wh_code)
                REFERENCES "{tenant_schema}".ik_warehouse(warehouse_code),

            CONSTRAINT fk_itr_item_to_wh
                FOREIGN KEY (to_wh_code)
                REFERENCES "{tenant_schema}".ik_warehouse(warehouse_code),

            CONSTRAINT fk_itr_item_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_itr_item_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_itr_item_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')

    # ======================================================
    # INVENTORY TRANSFER HEADER
    # ======================================================

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_it_header (

            it_id VARCHAR(25) PRIMARY KEY,

            series_id INTEGER,

            it_date DATE NOT NULL DEFAULT CURRENT_DATE,

            due_date DATE NOT NULL DEFAULT CURRENT_DATE,

            doc_date DATE NOT NULL DEFAULT CURRENT_DATE,

            branch VARCHAR(255),

            branch_id VARCHAR(25),

            from_wh_code VARCHAR(50) NOT NULL,

            to_wh_code VARCHAR(50) NOT NULL,

            remarks VARCHAR(254),

            journal_remarks VARCHAR(254),

            driver_name VARCHAR(100),

            oil DECIMAL(12,6),

            kilometer DECIMAL(12,6),

            purpose VARCHAR(100),

            base_id VARCHAR(25),

            base_type VARCHAR(25),

            sap_docentry VARCHAR(25),

            sap_docnum VARCHAR(25),

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            sap_status VARCHAR(15) NOT NULL DEFAULT 'Pending',

            status VARCHAR(25) NOT NULL DEFAULT 'Open',

            CONSTRAINT chk_it_sap_status
                CHECK (
                    sap_status IN (
                        'Pending',
                        'Posted',
                        'Failed',
                        'Reversed'
                    )
                ),

            CONSTRAINT chk_it_status
                CHECK (
                    status IN (
                        'Open',
                        'Close'
                    )
                ),

            CONSTRAINT fk_it_branch
                FOREIGN KEY (branch_id)
                REFERENCES "{tenant_schema}".ik_branch(branch_id),

            CONSTRAINT fk_it_from_wh
                FOREIGN KEY (from_wh_code)
                REFERENCES "{tenant_schema}".ik_warehouse(warehouse_code),

            CONSTRAINT fk_it_to_wh
                FOREIGN KEY (to_wh_code)
                REFERENCES "{tenant_schema}".ik_warehouse(warehouse_code),

            CONSTRAINT fk_it_base_id
                FOREIGN KEY (base_id)
                REFERENCES "{tenant_schema}".ik_itr_header(itr_id),

            CONSTRAINT fk_it_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_it_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_it_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')
    # ======================================================
    # INVENTORY TRANSFER ITEM LINE
    # ======================================================

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_it_item_line (

            it_item_line_id VARCHAR(25) PRIMARY KEY,

            it_id VARCHAR(25) NOT NULL,

            item_code VARCHAR(50) NOT NULL,

            item_name VARCHAR(100),

            from_wh_code VARCHAR(50) NOT NULL,

            to_wh_code VARCHAR(50) NOT NULL,

            qty DECIMAL(19,6) NOT NULL DEFAULT 0,

            manage_serial VARCHAR(10) DEFAULT 'N',

            manage_batch VARCHAR(10) DEFAULT 'N',

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            sap_status VARCHAR(15) NOT NULL DEFAULT 'Pending',

            status VARCHAR(25) NOT NULL DEFAULT 'Open',

            CONSTRAINT chk_it_item_sap_status
                CHECK (
                    sap_status IN (
                        'Pending',
                        'Posted',
                        'Failed',
                        'Reversed'
                    )
                ),

            CONSTRAINT chk_it_item_status
                CHECK (
                    status IN (
                        'Open',
                        'Close'
                    )
                ),

            CONSTRAINT fk_it_item_header
                FOREIGN KEY (it_id)
                REFERENCES "{tenant_schema}".ik_it_header(it_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_it_item_code
                FOREIGN KEY (item_code)
                REFERENCES "{tenant_schema}".ik_item(item_code),

            CONSTRAINT fk_it_item_from_wh
                FOREIGN KEY (from_wh_code)
                REFERENCES "{tenant_schema}".ik_warehouse(warehouse_code),

            CONSTRAINT fk_it_item_to_wh
                FOREIGN KEY (to_wh_code)
                REFERENCES "{tenant_schema}".ik_warehouse(warehouse_code),

            CONSTRAINT fk_it_item_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_it_item_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_it_item_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')

    # ======================================================
    # INVENTORY TRANSFER SERIAL LINE
    # ======================================================

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_it_serial_line (

            it_serial_line_id VARCHAR(25) PRIMARY KEY,

            it_item_line_id VARCHAR(25) NOT NULL,

            it_id VARCHAR(25) NOT NULL,

            item_code VARCHAR(50) NOT NULL,

            internal_serial_number VARCHAR(255) NOT NULL,

            quantity DECIMAL(19,6) NOT NULL DEFAULT 1,

            from_wh_code VARCHAR(50),

            to_wh_code VARCHAR(50),

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_it_serial_item_line
                FOREIGN KEY (it_item_line_id)
                REFERENCES "{tenant_schema}".ik_it_item_line(it_item_line_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_it_serial_header
                FOREIGN KEY (it_id)
                REFERENCES "{tenant_schema}".ik_it_header(it_id)
                ON DELETE CASCADE

        );
    ''')

    # ======================================================
    # INVENTORY TRANSFER BATCH LINE
    # ======================================================

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_it_batch_line (

            it_batch_line_id VARCHAR(25) PRIMARY KEY,

            it_item_line_id VARCHAR(25) NOT NULL,

            it_id VARCHAR(25) NOT NULL,

            item_code VARCHAR(50) NOT NULL,

            batch_number VARCHAR(255) NOT NULL,

            quantity DECIMAL(19,6) NOT NULL DEFAULT 0,

            from_wh_code VARCHAR(50),

            to_wh_code VARCHAR(50),

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_it_batch_item_line
                FOREIGN KEY (it_item_line_id)
                REFERENCES "{tenant_schema}".ik_it_item_line(it_item_line_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_it_batch_header
                FOREIGN KEY (it_id)
                REFERENCES "{tenant_schema}".ik_it_header(it_id)
                ON DELETE CASCADE

        );
    ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_itr_serial_line (

            itr_serial_line_id VARCHAR(25) PRIMARY KEY,

            itr_id VARCHAR(25) NOT NULL,

            itr_item_line_id VARCHAR(25) NOT NULL,

            serial_no VARCHAR(100),

            mnf_serial_no VARCHAR(100),

            qty DECIMAL(19,6),

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_itr_serial_header
                FOREIGN KEY (itr_id)
                REFERENCES "{tenant_schema}".ik_itr_header(itr_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_itr_serial_item
                FOREIGN KEY (itr_item_line_id)
                REFERENCES "{tenant_schema}".ik_itr_item_line(itr_item_line_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_itr_serial_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS "{tenant_schema}".ik_itr_batch_line (

            itr_batch_line_id VARCHAR(25) PRIMARY KEY,

            itr_id VARCHAR(25) NOT NULL,

            itr_item_line_id VARCHAR(25) NOT NULL,

            batch_no VARCHAR(100),

            mnf_date DATE,

            exp_date DATE,

            qty DECIMAL(19,6),

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            CONSTRAINT fk_itr_batch_header
                FOREIGN KEY (itr_id)
                REFERENCES "{tenant_schema}".ik_itr_header(itr_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_itr_batch_item
                FOREIGN KEY (itr_item_line_id)
                REFERENCES "{tenant_schema}".ik_itr_item_line(itr_item_line_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_itr_batch_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')

    await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS
        "{tenant_schema}".ik_merchant_id (

            merchant_id VARCHAR(50) PRIMARY KEY,

            gl_account VARCHAR(25) NOT NULL,

            qr_string_vpa VARCHAR(100) NOT NULL,

            bank_api_key VARCHAR(100) NOT NULL,

            schema_id VARCHAR(25) NOT NULL,

            branch VARCHAR(255),

            branch_id VARCHAR(25),

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),

            created_by VARCHAR(25) NOT NULL,

            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            updated_by VARCHAR(25) NOT NULL,

            CONSTRAINT fk_merchant_gl
                FOREIGN KEY (gl_account)
                REFERENCES "{tenant_schema}".ik_glaccount(account_id),

            CONSTRAINT fk_merchant_branch
                FOREIGN KEY (branch_id)
                REFERENCES "{tenant_schema}".ik_branch(branch_id),

            CONSTRAINT fk_merchant_created_by
                FOREIGN KEY (created_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_merchant_updated_by
                FOREIGN KEY (updated_by)
                REFERENCES "{tenant_schema}".ik_users(user_id),

            CONSTRAINT fk_merchant_schema
                FOREIGN KEY (schema_id)
                REFERENCES ik_opspulse_b1.ik_config(schema_id)

        );
    ''')