from datetime import datetime


class LogRepository:

    def __init__(self, conn):
        self.conn = conn


    async def generate_error_id(self, schema):

        q = f"""
        SELECT
        'ERROR_' ||
        nextval('{schema}.ik_error_seq')::text
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
        nextval('{schema}.ik_success_seq')::text
        """

        return await self.conn.fetchval(q)

    # =========================
    # INSERT ERROR
    # =========================
    async def insert_error(
        self,
        schema,
        schema_id,
        type,
        msg,
        payload=None
    ):

        import json
        from datetime import datetime

        error_id = await self.generate_error_id(schema)

        await self.conn.execute(f'''
            INSERT INTO "{schema}".ik_error
            (
                error_id,
                schema_id,
                executed_at,
                type,
                error_desc,
                json
            )
            VALUES ($1,$2,$3,$4,$5,$6)
        ''',
            error_id,
            schema_id,
            datetime.now(),
            type,
            msg,
            json.dumps(payload) if payload else None
        )

    # =========================
    # INSERT SUCCESS
    # =========================
    async def insert_success(
        self,
        schema,
        schema_id,
        type,
        msg,
        payload=None
    ):

        import json
        from datetime import datetime

        success_id = await self.generate_success_id(schema)

        await self.conn.execute(f'''
            INSERT INTO "{schema}".ik_success
            (
                success_id,
                schema_id,
                executed_at,
                type,
                last_sync_at,
                success_desc,
                json
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7)
        ''',
            success_id,
            schema_id,
            datetime.now(),
            type,
            datetime.now(),
            msg,
            json.dumps(payload) if payload else None
        )

