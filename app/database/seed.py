import logging
from app.auth.security import PasswordEncoder

logger = logging.getLogger("database")


# ==========================================================
# SEED DEFAULT SUPER ADMIN
# ==========================================================

async def seed_super_admin(conn):

    # --------------------------------------------------
    # Check if super admin already exists
    # --------------------------------------------------
    existing = await conn.fetchrow("""
        SELECT 1
        FROM ik_payops_b1.ik_global_users
        WHERE email = 'prod.admin@ikyam.com'
    """)

    if existing:
        logger.info("✅ Super Admin already exists")
        return

    # --------------------------------------------------
    # Generate password
    # --------------------------------------------------
    hashed_password = PasswordEncoder.encode("Admin@123")

    # --------------------------------------------------
    # Generate IDs
    # --------------------------------------------------
    seq_val = await conn.fetchval(
        "SELECT nextval('ik_payops_b1.global_user_seq')"
    )

    global_id = f"GUSER_{seq_val:014d}"
    super_user_id = f"SUPER_{seq_val:014d}"

    first_name = "Product"
    last_name = "Admin"

    # --------------------------------------------------
    # Insert SUPER_ADMIN into ik_global_users
    # --------------------------------------------------
    await conn.execute("""
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
        (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12
        )
        ON CONFLICT (email) DO NOTHING
    """,
        global_id,
        super_user_id,
        "prod.admin@ikyam.com",
        "SuperAdmin",
        hashed_password,
        "Ikyam Product",
        "8123332485",
        "ik_payops_b1",
        first_name,
        last_name,
        super_user_id,
        super_user_id
    )

    logger.info("✅ Default Super Admin created")