import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.log_service import LogService
from app.Integration.b1_master import SapMasterService
from app.Integration.b1_bp import SapBPService
from app.Integration.sap_api_client import SAPApiClient
from app.config.config_service import get_sap_config_by_schema


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
        hour=9,
        minute=0,
        args=[db_pool],
        id="sap_sync_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600
    )

    scheduler.start()
