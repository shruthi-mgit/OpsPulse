from fastapi import HTTPException
from app.scheduler.constants import ALLOWED_TYPES
from app.scheduler.log_repository import LogRepository
import logging
from datetime import datetime

logger = logging.getLogger("log-service")


def success_response(data):
    return {
        "status": "success",
        "data": data
    }


class LogService:

    def __init__(self, conn):
        self.repo = LogRepository(conn)
        self.conn = conn   # ✅ needed for fetch queries

    # =========================
    # VALIDATION
    # =========================
    def validate(self, type):

        if type not in ALLOWED_TYPES:
            raise Exception("Invalid type")

    # =========================
    # LOG ERROR (WRITE)
    # =========================
    async def log_error(
        self,
        schema,
        schema_id,
        type,
        msg,
        payload=None
    ):

        self.validate(type)

        await self.repo.insert_error(
            schema,
            schema_id,
            type,
            msg,
            payload
        )


    # =========================
    # LOG SUCCESS (WRITE)
    # =========================
    async def log_success(
        self,
        schema,
        schema_id,
        type,
        msg,
        payload=None
    ):

        self.validate(type)

        await self.repo.insert_success(
            schema,
            schema_id,
            type,
            msg,
            payload
        )


    # =========================
    # GET SUCCESS LOGS (READ)
    # =========================
    async def get_success_logs(
        self,
        schema: str,
        limit: int = 50,
        offset: int = 0,
        type: str = None
    ):
        try:
            query = f"""
                SELECT 
                    success_id,
                    executed_at,
                    type,
                    success_desc,
                    json
                FROM "{schema}".ik_success
            """

            params = []
            param_index = 1

            if type:
                query += f" WHERE type = ${param_index}"
                params.append(type)
                param_index += 1

            query += f"""
                ORDER BY executed_at DESC
                LIMIT ${param_index} OFFSET ${param_index + 1}
            """

            params.extend([limit, offset])

            rows = await self.conn.fetch(query, *params)

            return success_response([dict(r) for r in rows])

        except Exception as e:
            logger.exception("Scheduler jobs failed")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    # =========================
    # GET ERROR LOGS (READ)
    # =========================
    async def get_error_logs(
        self,
        schema: str,
        limit: int = 50,
        offset: int = 0,
        type: str = None
    ):
        try:
            query = f"""
                SELECT 
                    error_id,
                    executed_at,
                    type,
                    error_desc,
                    json
                FROM "{schema}".ik_error
            """

            params = []
            param_index = 1

            if type:
                query += f" WHERE type = ${param_index}"
                params.append(type)
                param_index += 1

            query += f"""
                ORDER BY executed_at DESC
                LIMIT ${param_index} OFFSET ${param_index + 1}
            """

            params.extend([limit, offset])

            rows = await self.conn.fetch(query, *params)

            return success_response([dict(r) for r in rows])

        except Exception as e:
            logger.exception("Scheduler jobs failed")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
    async def get_scheduler_jobs(
        self,
        schema: str,
        job_name: str = None,
        status: str = None,
        from_date: str = None,
        to_date: str = None,
        page: int = 1,
        limit: int = 10
    ):
        try:
            offset = (page - 1) * limit

            # =========================
            # BASE QUERY (UNION BOTH)
            # =========================
            base_query = f"""
                SELECT
                    type AS job_name,
                    last_sync_at AS last_sync,
                    executed_at,
                    success_desc AS message,
                    'Success' AS status
                FROM "{schema}".ik_success
                WHERE type IN (
                    'Branch',
                    'Bank',
                    'GLAccounts',
                    'Warehouse',
                    'Bin',
                    'MerchantID',
                    'Item',
                    'BusinessPartner'
                )

                UNION ALL

                SELECT
                    type AS job_name,
                    NULL AS last_sync,
                    executed_at,
                    error_desc AS message,
                    'Failed' AS status
                FROM "{schema}".ik_error
                WHERE type IN (
                    'Branch',
                    'Bank',
                    'GLAccounts',
                    'Warehouse',
                    'Bin',
                    'MerchantID',
                    'Item',
                    'BusinessPartner'
                )
            """

            conditions = []
            params = []
            idx = 1

            # =========================
            # FILTERS
            # =========================

            if job_name:
                conditions.append(f"job_name = ${idx}")
                params.append(job_name)
                idx += 1

            if status:
                conditions.append(f"status ILIKE ${idx}")
                params.append(status.capitalize())
                idx += 1

            if from_date:
                conditions.append(f"executed_at >= ${idx}")
                params.append(datetime.strptime(from_date, "%Y-%m-%d").date())
                idx += 1
            
            if to_date:
                conditions.append(f"executed_at <= ${idx}")
                params.append(datetime.strptime(to_date, "%Y-%m-%d").date())
                idx += 1
            # =========================
            # FINAL QUERY
            # =========================

            final_query = f"SELECT * FROM ({base_query}) AS latest_logs"

            if conditions:
                final_query += " WHERE " + " AND ".join(conditions)

            final_query += f"""
                ORDER BY executed_at DESC
                LIMIT ${idx} OFFSET ${idx + 1}
            """

            params.extend([limit, offset])

            rows = await self.conn.fetch(final_query, *params)

            return {
                "status": "success",
                "data": [
                    {
                        "job_name": r["job_name"],
                        "last_sync": r["last_sync"],
                        "executed_at": r["executed_at"],
                        "status": r["status"],
                        "message": r["message"],
                        "frequency": "Daily (2:00 AM)"
                    }
                    for r in rows
                ],
                "page": page,
                "limit": limit
            }

        except Exception as e:
            raise HTTPException(400, f"Failed to fetch scheduler jobs: {str(e)}")