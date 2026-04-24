from datetime import datetime


class LogRepository:

    def __init__(self, conn):
        self.conn = conn


    async def generate_error_id(self, schema):

        q = f"""
        SELECT
        'ERROR_' ||
        LPAD(
            nextval('{schema}.ik_error_seq')::text,
            14,
            '0'
        )
        """

        return await self.conn.fetchval(q)


    # -------------------------
    # SUCCESS ID
    # SUCCS00000000000001
    # -------------------------
    async def generate_success_id(self, schema):

        q = f"""
        SELECT
        'SUCCS_' ||
        LPAD(
            nextval('{schema}.ik_success_seq')::text,
            14,
            '0'
        )
        """

        return await self.conn.fetchval(q)


    # -------------------------
    # INSERT ERROR
    # -------------------------
    async def insert_error(
        self,
        schema,
        schema_id,
        type,
        error_desc,
    ):

        error_id = await self.generate_error_id(schema)

        await self.conn.execute(
            f"""
            INSERT INTO {schema}.ik_error
            (
                error_id,
                schema_id,
                executed_at,
                type,
                error_desc
            )
            VALUES ($1,$2,$3,$4,$5)
            """,
            error_id,
            schema_id,
            datetime.utcnow(),
            type,
            error_desc,
        )


    # -------------------------
    # INSERT SUCCESS
    # -------------------------
    async def insert_success(
        self,
        schema,
        schema_id,
        type,
        success_desc,
    ):

        success_id = await self.generate_success_id(schema)

        await self.conn.execute(
            f"""
            INSERT INTO {schema}.ik_success
            (
                success_id,
                schema_id,
                executed_at,
                type,
                last_sync_at,
                success_desc
            )
            VALUES ($1,$2,$3,$4,$5,$6)
            """,
            success_id,
            schema_id,
            datetime.utcnow(),
            type,
            datetime.utcnow(),
            success_desc,
        )