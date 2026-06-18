from fastapi import APIRouter, Depends
import asyncio

from app.database import get_db_pool
from app.auth.jwt_filter import get_current_user

from app.scheduler.scheduler import (
    trigger_single_tenant_sync,
    process_pending_upi_payments_by_tenant
)

router = APIRouter(
    prefix="/scheduler",
    tags=["Scheduler"]
)


# =====================================
# MASTER SYNC
# =====================================
@router.post("/master-sync/{schema_id}")
async def trigger_master_sync(
    schema_id: str,
    db_pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    asyncio.create_task(
        trigger_single_tenant_sync(
            db_pool,
            schema_id
        )
    )

    return {
        "status": "success",
        "schema_id": schema_id,
        "message": f"Master sync started for {schema_id}"
    }


# =====================================
# PAYMENT SYNC
# =====================================
@router.post("/payment-sync/{schema_id}")
async def trigger_payment_sync(
    schema_id: str,
    db_pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    asyncio.create_task(
        process_pending_upi_payments_by_tenant(
            db_pool,
            schema_id
        )
    )

    return {
        "status": "success",
        "schema_id": schema_id,
        "message": f"UPI payment posting started for {schema_id}"
    }