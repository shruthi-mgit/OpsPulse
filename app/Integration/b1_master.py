import logging
import json

logger = logging.getLogger("sap-master-service")


class SapMasterService:

    # ===============================
    # BRANCH
    # ===============================
    @staticmethod
    async def save_branch(
        conn,
        tenant_schema: str,
        data: dict,
        schema_id: str,
        user_id: str
    ):

        try:

            print("SAVE_BRANCH DATA =", data)

            branch_id = str(data.get("BPLId"))
            branch_name = data.get("BPLName")

            print("branch_id =", branch_id)
            print("branch_name =", branch_name)

            if not branch_id or branch_id == "None":
                raise ValueError("branch_id required")

            if not branch_name:
                raise ValueError("branch_name required")

            await conn.execute(
                f"""
                INSERT INTO "{tenant_schema}".ik_branch
                (
                    branch_id,
                    branch_name,
                    is_active,
                    created_at,
                    created_by,
                    updated_at,
                    updated_by,
                    schema_id
                )
                VALUES
                (
                    $1,$2,TRUE,
                    CURRENT_TIMESTAMP,
                    $3,
                    CURRENT_TIMESTAMP,
                    $4,
                    $5
                )

                ON CONFLICT (branch_id)
                DO UPDATE SET
                    branch_name = EXCLUDED.branch_name,
                    is_active = TRUE,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = EXCLUDED.updated_by
                """,
                branch_id,
                branch_name,
                user_id,
                user_id,
                schema_id
            )

            print(f"✅ Branch Saved : {branch_id} - {branch_name}")

        except Exception as e:

            print("❌ SAVE_BRANCH ERROR =", str(e))
            print("❌ FAILED DATA =", data)

            raise

    # ===============================
    # BANK
    # ===============================
    @staticmethod
    async def save_bank(
        conn,
        tenant_schema: str,
        data: dict,
        schema_id: str,
        user_id: str
    ):

        bank_id = data.get("BankCode")
        bank_name = data.get("BankName")

        if not bank_id:
            raise ValueError("bank_id required")

        if not bank_name:
            raise ValueError("bank_name required")

        await conn.execute(
            f"""
            INSERT INTO "{tenant_schema}".ik_bank
            (
                bank_id,
                bank_name,
                is_active,
                created_at,
                created_by,
                updated_at,
                updated_by,
                schema_id
            )
            VALUES
            (
                $1,$2,TRUE,
                CURRENT_TIMESTAMP,
                $3,
                CURRENT_TIMESTAMP,
                $4,
                $5
            )

            ON CONFLICT (bank_id)
            DO UPDATE SET
                bank_name = EXCLUDED.bank_name,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = EXCLUDED.updated_by
            """,
            bank_id,
            bank_name,
            user_id,
            user_id,
            schema_id
        )

    # ===============================
    # GL ACCOUNT
    # ===============================
    @staticmethod
    async def save_gl_master(
        conn,
        tenant_schema: str,
        data: dict,
        schema_id: str,
        user_id: str
    ):

        try:

            account_id = str(
                data.get("Code") or ""
            ).strip()

            account_name = str(
                data.get("Name") or ""
            ).strip()

            balance = float(
                data.get("Balance") or 0
            )

            is_active = (
                str(
                    data.get("ActiveAccount") or "tNO"
                ).upper() == "TYES"
            )

            is_control_account = (
                str(
                    data.get("LockManualTransaction") or "tNO"
                ).upper() == "TYES"
            )

            if not account_id:
                return

            await conn.execute(
                f"""
                INSERT INTO "{tenant_schema}".ik_glaccount
                (
                    account_id,
                    account_name,
                    is_active,
                    is_control_act,
                    balance,
                    created_by,
                    updated_by,
                    schema_id
                )
                VALUES
                (
                    $1,$2,$3,$4,$5,$6,$7,$8
                )

                ON CONFLICT (account_id)

                DO UPDATE SET
                    account_name = EXCLUDED.account_name,
                    is_active = EXCLUDED.is_active,
                    is_control_act = EXCLUDED.is_control_act,
                    balance = EXCLUDED.balance,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = CURRENT_TIMESTAMP
                """,
                account_id,
                account_name,
                is_active,
                is_control_account,
                balance,
                user_id,
                user_id,
                schema_id
            )

        except Exception as e:

            logger.exception(
                f"GL Master Sync Failed : {str(e)}"
            )
    # ===============================
    # WAREHOUSE
    # ===============================
    @staticmethod
    async def save_warehouse(
        conn,
        tenant_schema: str,
        data: dict,
        schema_id: str,
        branch_id: str,
        user_id: str
    ):

        warehouse_code = data.get("WarehouseCode")

        warehouse_name = data.get("WarehouseName")

        if not branch_id or branch_id == "None":
            raise ValueError(
                f"Invalid branch_id for warehouse {warehouse_code}"
            )

        if not warehouse_code:
            raise ValueError("warehouse_code required")

        if not warehouse_name:
            raise ValueError("warehouse_name required")

        await conn.execute(
            f"""
            INSERT INTO "{tenant_schema}".ik_warehouse
            (
                warehouse_code,
                warehouse_name,
                city,
                state,
                country,
                is_active,
                branch_id,
                is_bin_activated,
                created_at,
                created_by,
                updated_at,
                updated_by,
                schema_id
            )

            VALUES
            (
                $1,$2,$3,$4,$5,$6,
                $7,
                FALSE,
                CURRENT_TIMESTAMP,
                $8,
                CURRENT_TIMESTAMP,
                $9,
                $10
            )

            ON CONFLICT (warehouse_code)

            DO UPDATE SET

                warehouse_name = EXCLUDED.warehouse_name,
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                country = EXCLUDED.country,
                is_active = EXCLUDED.is_active,
                branch_id = EXCLUDED.branch_id,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = EXCLUDED.updated_by
            """,

            warehouse_code,

            warehouse_name,

            data.get("City"),

            data.get("State"),

            data.get("Country"),

            False if data.get("Inactive") == "Y" else True,

            branch_id,

            user_id,

            user_id,

            schema_id
        )

    # ===============================
    # ITEM
    # ===============================
    
    @staticmethod
    async def save_item(
        conn,
        tenant_schema: str,
        item_data: list,
        schema_id: str,
        user_id: str
    ):

        try:

            rows = []

            # =========================
            # PREPARE ROWS
            # =========================
            for data in item_data:

                item_code = str(
                    data.get("ItemCode") or ""
                ).strip()

                item_name = str(
                    data.get("ItemName") or ""
                ).strip()

                if not item_code:
                    continue

                if not item_name:
                    item_name = "UNKNOWN_ITEM"

                rows.append(
                    (
                        item_code,
                        item_name,
                        str(data.get("ItemsGroupCode")),
                        data.get("InventoryItem"),
                        data.get("SalesItem"),
                        data.get("PurchaseItem"),
                        data.get("DefaultWarehouse"),
                        data.get("ManageSerialNumbers"),
                        data.get("ManageBatchNumbers"),
                        data.get("Valid"),
                        user_id,
                        user_id,
                        schema_id
                    )
                )

            if not rows:

                # logger.info(
                #     "⚠️ No valid item rows found"
                # )

                return

            # =========================
            # UPSERT QUERY
            # =========================
            query = f"""
                INSERT INTO "{tenant_schema}".ik_item
                (
                    item_code,
                    item_name,
                    item_group_code,
                    inventory_item,
                    sales_item,
                    purchase_item,
                    default_warehouse,
                    manage_serial,
                    manage_batch,
                    valid,
                    created_at,
                    created_by,
                    updated_at,
                    updated_by,
                    schema_id
                )

                VALUES
                (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
                    CURRENT_TIMESTAMP,
                    $11,
                    CURRENT_TIMESTAMP,
                    $12,
                    $13
                )

                ON CONFLICT (item_code)

                DO UPDATE SET

                    item_name = EXCLUDED.item_name,
                    item_group_code = EXCLUDED.item_group_code,
                    inventory_item = EXCLUDED.inventory_item,
                    sales_item = EXCLUDED.sales_item,
                    purchase_item = EXCLUDED.purchase_item,
                    default_warehouse = EXCLUDED.default_warehouse,
                    manage_serial = EXCLUDED.manage_serial,
                    manage_batch = EXCLUDED.manage_batch,
                    valid = EXCLUDED.valid,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = EXCLUDED.updated_by

                WHERE
                (
                    ik_item.item_name IS DISTINCT FROM EXCLUDED.item_name
                    OR ik_item.valid IS DISTINCT FROM EXCLUDED.valid
                    OR ik_item.default_warehouse IS DISTINCT FROM EXCLUDED.default_warehouse
                )
            """

            # =========================
            # CHUNK INSERT
            # =========================
            chunk_size = 5000

            total = len(rows)

            for i in range(0, total, chunk_size):

                chunk = rows[i:i + chunk_size]

                await conn.executemany(
                    query,
                    chunk
                )

                # logger.info(
                #     f"✅ Item Chunk Synced: "
                #     f"{min(i + chunk_size, total)} / {total}"
                # )

            # logger.info(
            #     f"✅ Bulk Item Sync Completed: "
            #     f"{total} rows"
            # )

        except Exception:

            logger.exception(
                "❌ Bulk Item Sync Failed"
            )

            raise


    # ===============================
    # GET WAREHOUSES
    # ===============================
    @staticmethod
    async def get_warehouses(conn, tenant_schema: str):

        query = f"""
            SELECT

                warehouse_code,

                warehouse_name,

                city,

                state,

                country,

                branch_id,

                is_bin_activated,

                is_active,

                created_at,

                updated_at

            FROM "{tenant_schema}".ik_warehouse

            WHERE is_active = TRUE

            ORDER BY warehouse_name
        """

        return await conn.fetch(query)

    # ===============================
    # GET ITEMS
    # ===============================
    @staticmethod
    async def get_items(conn, tenant_schema: str):

        query = f"""
            SELECT

                item_code,

                item_name,

                item_group_code,

                inventory_item,

                sales_item,

                purchase_item,

                default_warehouse,

                manage_serial,

                manage_batch,

                valid,

                created_at,

                updated_at

            FROM "{tenant_schema}".ik_item

            WHERE valid = 'Y'

            ORDER BY item_name
        """

        return await conn.fetch(query)

    @staticmethod
    async def save_bin(
        conn,
        tenant_schema: str,
        data: dict,
        schema_id: str,
        user_id: str
    ):

        bin_id = data.get("AbsEntry")
        bin_code = data.get("BinCode")
        warehouse_code = data.get("Warehouse")

        if not bin_id:
            raise ValueError("bin_id required")

        if not bin_code:
            raise ValueError("bin_code required")

        if not warehouse_code:
            raise ValueError("warehouse_code required")

        is_active = (
            False
            if data.get("Inactive") == "tYES"
            else True
        )

        await conn.execute(
            f"""
            INSERT INTO "{tenant_schema}".ik_bin
            (
                bin_id,
                bin_code,
                warehouse_code,
                is_active,
                created_at,
                created_by,
                updated_at,
                updated_by,
                schema_id
            )

            VALUES
            (
                $1,$2,$3,$4,
                CURRENT_TIMESTAMP,
                $5,
                CURRENT_TIMESTAMP,
                $6,
                $7
            )

            ON CONFLICT (bin_id)

            DO UPDATE SET

                bin_code = EXCLUDED.bin_code,
                warehouse_code = EXCLUDED.warehouse_code,
                is_active = EXCLUDED.is_active,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = EXCLUDED.updated_by
            """,
            bin_id,
            bin_code,
            warehouse_code,
            is_active,
            user_id,
            user_id,
            schema_id
        )

    @staticmethod
    async def save_merchant_id(
        conn,
        tenant_schema: str,
        data: dict,
        schema_id: str,
        user_id: str
    ):

        merchant_id = str(
            data.get("U_IKMID") or ""
        ).strip()

        if not merchant_id:
            raise ValueError(
                f"U_IKMID missing : {data}"
            )

        await conn.execute(
            f"""
            INSERT INTO
            "{tenant_schema}".ik_merchant_id
            (
                merchant_id,
                gl_account,
                qr_string_vpa,
                bank_api_key,
                branch,
                branch_id,
                schema_id,
                created_by,
                updated_by
            )

            VALUES
            (
                $1,$2,$3,$4,
                $5,$6,$7,
                $8,$9
            )

            ON CONFLICT (merchant_id)

            DO UPDATE SET

                gl_account    = EXCLUDED.gl_account,
                qr_string_vpa = EXCLUDED.qr_string_vpa,
                bank_api_key  = EXCLUDED.bank_api_key,
                branch        = EXCLUDED.branch,
                branch_id     = EXCLUDED.branch_id,
                updated_at    = NOW(),
                updated_by    = EXCLUDED.updated_by
            """,

            merchant_id,

            data.get("U_IKGL"),

            data.get("U_IKVPA"),

            data.get("U_IKAPI"),

            None,  # Branch not returned by SAP query

            None,  # BranchID not returned by SAP query

            schema_id,

            user_id,
            user_id
        )