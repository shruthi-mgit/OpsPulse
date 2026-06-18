from fastapi import APIRouter, Depends, HTTPException, Request
from app.database import get_db_pool
from app.auth.jwt_filter import get_current_user
from app.scheduler.log_service import LogService


router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/success")
async def get_success_logs(
    limit: int = 50,
    offset: int = 0,
    type: str = None,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
):
    role = current_user.get("role")

    # 🔴 ONLY ADMIN
    if role != "Finance":
        raise HTTPException(403, "Only Admin can view logs")

    async with pool.acquire() as conn:
        tenant_schema = current_user.get("company_schema")
        service = LogService(conn)

        return await service.get_success_logs(
            tenant_schema,
            limit,
            offset,
            type
        )


@router.get("/error")
async def get_error_logs(
    limit: int = 50,
    offset: int = 0,
    type: str = None,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
):
    role = current_user.get("role")

    
    if role != "Finance":
        raise HTTPException(403, "Only Admin can view logs")

    async with pool.acquire() as conn:
        tenant_schema = current_user.get("company_schema")
        service = LogService(conn)

        return await service.get_error_logs(
            tenant_schema,
            limit,
            offset,
            type
        )

@router.get("/scheduler/jobs")
async def get_scheduler_jobs(
    request: Request,
    jobName: str = None,
    status: str = None,
    from_date: str = None,
    to_date: str = None,
    page: int = 1,
    limit: int = 10,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "Admin":
        raise HTTPException(403, "Only Admin can view scheduler jobs")

    schema = current_user.get("company_schema")

    async with pool.acquire() as conn:
        service = LogService(conn)

        return await service.get_scheduler_jobs(
            schema,
            jobName,
            status,
            from_date,
            to_date,
            page,
            limit
        )