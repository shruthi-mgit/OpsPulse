from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.log_service import LogService
from app.Integration.b1_master import SapMasterService
from app.Integration.b1_bp import SapBPService
from app.Integration.sap_api_client import SAPApiClient
from app.config.config_service import get_sap_config


scheduler = AsyncIOScheduler()


# ===================================
# GET TENANTS
# ===================================
async def get_tenants(conn):
    query = """
        SELECT schema_id
        FROM ik_payops_b1.ik_config
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
        config = await get_sap_config(conn)
        await SAPApiClient.login(config)
        # ========================
        # BRANCH
        # ========================
        try:
            branches = await SAPApiClient.get_branches_all(config)

            for b in branches:
                await SapMasterService.save_branch(conn, schema, b)

            await log.log_success(schema, schema_id, "Branch", "Branch sync success")

        except Exception as e:
            await log.log_error(schema, schema_id, "Branch", str(e))

        # ========================
        # BANK
        # ========================
        try:
            banks = await SAPApiClient.get_banks_all(config)

            for b in banks:
                await SapMasterService.save_bank(conn, schema, b)

            await log.log_success(schema, schema_id, "Bank", "Bank sync success")

        except Exception as e:
            await log.log_error(schema, schema_id, "Bank", str(e))

        # ========================
        # GL ACCOUNTS
        # ========================
        try:
            gl_accounts = await SAPApiClient.get_gl_all(config)

            for g in gl_accounts:
                await SapMasterService.save_glaccount(conn, schema, g)

            await log.log_success(schema, schema_id, "GLAccounts", "GL sync success")

        except Exception as e:
            await log.log_error(schema, schema_id, "GLAccounts", str(e))

        # ========================
        # BUSINESS PARTNERS (FULL SYNC)
        # ========================
        try:
            bp_data = await SAPApiClient.get_bp_all(config)  

            for bp in bp_data:
                await SapBPService.save_bp(conn, schema, bp)

            await log.log_success(schema, schema_id, "BusinessPartner", "BP sync success")

        except Exception as e:
            await log.log_error(schema, schema_id, "BusinessPartner", str(e))

    except Exception as e:
        # global failure
        await log.log_error(schema, schema_id, "ERROR", str(e))


# ===================================
# MAIN SYNC
# ===================================
async def sync_sap_data(db_pool):

    async with db_pool.acquire() as conn:

        tenants = await get_tenants(conn)

        for t in tenants:
            schema_id = t["schema_id"]

            await sync_one_tenant(conn, schema_id)


# ===================================
# START SCHEDULER
# ===================================
def start_scheduler(db_pool):

    scheduler.add_job(
        sync_sap_data,
        "interval",
        minutes=3,        
        args=[db_pool],
        max_instances=3,  # prevent parallel runs
        coalesce=True,
        misfire_grace_time=60
    )

    scheduler.start()