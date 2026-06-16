# app/config/config_service.py

# =====================================
# ❌ OLD (GLOBAL CONFIG - keep if needed)
# =====================================
async def get_sap_config(conn):

    query = """
        SELECT base_url, sap_username, sap_password, sap_db
        FROM ik_opspulse_b1.ik_config
        LIMIT 1
    """

    row = await conn.fetchrow(query)

    if not row:
        raise Exception("SAP Config not found")

    return {
        "base_url": row["base_url"],
        "sap_username": row["sap_username"],
        "sap_password": row["sap_password"],
        "sap_db": row["sap_db"]
    }


# =====================================
# ✅ NEW (MULTI-TENANT CONFIG)
# =====================================
# =====================================
# ✅ NEW (MULTI-TENANT CONFIG)
# =====================================
async def get_sap_config_by_schema(conn, schema_id: str):

    query = """
        SELECT
            schema_id,
            created_by,
            base_url,
            sap_username,
            sap_password,
            sap_db

        FROM ik_opspulse_b1.ik_config

        WHERE schema_id = $1
    """

    row = await conn.fetchrow(query, schema_id)

    if not row:
        raise Exception(f"SAP Config not found for schema: {schema_id}")

    return {

        "user_id": row["created_by"],

        "schema_id": row["schema_id"],

        "base_url": row["base_url"],

        "sap_username": row["sap_username"],

        "sap_password": row["sap_password"],

        "sap_db": row["sap_db"]
    }