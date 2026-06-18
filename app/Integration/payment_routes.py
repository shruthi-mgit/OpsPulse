from fastapi import APIRouter, Request, HTTPException, Depends
from app.Integration.payment_service import SapPaymentService
#from app.Integration.dashboard_service import DashboardService
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
    search: str = "",
    page: int = 1,
    per_page: int = 200
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_customers(
            conn=conn,
            tenant_schema=tenant_schema,
            search=search,
            page=page,
            per_page=per_page
        )

# =========================
# GET INVOICES
# =========================
@router.get("/customer/{customer_code}/invoices/{bpl_id}")
async def get_invoices(
    customer_code: str,
    bpl_id: int,
    request: Request,
    db_pool=Depends(get_db_pool)
):
    check_finance_access(request)

    return await SapPaymentService.get_invoices(
        customer_code,
        bpl_id,
        request,
        db_pool
    )

# =========================
# GET GL ACCOUNTS
# =========================
@router.get("/gl-accounts")
async def get_gl_accounts(
    search: str = "",
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = current_user.get(
            "company_schema"
        )

        return await SapPaymentService.get_gl_accounts(
            conn,
            tenant_schema,
            search
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
    pool = Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
    search: str = "",
    page: int = 1,
    per_page: int = 200
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_suppliers(
            conn=conn,
            tenant_schema=tenant_schema,
            search=search,
            page=page,
            per_page=per_page
        )
@router.get("/supplier/{supplier_code}/invoices/{bpl_id}")
async def get_supplier_invoices(
    supplier_code: str,
    bpl_id: int,
    request: Request,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):
    check_finance_access(request)

    return await SapPaymentService.get_supplier_invoices(
        supplier_code,
        bpl_id,
        request,
        pool
    )

@router.get("/branches")
async def get_branches(
    search: str = "",
    pool = Depends(get_db_pool),
    current_user: dict = Depends(get_current_user),
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

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
    current_user: dict = Depends(get_current_user)   
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
async def get_recent_incoming(
    request: Request,
    search: str = "",
    status: str = "",
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    per_page: int = 20
):

    db_pool = request.app.state.db_pool
    current_user = request.state.user

    return await SapPaymentService.get_recent_incoming_payments(
        request=request,
        db_pool=db_pool,
        current_user=current_user,
        search=search,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        per_page=per_page
    )

@router.get("/payments/outgoing/recent")
async def get_recent_outgoing(
    request: Request,
    search: str = "",
    status: str = "",
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    per_page: int = 20
):

    db_pool = request.app.state.db_pool
    current_user = request.state.user

    return await SapPaymentService.get_recent_outgoing_payments(
        request=request,
        db_pool=db_pool,
        current_user=current_user,
        search=search,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        per_page=per_page
    )

@router.get("/incoming-payment-series")
async def get_incoming_payment_series(
    branch_id: str,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_branch_series(
            conn=conn,
            tenant_schema=tenant_schema,
            branch_id=branch_id,
            object_code="24"
        )

@router.get("/outgoing-payment-series")
async def get_outgoing_payment_series(
    branch_id: str,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_branch_series(
            conn=conn,
            tenant_schema=tenant_schema,
            branch_id=branch_id,
            object_code="46"
        )

@router.get("/controlled-gl-accounts-bank-transfer")
async def get_ip_controled_glaccount(
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_ip_controled_glaccount(
            conn=conn,
            tenant_schema=tenant_schema
        )

@router.get(
    "/cash-glaccounts"
)
async def get_cash_gl_accounts(
    request: Request,
    db_pool = Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    return await SapPaymentService.get_cash_gl_accounts(
        request,
        db_pool
    )

@router.get("/control-accounts")
async def get_control_accounts(
    request: Request,
    db_pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    return await SapPaymentService.get_control_accounts(
        request,
        db_pool
    )

@router.get("/gl-master")
async def get_gl_master(
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = current_user.get(
            "company_schema"
        )

        return await SapPaymentService.get_gl_master(
            conn=conn,
            tenant_schema=tenant_schema
        )
# =====================================
# OUTGOING GL ACCOUNTS
# =====================================
# @router.get("/outgoing-gl-accounts")
# async def get_outgoing_gl_accounts(

#     request: Request,

#     db_pool = Depends(get_db_pool),

#     current_user = Depends(get_current_user)

# ):

#     tenant_schema = getattr(
#         request.state,
#         "schema"
#     )

#     async with db_pool.acquire() as conn:

#         return await SapPaymentService.get_outgoing_gl_accounts(
#             conn,
#             tenant_schema
#         )

@router.get("/merchant-mapping")
async def get_merchant_mapping(
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get(
            "company_schema"
        )

        return await SapPaymentService.get_merchant_mapping(
            conn=conn,
            tenant_schema=tenant_schema
        )
# =========================
# GET PAYMENT MEANS LINES
# =========================
@router.get("/incoming/get_all_paymeans_lines_by_payment_id/{payment_id}")
async def get_payment_means_lines(
    payment_id: str,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):
    async with pool.acquire() as conn:
 
        tenant_schema = current_user.get("company_schema")
 
        return await SapPaymentService.get_payment_means_lines(
            conn=conn,
            tenant_schema=tenant_schema,
            payment_id=payment_id
        )
 
@router.patch("/incoming/patch_paymeans_lines_by_payment_id/{payment_id}")
async def patch_payment_means_line(
    payment_id: str,
    tenant_schema: str,
    payload: dict,
    pool=Depends(get_db_pool)
):
    async with pool.acquire() as conn:
 
        return await SapPaymentService.patch_payment_means_line(
            conn=conn,
            tenant_schema=tenant_schema,
            payment_id=payment_id,
            payload=payload
        )
       
# =========================
# POST INCOMING PAYMENT (SAP)
# =========================
@router.post("/post_sap_incoming")
async def create_incoming_payment_sap(
    request: Request,
    payload: dict,
    db_pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):
    check_finance_access(request)
 
    return await SapPaymentService.create_incoming_payment_sap(
        request,
        payload,
        db_pool,
        current_user
    )

# =========================
# POST INCOMING PAYMENT (SAVE TO DB)
# =========================
@router.post("/post_db_incoming")
async def create_incoming_payment_sap(
    request: Request,
    payload: dict,
    db_pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):
    check_finance_access(request)
 
    return await SapPaymentService.create_incoming_db_sap(
        request,
        payload,
        db_pool,
        current_user
    )

@router.patch("/incoming/patch_status_by_payment_id/{payment_id}")
async def patch_payment_means_line(
    request: Request,
    payment_id: str,
    payload: dict,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    check_finance_access(request)

    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.patch_payment_means_line(
            conn=conn,
            tenant_schema=tenant_schema,
            payment_id=payment_id,
            payload=payload
        )

@router.get("/incoming/recent/{payment_id}")
async def get_incoming_payment_by_id(
    payment_id: str,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_incoming_payment_by_id(
            conn,
            tenant_schema,
            payment_id
        )

@router.get("/outgoing/recent/{payment_id}")
async def get_outgoing_payment_by_id(
    payment_id: str,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):
    async with pool.acquire() as conn:

        tenant_schema = current_user.get("company_schema")

        return await SapPaymentService.get_outgoing_payment_by_id(
            conn,
            tenant_schema,
            payment_id
        )

# =====================================
# INCOMING PAYMENT REPORT
# =====================================
@router.get("/incoming-payment-report/{doc_key}")
async def get_incoming_payment_report(
    doc_key: int,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = current_user.get(
            "company_schema"
        )

        return await SapPaymentService.get_incoming_payment_report(
            conn=conn,
            tenant_schema=tenant_schema,
            doc_key=doc_key
        )

# =====================================
# OUTGOING PAYMENT REPORT
# =====================================
@router.get("/outgoing-payment-report/{doc_key}")
async def get_outgoing_payment_report(
    doc_key: int,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = current_user.get(
            "company_schema"
        )

        return await SapPaymentService.get_outgoing_payment_report(
            conn=conn,
            tenant_schema=tenant_schema,
            doc_key=doc_key
        )

# =====================================
# OUTGOING PAYMENT CHEQUE REPORT
# =====================================
@router.get("/outgoing-payment-cheque-report/{check_key}")
async def get_outgoing_payment_cheque_report(
    check_key: int,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = current_user.get(
            "company_schema"
        )

        return await SapPaymentService.get_outgoing_payment_cheque_report(
            conn=conn,
            tenant_schema=tenant_schema,
            check_key=check_key
        )

@router.get("/house-bank-accounts")
async def get_house_bank_accounts(
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = current_user.get(
            "company_schema"
        )

        return await SapPaymentService.get_house_bank_accounts(
            conn=conn,
            tenant_schema=tenant_schema
        )