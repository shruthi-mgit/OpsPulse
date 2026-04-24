from fastapi import APIRouter, Request, HTTPException, Depends
from app.Integration.payment_service import SapPaymentService
from app.Integration.dashboard_service import DashboardService
from app.database import get_db_pool
from app.auth.jwt_filter import get_current_user
from fastapi import Query


router = APIRouter(prefix="/payment", tags=["Payments"])





# =========================
# ROLE CHECK FUNCTION
# =========================
def check_finance_access(request: Request):

    role = getattr(request.state, "role", None)

    if role not in ["Finance", "Admin"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Finance role required"
        )


# =========================
# GET CUSTOMER
# =========================
@router.get("/customers")
async def get_customers(
    pool = Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
    search: str = ""
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_customers(
            conn,
            tenant_schema,
            search   # ✅ only 3 args
        )

# =========================
# GET INVOICES
# =========================
@router.get("/customer/{customer_code}/invoices")
async def get_invoices(
    customer_code: str,
    request: Request,
    db_pool = Depends(get_db_pool)
):

    check_finance_access(request)

    return await SapPaymentService.get_invoices(
        customer_code,
        request,
        db_pool
    )


# =========================
# GET GL ACCOUNTS
# =========================
@router.get("/gl-accounts")
async def get_gl_accounts(
    pool = Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_gl_accounts(
            conn,
            tenant_schema
        )

@router.get("/dashboard")
async def get_dashboard(request: Request):

    check_finance_access(request)

    return await DashboardService.get_dashboard()

@router.get("/banks")
async def get_banks(
    pool = Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
    search: str = ""
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_banks(
            conn,
            tenant_schema,
            search
        )

@router.get("/suppliers")
async def get_suppliers(
    search: str = Query("", description="Search supplier"),
    pool = Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_suppliers(
            conn,
            tenant_schema,
            search
        )

@router.get("/supplier/{supplier_code}/invoices")
async def get_supplier_invoices(
    supplier_code: str,
    request: Request,                         # ✅ ADD
    pool = Depends(get_db_pool),             # ✅ ADD
    current_user: dict = Depends(get_current_user)
):

    check_finance_access(request)            # ✅ (optional but recommended)

    return await SapPaymentService.get_supplier_invoices(
        supplier_code,
        request,
        pool                                 # ✅ FIXED
    )

@router.get("/branches")
async def get_branches(
    search: str = "",
    pool = Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
):
    async with pool.acquire() as conn:

        # Get tenant schema from logged-in user
        tenant_schema = current_user.get("company_schema")

        # Optional safety check
        if not tenant_schema:
            return {
                "status": "error",
                "message": "Tenant schema not found for user"
            }

        return await SapPaymentService.get_branches(
            conn=conn,
            tenant_schema=tenant_schema,
            search=search
        )
@router.post("/incoming")
async def create_incoming_payment(
    request: Request,
    payload: dict,
    db_pool = Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)   # ✅ ADD
):
    check_finance_access(request)

    return await SapPaymentService.create_incoming_payment(
        request,
        payload,
        db_pool,
        current_user   
    )

@router.post("/outgoing")
async def create_outgoing_payment(
    request: Request,
    payload: dict,
    db_pool=Depends(get_db_pool),
    current_user=Depends(get_current_user)
):
    return await SapPaymentService.create_outgoing_payment(
        request,
        payload,
        db_pool,
        current_user
    )

@router.get("/payments/incoming/recent")
async def get_recent_incoming(request: Request):

    db_pool = request.app.state.db_pool
    current_user = request.state.user

    return await SapPaymentService.get_recent_incoming_payments(
        request,
        db_pool,
        current_user
    )

@router.get("/payments/outgoing/recent")
async def get_recent_outgoing(request: Request):

    db_pool = request.app.state.db_pool
    current_user = request.state.user

    return await SapPaymentService.get_recent_outgoing_payments(
        request,
        db_pool,
        current_user
    )