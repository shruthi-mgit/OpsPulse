import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.log_service import LogService
from app.Integration.b1_master import SapMasterService
from app.Integration.b1_bp import SapBPService
from app.Integration.sap_api_client import SAPApiClient
from app.config.config_service import get_sap_config_by_schema
from app.Integration.payment_service import SapPaymentService
import json
from app.Integration.payment_service import (
    generate_error_id,
    extract_sap_error
)


logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


# ===================================
# GET TENANTS
# ===================================
async def get_tenants(conn):

    query = """
        SELECT schema_id
        FROM ik_opspulse_b1.ik_config
    """

    return await conn.fetch(query)


# ===================================
# SYNC FOR ONE TENANT
# ===================================
async def sync_one_tenant(conn, schema_id):

    schema = schema_id

    log = LogService(conn)

    try:

        # 🔐 Login once per tenant
        config = await get_sap_config_by_schema(
            conn,
            schema_id
        )

        user_id = config["user_id"]

        await SAPApiClient.login(config)

        # ===================================
        # BRANCH
        # ===================================
        async def sync_branch():

            try:

                branches = await SAPApiClient.get_branches_all(
                    config
                )

                for b in branches:

                    print("BRANCH DATA =", b)

                    await SapMasterService.save_branch(
                        conn,
                        schema,
                        b,
                        schema_id,
                        user_id
                    )

                await log.log_success(
                    schema,
                    schema_id,
                    "Branch",
                    "Branch sync success"
                )

            except Exception as e:

                await log.log_error(
                    schema,
                    schema_id,
                    "Branch",
                    str(e)
                )


        # ===================================
        # BANK
        # ===================================
        async def sync_bank():

            try:

                banks = await SAPApiClient.get_banks_all(
                    config
                )

                for b in banks:

                    await SapMasterService.save_bank(
                        conn,
                        schema,
                        b,
                        schema_id,
                        user_id
                    )

                await log.log_success(
                    schema,
                    schema_id,
                    "Bank",
                    "Bank sync success"
                )

            except Exception as e:

                await log.log_error(
                    schema,
                    schema_id,
                    "Bank",
                    str(e)
                )


        # ===================================
        # GL
        # ===================================
        async def sync_gl():

            try:

                gl_accounts = await SAPApiClient.get_gl_master(
                    config
                )

                for g in gl_accounts:

                    await SapMasterService.save_gl_master(
                        conn,
                        schema,
                        g,
                        schema_id,
                        user_id
                    )

                await log.log_success(
                    schema,
                    schema_id,
                    "GLAccounts",
                    "GL sync success"
                )

            except Exception as e:

                await log.log_error(
                    schema,
                    schema_id,
                    "GLAccounts",
                    str(e)
                )


        # ===================================
        # ITEM
        # ===================================
        async def sync_item():

            try:

                async for page in SAPApiClient.get_items_all(
                    config
                ):

                    await SapMasterService.save_item(
                        conn,
                        schema,
                        page,
                        schema_id,
                        user_id
                    )

                await log.log_success(
                    schema,
                    schema_id,
                    "Item",
                    "Item sync success"
                )

            except Exception as e:

                await log.log_error(
                    schema,
                    schema_id,
                    "Item",
                    str(e)
                )


        # ===================================
        # BUSINESS PARTNER
        # ===================================
        async def sync_bp():

            try:

                async for bp_chunk in SAPApiClient.get_bp_all(
                    config
                ):

                    await SapBPService.save_bulk_bp(
                        conn,
                        schema,
                        bp_chunk,
                        user_id,
                        schema_id
                    )

                await log.log_success(
                    schema,
                    schema_id,
                    "BusinessPartner",
                    "BP sync success"
                )

            except Exception as e:

                await log.log_error(
                    schema,
                    schema_id,
                    "BusinessPartner",
                    str(e)
                )

        
        # ===================================
        # RUN PARALLEL
        # ===================================
        await sync_branch() 
        await sync_bank() 
        await sync_gl() 
        # ===================================
        # WAREHOUSE
        # ===================================
        try:

            warehouses = await SAPApiClient.get_warehouses_all(
                config
            )

            for w in warehouses:

                print(
                    "WAREHOUSE =",
                    w.get("WarehouseCode"),
                    "| BRANCH_ID =",
                    w.get("BusinessPlaceID")
                )

                await SapMasterService.save_warehouse(
                    conn,
                    schema,
                    w,
                    schema_id,
                    str(w.get("BusinessPlaceID")),
                    user_id
                )

            await log.log_success(
                schema,
                schema_id,
                "Warehouse",
                "Warehouse sync success"
            )

        except Exception as e:

            await log.log_error(
                schema,
                schema_id,
                "Warehouse",
                str(e)
            )
        # ===================================
        # BIN
        # ===================================
        try:

            bins = await SAPApiClient.get_bins_all(
                config
            )

            for b in bins:

                await SapMasterService.save_bin(
                    conn,
                    schema,
                    b,
                    schema_id,
                    user_id
                )

            await log.log_success(
                schema,
                schema_id,
                "Bin",
                "Bin sync success"
            )

        except Exception as e:

            await log.log_error(
                schema,
                schema_id,
                "Bin",
                str(e)
            )

        # ===================================
        # MERCHANT ID
        # ===================================
        try:

            merchant_ids = await SAPApiClient.get_merchant_ids_all(
                config
            )

            for m in merchant_ids:

                await SapMasterService.save_merchant_id(
                    conn,
                    schema,
                    m,
                    schema_id,
                    user_id
                )

            await log.log_success(
                schema,
                schema_id,
                "MerchantID",
                "Merchant ID sync success"
            )

        except Exception as e:

            await log.log_error(
                schema,
                schema_id,
                "MerchantID",
                str(e)
            )
        await sync_item() 
        await sync_bp()
     

    except Exception as e:

        import traceback

        traceback.print_exc()

        print("GLOBAL ERROR =", repr(e))

        await log.log_error(
            schema,
            schema_id,
            "GLOBAL_ERROR",
            str(e)
        )

async def process_pending_upi_payments(db_pool):

    print("=" * 60)
    print("UPI TO SAP POSTING STARTED")
    print("=" * 60)

    async with db_pool.acquire() as conn:

        tenants = await get_tenants(conn)

    for tenant in tenants:

        schema_id = tenant["schema_id"]

        async with db_pool.acquire() as conn:

            rows = await conn.fetch(
                f"""
                SELECT DISTINCT h.payment_id
                FROM "{schema_id}".ik_inc_payment_header h
                INNER JOIN "{schema_id}".ik_inc_payment_paymeans_line p
                    ON h.payment_id = p.payment_id
                WHERE
                    h.status = 'Draft'
                    AND h.sap_status = 'Pending'
                    AND p.upi_status = 'SUCCESS'
                """
            )

            if not rows:
                continue

            print(
                f"FOUND {len(rows)} PAYMENTS FOR {schema_id}"
            )

            # Load config once per tenant
            config = await get_sap_config_by_schema(
                conn,
                schema_id
            )

            for row in rows:

                payment_id = row["payment_id"]

                try:

                    print(
                        f"PROCESSING PAYMENT : {payment_id}"
                    )

                    payload = await SapPaymentService.build_sap_payload_from_db(
                        conn,
                        schema_id,
                        payment_id
                    )

                    print("=" * 100)
                    print(
                        "SAP PAYLOAD =",
                        json.dumps(payload, indent=4, default=str)
                    )
                    print("=" * 100)

                    sap_response = await SAPApiClient.post_incoming_payment(
                        config,
                        payload
                    )

                    print(
                        "SAP RESPONSE =",
                        sap_response
                    )

                    await conn.execute(
                        f"""
                        UPDATE "{schema_id}".ik_inc_payment_header
                        SET
                            status='Close',
                            sap_status='Posted',
                            sap_docentry=$1,
                            sap_docnum=$2,
                            updated_at=NOW()
                        WHERE payment_id=$3
                        """,
                        str(sap_response.get("DocEntry")),
                        str(sap_response.get("DocNum")),
                        payment_id
                    )

                    print(
                        f"PAYMENT POSTED SUCCESSFULLY : {payment_id}"
                    )

                except Exception as e:

                    print(
                        f"PAYMENT FAILED : {payment_id}"
                    )

                    await log_payment_error(
                        conn,
                        schema_id,
                        payment_id,
                        payload if "payload" in locals() else {},
                        str(e)
                    )

                    continue



async def process_pending_upi_payments_by_tenant(
    db_pool,
    schema_id
):

    print("=" * 60)
    print(f"UPI TO SAP POSTING STARTED FOR {schema_id}")
    print("=" * 60)

    async with db_pool.acquire() as conn:

        rows = await conn.fetch(
            f"""
            SELECT DISTINCT h.payment_id
            FROM "{schema_id}".ik_inc_payment_header h
            INNER JOIN "{schema_id}".ik_inc_payment_paymeans_line p
                ON h.payment_id = p.payment_id
            WHERE
                h.status = 'Draft'
                AND h.sap_status = 'Pending'
                AND p.upi_status = 'SUCCESS'
            """
        )

        config = await get_sap_config_by_schema(
                    conn,
                    schema_id
                )

        for row in rows:

            payment_id = row["payment_id"]

            try:

                print("PROCESSING PAYMENT =", payment_id)

                payload = await SapPaymentService.build_sap_payload_from_db(
                    conn,
                    schema_id,
                    payment_id
                )

                

                sap_response = await SAPApiClient.post_incoming_payment(
                    config,
                    payload
                )

                await conn.execute(
                    f"""
                    UPDATE "{schema_id}".ik_inc_payment_header
                    SET
                        status='Close',
                        sap_status='Posted',
                        sap_docentry=$1,
                        sap_docnum=$2,
                        series_id=$3,
                        journal_remarks=$4,
                        updated_at=NOW()
                    WHERE payment_id=$5
                    """,
                    str(sap_response.get("DocEntry")),
                    str(sap_response.get("DocNum")),
                    sap_response.get("Series"),
                    sap_response.get("JournalRemarks"),
                    payment_id
                )

                print(
                    f"PAYMENT POSTED SUCCESSFULLY : {payment_id}"
                )

            except Exception as e:

                print(
                    f"PAYMENT FAILED : {payment_id}"
                )

                await log_payment_error(
                    conn,
                    schema_id,
                    payment_id,
                    payload if "payload" in locals() else {},
                    str(e)
                )

async def log_payment_error(
    conn,
    tenant_schema,
    payment_id,
    payload,
    error
):

    error_id = await generate_error_id(
        conn,
        tenant_schema
    )

    await conn.execute(
        f"""
        INSERT INTO "{tenant_schema}".ik_error
        (
            error_id,
            schema_id,
            type,
            error_desc,
            json
        )
        VALUES
        (
            $1,$2,$3,$4,$5
        )
        """,
        error_id,
        tenant_schema,
        "IncomingPaymentSAP",
        f"Payment ID {payment_id} : {extract_sap_error(error)}",
        json.dumps(payload, default=str)
    )

    await conn.execute(
        f"""
        UPDATE "{tenant_schema}".ik_inc_payment_header
        SET
            sap_status='Failed',
            updated_at=NOW()
        WHERE payment_id=$1
        """,
        payment_id
    )


# ===================================
# MAIN SYNC (PARALLEL)
# ===================================
async def sync_sap_data(db_pool):

    print("=" * 60)
    print("SYNC STARTED")
    print("=" * 60)

    async with db_pool.acquire() as conn:

        tenants = await get_tenants(conn)

    async def run_for_tenant(schema_id):

        async with db_pool.acquire() as conn:

            await sync_one_tenant(
                conn,
                schema_id
            )

    await asyncio.gather(
        *[
            run_for_tenant(t["schema_id"])
            for t in tenants
        ]
    )


# ===================================
# TRIGGER FOR SINGLE TENANT (ONBOARD)
# ===================================
async def trigger_single_tenant_sync(
    db_pool,
    schema_id
):

    async with db_pool.acquire() as conn:

        await sync_one_tenant(
            conn,
            schema_id
        )


# ===================================
# START SCHEDULER
# ===================================
def start_scheduler(db_pool):

    scheduler.add_job(
        sync_sap_data,
        "cron",
        hour=3,
        minute=0,
        args=[db_pool],
        id="sap_sync_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600
    )

    scheduler.add_job(
        process_pending_upi_payments,
        "cron",
        hour=4,
        minute=55,
        args=[db_pool],
        id="incoming_payment_sap_posting",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600
    )

    scheduler.start()

