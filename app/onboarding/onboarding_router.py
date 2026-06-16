from fastapi import APIRouter, Depends, Request, BackgroundTasks, UploadFile, File
import asyncpg

from app.database import get_db_pool
from app.onboarding.onboarding_entity import (
    CreateOnboardingRequest,
    UpdateOnboardingRequest
)
from app.onboarding.onboarding_service import OnboardingService

router = APIRouter(
    tags=["Company"]
)


@router.post("/add_onboarding_form")
async def create_company_onboarding(
    request: Request,
    data: CreateOnboardingRequest,
    background_tasks: BackgroundTasks,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    return await OnboardingService.create_company_onboarding(
        request, data, background_tasks, db_pool
    )


@router.post("/approve_onboarding/{onboard_company_id}")
async def approve_company(
    onboard_company_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    return await OnboardingService.approve_company(
        onboard_company_id, request, background_tasks, db_pool
    )


@router.get("/get_all_companies")
async def get_all_companies(
    request: Request,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    return await OnboardingService.get_all_companies(
        request,
        db_pool
    )


@router.get("/get_by_company_id/{onboard_company_id}")
async def get_company_by_id(
    request: Request,
    onboard_company_id: str,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    return await OnboardingService.get_company_by_id(
        request,
        onboard_company_id,
        db_pool
    )


@router.patch("/update_company/{onboard_company_id}")
async def update_company(
    onboard_company_id: str,
    data: UpdateOnboardingRequest,
    request: Request,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    return await OnboardingService.update_company(
        request, onboard_company_id, data, db_pool
    )

@router.post("/upload-logo/{onboard_company_id}")
async def upload_logo(
    onboard_company_id: str,
    file: UploadFile = File(...),
    db_pool=Depends(get_db_pool)
):
    async with db_pool.acquire() as conn:

        company = await conn.fetchrow(
            """
            SELECT schema_id
            FROM ik_opspulse_b1.ik_onboarding_company
            WHERE onboard_company_id = $1
            """,
            onboard_company_id
        )

        if not company:
            raise HTTPException(404, "Company not found")

        schema_id = company["schema_id"]

    return await OnboardingService.upload_logo(
        onboard_company_id,
        schema_id,   # ✅ FIXED
        file,
        db_pool
    )


# ==========================================================
# UPDATE LOGO
# ==========================================================
@router.patch("/logo/{onboard_company_id}")
async def update_logo(
    onboard_company_id: str,
    file: UploadFile = File(...),
    db_pool=Depends(get_db_pool)
):
    async with db_pool.acquire() as conn:

        company = await conn.fetchrow(
            """
            SELECT schema_id
            FROM ik_opspulse_b1.ik_onboarding_company
            WHERE onboard_company_id = $1
            """,
            onboard_company_id
        )

        if not company:
            raise HTTPException(404, "Company not found")

        schema_id = company["schema_id"]

    return await OnboardingService.update_logo(
        onboard_company_id,
        schema_id,   # ✅ FIXED
        file,
        db_pool
    )