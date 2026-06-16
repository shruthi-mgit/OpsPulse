import time
import asyncpg

from app.database.connection import get_db_pool

SESSION_TIMEOUT = 1500  # 25 minutes


# =========================================================
# GET SESSION
# =========================================================
async def get_session(user_id, schema_id):

    pool = await get_db_pool()

    async with pool.acquire() as conn:

        query = f"""
            SELECT
                session_id,
                sap_user_name,
                sap_db,
                password,
                expires_at
            FROM "{schema_id}".b1_sessions
            WHERE user_id = $1
              AND schema_id = $2
        """

        session = await conn.fetchrow(
            query,
            user_id,
            schema_id
        )

        # no session
        if not session:
            return None

        # session expired
        current_time = int(time.time())

        if current_time > session["expires_at"]:

            await delete_session(user_id, schema_id)

            return None

        return {
            "session_id": session["session_id"],
            "sap_user_name": session["sap_user_name"],
            "sap_db": session["sap_db"],
            "password": session["password"]
        }


# =========================================================
# SET SESSION
# =========================================================
async def set_session(
    user_id,
    schema_id,
    sap_user_name,
    session_id,
    sap_db,
    password
):

    pool = await get_db_pool()

    async with pool.acquire() as conn:

        expires_at = int(time.time()) + SESSION_TIMEOUT

        query = f"""
            INSERT INTO "{schema_id}".b1_sessions (

                user_id,
                schema_id,
                sap_user_name,
                session_id,
                sap_db,
                password,
                expires_at

            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7
            )

            ON CONFLICT (user_id, schema_id)

            DO UPDATE SET

                sap_user_name = EXCLUDED.sap_user_name,
                session_id = EXCLUDED.session_id,
                sap_db = EXCLUDED.sap_db,
                password = EXCLUDED.password,
                expires_at = EXCLUDED.expires_at,
                updated_at = CURRENT_TIMESTAMP
        """

        await conn.execute(
            query,
            user_id,
            schema_id,
            sap_user_name,
            session_id,
            sap_db,
            password,
            expires_at
        )


# =========================================================
# DELETE SESSION
# =========================================================
async def delete_session(user_id, schema_id):

    pool = await get_db_pool()

    async with pool.acquire() as conn:

        query = f"""
            DELETE FROM "{schema_id}".b1_sessions
            WHERE user_id = $1
              AND schema_id = $2
        """

        await conn.execute(
            query,
            user_id,
            schema_id
        )