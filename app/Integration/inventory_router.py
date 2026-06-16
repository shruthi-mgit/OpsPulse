
from fastapi import APIRouter, Depends, Request, Query

from app.database import get_db_pool
from app.auth.jwt_filter import get_current_user

from app.Integration.inventory_service import InventoryService
import json
from datetime import datetime


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


# =====================================
# WAREHOUSES
# =====================================
@router.get("/warehouses")
async def get_warehouses(

    request: Request,

    search: str = Query(
        "",
        description="Search warehouse"
    ),

    pool = Depends(get_db_pool),

    current_user: dict = Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        if not tenant_schema:
            return {
                "status": "error",
                "message": "Tenant schema not found"
            }

        return await InventoryService.get_warehouses(
            conn=conn,
            tenant_schema=tenant_schema,
            search=search
        )


# =====================================
# ITEMS
# =====================================
@router.get("/items")
async def get_items(

    request: Request,

    search: str = Query(
        "",
        description="Search item"
    ),

    pool = Depends(get_db_pool),

    current_user: dict = Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        if not tenant_schema:
            return {
                "status": "error",
                "message": "Tenant schema not found"
            }

        return await InventoryService.get_items(
            conn=conn,
            tenant_schema=tenant_schema,
            search=search
        )


# =====================================
# SERIAL NUMBERS
# =====================================
# SERIAL NUMBERS
# =====================================
@router.get("/serials/{item_code}/{whs_code}")
async def get_serial_numbers(

    request: Request,
    item_code: str,
    whs_code: str,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        if not tenant_schema:
            return {
                "status": "error",
                "message": "Tenant schema not found"
            }

        data = await InventoryService.get_serial_numbers(
            conn=conn,
            tenant_schema=tenant_schema,
            item_code=item_code,
            whs_code=whs_code
        )

        return {
            "status": "success",
            "count": len(data),
            "data": data
        }


# =====================================
# BATCH NUMBERS
# =====================================
@router.get("/batches/{item_code}/{whs_code}")
async def get_batch_numbers(

    request: Request,
    item_code: str,
    whs_code: str,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        if not tenant_schema:
            return {
                "status": "error",
                "message": "Tenant schema not found"
            }

        data = await InventoryService.get_batch_numbers(
            conn=conn,
            tenant_schema=tenant_schema,
            item_code=item_code,
            whs_code=whs_code
        )

        return {
            "status": "success",
            "count": len(data),
            "data": data
        }
# =====================================
# CREATE STOCK TRANSFER
# =====================================
@router.post("/stock-transfer")
async def create_stock_transfer(

    request: Request,

    payload: dict,

    db_pool = Depends(get_db_pool),

    current_user = Depends(get_current_user)

):

    return await InventoryService.create_stock_transfer(
        request,
        payload,
        db_pool,
        current_user
    )


# =====================================
# RECENT STOCK TRANSFERS
# =====================================
@router.get("/recent-stock-transfers")
async def get_recent_stock_transfers(

    request: Request,

    search: str = "",
    status: str = "",
    from_date: str = None,
    to_date: str = None,

    page: int = 1,
    per_page: int = 20,

    db_pool=Depends(get_db_pool),

    current_user: dict = Depends(get_current_user)

):

    return await InventoryService.get_recent_stock_transfers(
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
# =====================================
# STOCK TRANSFER DETAILS
# =====================================
@router.get("/stock-transfer-details/{it_id}")
async def get_stock_transfer_details(
    it_id: str,
    request: Request,
    pool=Depends(get_db_pool),
    current_user=Depends(get_current_user)
):

    async with pool.acquire() as conn:
        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )
        if not tenant_schema:
            return {
                "status": "error",
                "message": "Tenant schema not found"
            }
        return await InventoryService.get_stock_transfer_details(
            conn,
            tenant_schema,
            it_id
        )
# =====================================
# CREATE INVENTORY TRANSFER REQUEST
@router.post("/inventory-transfer-request")
async def create_inventory_transfer_request(
    request: Request,
    payload: dict,
    db_pool=Depends(get_db_pool),
    current_user=Depends(get_current_user)
):

    return await InventoryService.create_inventory_transfer_request(
        request=request,
        data=payload,
        db_pool=db_pool,
        current_user=current_user
    )
# =====================================
# BIN ENABLED CHECK
# =====================================
@router.get("/warehouse-bin-enabled/{whs_code}")
async def warehouse_bin_enabled(

    request: Request,

    whs_code: str,

    pool = Depends(get_db_pool),

    current_user: dict = Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        if not tenant_schema:

            return {
                "status": "error",
                "message": "Tenant schema not found"
            }

        data = await InventoryService.is_bin_enabled(
            conn=conn,
            tenant_schema=tenant_schema,
            whs_code=whs_code
        )

        return {
            "status": "success",
            "data": data
        }

# =====================================
# BIN DETAILS
# =====================================
@router.get("/bins/{item_code}/{whs_code}")
async def get_bin_details(

    request: Request,

    item_code: str,

    whs_code: str,

    pool = Depends(get_db_pool),

    current_user: dict = Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        if not tenant_schema:

            return {
                "status": "error",
                "message": "Tenant schema not found"
            }

        data = await InventoryService.get_bin_details(
            conn=conn,
            tenant_schema=tenant_schema,
            item_code=item_code,
            whs_code=whs_code
        )

        return {
            "status": "success",
            "data": data
        }

@router.get("/stock-transfer-series")
async def get_stock_transfer_series(

    request: Request,

    pool=Depends(get_db_pool),

    current_user=Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        data = await InventoryService.get_stock_transfer_series(
            conn=conn,
            tenant_schema=tenant_schema
        )

        return {
            "status": "success",
            "data": data
        }

@router.get("/inventory-transfer-request-series")
async def get_inventory_transfer_request_series(

    request: Request,

    pool=Depends(get_db_pool),

    current_user=Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        data = await InventoryService.get_inventory_transfer_request_series(
            conn=conn,
            tenant_schema=tenant_schema
        )
        return {
            "status": "success",
            "data": data
        }

@router.get("/itr-numbers")
async def get_itr_numbers(

    request: Request,

    search: str = "",

    status: str = "",

    page: int = 1,

    per_page: int = 20,

    pool=Depends(get_db_pool),

    current_user=Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        if not tenant_schema:

            return {
                "status": "error",
                "message": "Tenant schema not found"
            }

        return await InventoryService.get_itr_numbers(
            conn=conn,
            tenant_schema=tenant_schema,
            search=search,
            status=status,
            page=page,
            per_page=per_page
        )
@router.get("/itr-details/{itr_id}")
async def get_itr_details(
    itr_id: str,
    request: Request,
    pool=Depends(get_db_pool),
    current_user=Depends(get_current_user)
):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        return await InventoryService.get_itr_details(
            conn,
            tenant_schema,
            itr_id
        )

@router.get("/bin-details/{whs_code}")
async def get_bin_details(
    request: Request,
    whs_code: str,
    pool=Depends(get_db_pool),
    current_user: dict = Depends(get_current_user)
):

    tenant_schema = request.state.schema

    async with pool.acquire() as conn:

        data = await conn.fetch(
            f"""
            SELECT
                bin_id,
                bin_code,
                warehouse_code,
                is_active
            FROM "{tenant_schema}".ik_bin
            WHERE
                warehouse_code = $1
                AND is_active = TRUE
            ORDER BY bin_code
            """,
            whs_code
        )

        return {
            "status": "success",
            "data": [dict(x) for x in data]
        }

@router.get("/warehouse/{warehouse_code}/branch")
async def get_branch_by_warehouse(

    request: Request,

    warehouse_code: str,

    pool = Depends(get_db_pool),

    current_user: dict = Depends(get_current_user)

):

    async with pool.acquire() as conn:

        tenant_schema = getattr(
            request.state,
            "schema",
            None
        )

        if not tenant_schema:
            return {
                "status": "error",
                "message": "Tenant schema not found"
            }

        data = await conn.fetchrow(
            f"""
            SELECT
                warehouse_code,
                warehouse_name,
                branch_id
            FROM "{tenant_schema}".ik_warehouse
            WHERE warehouse_code = $1
            """,
            warehouse_code
        )

        if not data:
            raise HTTPException(
                status_code=404,
                detail="Warehouse not found"
            )

        return {
            "status": "success",
            "data": dict(data)
        }