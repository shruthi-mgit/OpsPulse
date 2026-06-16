from fastapi import APIRouter, Request

from app.Integration.upi_service import UPIService
from app.Integration.schemas import GenerateUPIRequest
from app.Integration.payment_service import generate_id

router = APIRouter(
    prefix="/upi",
    tags=["UPI"]
)

@router.post("/generate/production")
async def generate_upi(
    payload: GenerateUPIRequest,
    request: Request
):
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:

        tenant_schema = getattr(request.state, "schema")

        payment_id = await generate_id(
            conn,
            tenant_schema,
            "ik_inc_payment_seq",
            "INCPH"
        )

        return await UPIService.generate_upi(
            conn=conn,
            tenant_schema=tenant_schema,
            payment_id=payment_id,
            merchant_id=payload.merchant_id,
            merchant_tran_id=payload.merchantTranId,
            amount=payload.amount,
            terminal_id=payload.terminalId,
            bill_number=payload.billNumber
        )

@router.post("/generate/stage")
async def generate_upi(
    payload: GenerateUPIRequest,
    request: Request
):
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:

        tenant_schema = getattr(request.state, "schema")

        payment_id = await generate_id(
            conn,
            tenant_schema,
            "ik_inc_payment_seq",
            "INCPH"
        )

        return await UPIService.stage_generate_upi(
            conn=conn,
            tenant_schema=tenant_schema,
            payment_id=payment_id,
            merchant_id=payload.merchant_id,
            merchant_tran_id=payload.merchantTranId,
            amount=payload.amount,
            terminal_id=payload.terminalId,
            bill_number=payload.billNumber
        )