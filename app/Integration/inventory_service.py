from asyncpg import Connection
from app.Integration.sap_api_client import SAPApiClient
from app.config.config_service import get_sap_config_by_schema
from datetime import datetime
from fastapi import HTTPException
from app.scheduler.log_service import LogService
import copy
from datetime import datetime

class InventoryService:

    # =====================================
    # WAREHOUSES
    # =====================================
    @staticmethod
    async def get_warehouses(
        conn: Connection,
        tenant_schema: str,
        search: str = ""
    ):

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

            WHERE
            (
                warehouse_code ILIKE $1
                OR warehouse_name ILIKE $1
            )
            AND is_active = TRUE

            ORDER BY warehouse_name
        """

        return await conn.fetch(
            query,
            f"%{search}%"
        )

    # =====================================
    # ITEMS
    # =====================================
    @staticmethod
    async def get_items(
        conn: Connection,
        tenant_schema: str,
        search: str = ""
    ):

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

            WHERE
            (
                item_code ILIKE $1
                OR item_name ILIKE $1
            )
            AND valid = 'tYES'

            ORDER BY item_name
        """

        return await conn.fetch(
            query,
            f"%{search}%"
        )

    # =====================================
    # SERIAL NUMBERS
    # =====================================
    @staticmethod
    async def get_serial_numbers(
        conn: Connection,
        tenant_schema: str,
        item_code: str,
        whs_code: str
    ):

        config = await get_sap_config_by_schema(
            conn,
            tenant_schema
        )

        data = await SAPApiClient.get_serial_numbers(
            config,
            item_code,
            whs_code
        )

        if isinstance(data, dict):
            rows = data.get("value", [])
        else:
            rows = data

        filtered_rows = [
            row
            for row in rows
            if (
                float(row.get("AvailableQty", 0))
                - float(row.get("QuantityOut", 0))
            ) > 0
        ]

        return filtered_rows


    # =====================================
    # BATCH NUMBERS
    # =====================================
    @staticmethod
    async def get_batch_numbers(
        conn: Connection,
        tenant_schema: str,
        item_code: str,
        whs_code: str
    ):

        config = await get_sap_config_by_schema(
            conn,
            tenant_schema
        )

        data = await SAPApiClient.get_batch_numbers(
            config,
            item_code,
            whs_code
        )

        rows = data.get("value", data)

        filtered_rows = [
            row
            for row in rows
            if (
                float(row.get("AvailableQty", 0))
                - float(row.get("QuantityOut", 0))
            ) > 0
        ]

        return filtered_rows

    @staticmethod
    async def create_stock_transfer(
        request,
        payload,
        db_pool,
        current_user
    ):

        import copy
        from fastapi import HTTPException

        tenant_schema = request.state.schema

        user_id = str(
            current_user["user_id"]
        )

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                # =====================================
                # GENERATE TRANSFER ID
                # =====================================

                seq = await conn.fetchval(f"""
                    SELECT nextval(
                        '"{tenant_schema}".ik_inventory_transfer_seq'
                    )
                """)

                transfer_id = (
                    f"INVTH_{seq}"
                )
    
                doc_date = (
                    datetime.strptime(
                        payload["DocDate"],
                        "%Y-%m-%d"
                    ).date()
                    if payload.get("DocDate")
                    else None
                )

                due_date = (
                    datetime.strptime(
                        payload["DueDate"],
                        "%Y-%m-%d"
                    ).date()
                    if payload.get("DueDate")
                    else None
                )

                tax_date = (
                    datetime.strptime(
                        payload["TaxDate"],
                        "%Y-%m-%d"
                    ).date()
                    if payload.get("TaxDate")
                    else None
                )

                itr_id = payload.get("U_IKOPID")

                base_type = (
                    "ITR"
                    if itr_id
                    else None
                )
                # =====================================
                # INSERT HEADER
                # =====================================

                await conn.execute(f"""
                    INSERT INTO
                    "{tenant_schema}".ik_it_header
                    (
                        it_id,
                        doc_date,
                        due_date,
                        it_date,
                        branch,
                        branch_id,
                        from_wh_code,
                        to_wh_code,
                        remarks,
                        journal_remarks,
                        driver_name,
                        oil,
                        kilometer,
                        purpose,
                        base_id,
                        base_type,
                        created_by,
                        updated_by,
                        schema_id,
                        sap_status,
                        status
                    )
                    VALUES
                    (
                        $1,$2,$3,$4,
                        $5,$6,$7,$8,
                        $9,$10,
                        $11,$12,$13,$14,

                        $15,$16,

                        $17,$17,$18,
                        'Pending',
                        'Open'
                    )
                """,

                    transfer_id,

            

                    doc_date,
                    due_date,
                    tax_date,

                    payload.get("BPLName"),
                    str(payload.get("BPLID"))
                    if payload.get("BPLID")
                    else None,

                    payload.get("FromWarehouse"),
                    payload.get("ToWarehouse"),

                    payload.get("Comments"),
                    payload.get("Comments"),
                    payload.get("U_IKDN"),
                    payload.get("U_IKOIL"),
                    payload.get("U_IKKMS"),
                    payload.get("U_IKPP"),

                    itr_id,         # base_id
                    base_type, 


                    user_id,
                    tenant_schema
                )

                # =====================================
                # INSERT LINES
                # =====================================

                for line in payload.get(
                    "StockTransferLines",
                    []
                ):

                    line_seq = await conn.fetchval(f"""
                        SELECT nextval(
                            '"{tenant_schema}".ik_inventory_transfer_line_seq'
                        )
                    """)

                    line_id = (
                        f"INTIL_{line_seq}"
                    )

                    serials = line.get(
                        "SerialNumbers",
                        []
                    )

                    batches = line.get(
                        "BatchNumbers",
                        []
                    )

                    await conn.execute(f"""
                        INSERT INTO
                        "{tenant_schema}".ik_it_item_line
                        (
                            it_item_line_id,
                            it_id,
                            item_code,
                            item_name,
                            from_wh_code,
                            to_wh_code,
                            qty,
                            manage_serial,
                            manage_batch,
                            created_by,
                            updated_by,
                            schema_id
                        )
                        VALUES
                        (
                            $1,$2,$3,$4,
                            $5,$6,$7,
                            $8,$9,
                            $10,$10,$11
                        )
                    """,

                        line_id,
                        transfer_id,

                        line.get("ItemCode"),
                        line.get("ItemDescription"),

                        line.get(
                            "FromWarehouseCode"
                        ),

                        line.get(
                            "WarehouseCode"
                        ),

                        line.get("Quantity"),

                        "Y" if serials else "N",
                        "Y" if batches else "N",

                        user_id,
                        tenant_schema
                    )

                    # ==========================
                    # SERIALS
                    # ==========================

                    for serial in serials:

                        serial_seq = await conn.fetchval(f"""
                            SELECT nextval(
                                '"{tenant_schema}".ik_inventory_transfer_serial_seq'
                            )
                        """)

                        serial_id = (
                            f"INTSL_{serial_seq}"
                        )

                        await conn.execute(f"""
                            INSERT INTO
                            "{tenant_schema}".ik_it_serial_line
                            (
                                it_serial_line_id,
                                it_item_line_id,
                                it_id,
                                item_code,
                                internal_serial_number,
                                quantity,
                                from_wh_code,
                                to_wh_code,
                                created_by,
                                schema_id
                            )
                            VALUES
                            (
                                $1,$2,$3,$4,$5,
                                $6,$7,$8,$9,$10
                            )
                        """,

                            serial_id,
                            line_id,
                            transfer_id,

                            line.get("ItemCode"),

                            serial.get(
                                "InternalSerialNumber"
                            ),

                            serial.get(
                                "Quantity"
                            ),

                            line.get(
                                "FromWarehouseCode"
                            ),

                            line.get(
                                "WarehouseCode"
                            ),

                            user_id,
                            tenant_schema
                        )

                    # ==========================
                    # BATCHES
                    # ==========================

                    for batch in batches:

                        batch_seq = await conn.fetchval(f"""
                            SELECT nextval(
                                '"{tenant_schema}".ik_inventory_transfer_batch_seq'
                            )
                        """)

                        batch_id = (
                            f"INTBL_{batch_seq}"
                        )

                        await conn.execute(f"""
                            INSERT INTO
                            "{tenant_schema}".ik_it_batch_line
                            (
                                it_batch_line_id,
                                it_item_line_id,
                                it_id,
                                item_code,
                                batch_number,
                                quantity,
                                from_wh_code,
                                to_wh_code,
                                created_by,
                                schema_id
                            )
                            VALUES
                            (
                                $1,$2,$3,$4,$5,
                                $6,$7,$8,$9,$10
                            )
                        """,

                            batch_id,
                            line_id,
                            transfer_id,

                            line.get("ItemCode"),

                            batch.get(
                                "BatchNumber"
                            ),

                            batch.get(
                                "Quantity"
                            ),

                            line.get(
                                "FromWarehouseCode"
                            ),

                            line.get(
                                "WarehouseCode"
                            ),

                            user_id,
                            tenant_schema
                        )

                # =====================================
                # POST TO SAP
                # =====================================

                config = await get_sap_config_by_schema(
                    conn,
                    tenant_schema
                )

                sap_payload = copy.deepcopy(
                    payload
                )

                try:

                    print("===================================")
                    print("SAP STOCK TRANSFER PAYLOAD")
                    print("===================================")
                    print(sap_payload)

                    sap_response = await SAPApiClient.post_stock_transfer(
                        config,
                        sap_payload
                    )

                    print("===================================")
                    print("SAP STOCK TRANSFER RESPONSE")
                    print("===================================")
                    print(sap_response)

                    itr_id = payload.get("U_IKOPID")

                    if itr_id:
                        await conn.execute(f"""
                            UPDATE
                            "{tenant_schema}".ik_itr_header
                            SET
                                status = 'Close',
                                updated_at = NOW(),
                                updated_by = $1
                            WHERE itr_id = $2
                        """,
                            user_id,
                            itr_id
                        )

                    await conn.execute(f"""
                        UPDATE "{tenant_schema}".ik_it_header
                        SET
                            sap_docentry = $1,
                            sap_docnum = $2,
                            journal_remarks = $3,
                            sap_status = 'Posted',
                            status = 'Close',
                            updated_at = NOW(),
                            updated_by = $4
                        WHERE it_id = $5
                    """,
                        str(sap_response.get("DocEntry")),
                        str(sap_response.get("DocNum")),
                        sap_response.get("JournalMemo"),
                        user_id,
                        transfer_id
                    )

                    return {
                        "status": "success",
                        "transfer_id": transfer_id,
                        "sap_response": sap_response
                    }

                except Exception as e:

                    print("===================================")
                    print("SAP STOCK TRANSFER ERROR")
                    print("===================================")
                    print("ERROR TYPE:", type(e))
                    print("ERROR:", repr(e))
                    print("ERROR STRING:", str(e))

                    await conn.execute(f"""
                        UPDATE
                        "{tenant_schema}".ik_it_header
                        SET
                            sap_status = 'Failed',
                            updated_at = NOW(),
                            updated_by = $1
                        WHERE it_id = $2
                    """,
                        user_id,
                        transfer_id
                    )

                    raise HTTPException(
                        status_code=400,
                        detail=f"SAP Stock Transfer Failed: {str(e)}"
                    )
    # =====================================
    # RECENT STOCK TRANSFERS
    # =====================================
    @staticmethod
    async def get_recent_stock_transfers(
        request,
        db_pool,
        current_user,
        limit: int = 20
    ):

        tenant_schema = getattr(
            request.state,
            "schema"
        )

        user_id = str(
            current_user.get("user_id")
        )

        async with db_pool.acquire() as conn:

            rows = await conn.fetch(f'''

                SELECT

                    it_id,

                    it_date,

                    from_wh_code,

                    to_wh_code,

                    sap_docentry,

                    sap_status,

                    status,

                    created_at

                FROM
                "{tenant_schema}".ik_it_header

                WHERE created_by = $1

                ORDER BY created_at DESC

                LIMIT $2

            ''',

                user_id,
                limit
            )

            return {
                "status": "success",
                "count": len(rows),
                "data": [dict(row) for row in rows]
            }

    @staticmethod
    async def create_inventory_transfer_request(
        request,
        data,
        db_pool,
        current_user
    ):

        import json
        from datetime import datetime

        tenant_schema = getattr(
            request.state,
            "schema"
        )

        user_id = str(
            current_user.get("user_id")
        )

        schema_id = tenant_schema

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                # =====================================
                # DEBUG PAYLOAD
                # =====================================

                print("===================================")
                print("INVENTORY TRANSFER REQUEST PAYLOAD")
                print("===================================")
                print(data)

                # =====================================
                # VALIDATION
                # =====================================

                lines = data.get(
                    "StockTransferLines",
                    []
                )

                if not lines:
                    raise Exception(
                        "StockTransferLines required"
                    )

                # =====================================
                # DATE CONVERSION
                # =====================================
                from datetime import datetime
                itr_date = (
                    datetime.strptime(
                        data["DocDate"],
                        "%Y-%m-%d"
                    ).date()
                    if data.get("DocDate")
                    else None
                )

                due_date = (
                    datetime.strptime(
                        data["DueDate"],
                        "%Y-%m-%d"
                    ).date()
                    if data.get("DueDate")
                    else None
                )

                

                doc_date = (
                    datetime.strptime(
                        data.get("TaxDate")
                        or data.get("DocDate"),
                        "%Y-%m-%d"
                    ).date()
                    if (
                        data.get("TaxDate")
                        or data.get("DocDate")
                    )
                    else None
                )

                # =====================================
                # GENERATE ITR ID
                # =====================================

                seq = await conn.fetchval(f'''
                    SELECT nextval(
                        '"{tenant_schema}".ik_inventory_transfer_request_seq'
                    )
                ''')

                itr_id = (
                    f"ITRTH_{seq}"
                )

                print("===================================")
                print("BRANCH DETAILS")
                print("===================================")
                print("BPLID =", data.get("BPLID"))
                print("BPLID TYPE =", type(data.get("BPLID")))
                print("BPLName =", data.get("BPLName"))
                # =====================================
                # INSERT HEADER
                # =====================================

                await conn.execute(f'''
                    INSERT INTO
                    "{tenant_schema}".ik_itr_header
                    (
                        itr_id,
                        itr_date,
                        due_date,
                        doc_date,
                        branch,
                        branch_id,
                        from_wh_code,
                        to_wh_code,
                        remarks,
                        driver_name,
                        oil,
                        kilometer,
                        purpose,
                        created_by,
                        updated_by,
                        schema_id,
                        sap_status,
                        status
                    )
                    VALUES
                    (
                        $1,$2,$3,$4,
                        $5,$6,
                        $7,$8,
                        $9,

                        $10,$11,$12,$13,

                        $14,$14,$15,
                        'Pending',
                        'Open'
                    )
                ''',

                    itr_id,
                    itr_date,
                    due_date,
                    doc_date,
                    data.get("BPLName"),
                    str(data.get("BPLID"))
                    if data.get("BPLID") is not None
                    else None,
                    data.get("FromWarehouse"),
                    data.get("ToWarehouse"),
                    data.get("Comments"),
                    data.get("U_IKDN"),
                    data.get("U_IKOIL"),
                    data.get("U_IKKMS"),
                    data.get("U_IKPP"),
                    user_id,
                    schema_id
                )

                # =====================================
                # INSERT ITEM LINES
                # =====================================

                for line in lines:

                    print("================================")
                    print("CURRENT LINE")
                    print(json.dumps(line, indent=4))
                    print("================================")

                    print(
                        "SERIAL NUMBERS =",
                        line.get("SerialNumbers")
                    )

                    line_seq = await conn.fetchval(f'''
                        SELECT nextval(
                            '"{tenant_schema}".ik_inventory_transfer_request_line_seq'
                        )
                    ''')

                    itr_item_line_id = (
                        f"ITRIL_{line_seq}"
                    )

                    await conn.execute(f'''
                        INSERT INTO
                        "{tenant_schema}".ik_itr_item_line
                        (
                            itr_item_line_id,
                            itr_id,
                            item_code,
                            item_name,
                            from_wh_code,
                            to_wh_code,
                            qty,
                            created_by,
                            updated_by,
                            schema_id
                        )
                        VALUES
                        (
                            $1,$2,$3,$4,$5,$6,$7,
                            $8,$8,$9
                        )
                    ''',

                        itr_item_line_id,
                        itr_id,
                        line.get("ItemCode"),
                        line.get("ItemDescription"),
                        line.get("FromWarehouseCode"),
                        line.get("WarehouseCode"),
                        line.get("Quantity"),
                        user_id,
                        schema_id
                    )

                    # =====================================
                    # INSERT SERIALS
                    # =====================================

                    serials = line.get("SerialNumbers", [])

                    for serial in serials:

                        serial_seq = await conn.fetchval(f'''
                            SELECT nextval(
                                '"{tenant_schema}".ik_inventory_transfer_request_serial_seq'
                            )
                        ''')

                        itr_serial_line_id = f"ITRSL_{serial_seq}"

                        await conn.execute(f'''
                            INSERT INTO
                            "{tenant_schema}".ik_itr_serial_line
                            (
                                itr_serial_line_id,
                                itr_id,
                                itr_item_line_id,
                                serial_no,
                                mnf_serial_no,
                                qty,
                                created_by,
                                updated_by,
                                schema_id
                            )
                            VALUES
                            (
                                $1,$2,$3,$4,$5,$6,$7,$7,$8
                            )
                        ''',
                            itr_serial_line_id,
                            itr_id,
                            itr_item_line_id,
                            serial.get("InternalSerialNumber"),
                            serial.get("ManufacturerSerialNumber"),
                            float(serial.get("Quantity", 1)),
                            user_id,
                            schema_id
                        )

                # =====================================
                # SAP CONFIG
                # =====================================

                config = await get_sap_config_by_schema(
                    conn,
                    tenant_schema
                )

                print("========== FINAL PAYLOAD TO SAP ==========")
                print(json.dumps(data, indent=4))
                print("==========================================")

                try:

                    sap_response = await SAPApiClient.post_inventory_transfer_request(
                        config,
                        data
                    )

                    print("SAP RESPONSE =", sap_response)

                    # SAP returned error object
                    if (
                        isinstance(sap_response, dict)
                        and sap_response.get("error")
                    ):

                        await conn.execute(f'''
                            UPDATE "{tenant_schema}".ik_itr_header
                            SET
                                sap_status='Failed',
                                updated_at=NOW(),
                                updated_by=$1
                            WHERE itr_id=$2
                        ''',
                            user_id,
                            itr_id
                        )

                        raise HTTPException(
                            status_code=400,
                            detail=sap_response
                        )

                except HTTPException:
                    raise

                except Exception as e:

                    await conn.execute(f'''
                        UPDATE "{tenant_schema}".ik_itr_header
                        SET
                            sap_status='Failed',
                            updated_at=NOW(),
                            updated_by=$1
                        WHERE itr_id=$2
                    ''',
                        user_id,
                        itr_id
                    )

                    raise HTTPException(
                        status_code=400,
                        detail={
                            "status": "error",
                            "itr_id": itr_id,
                            "message": str(e)
                        }
                    )

                # =====================================
                # UPDATE HEADER
                # =====================================

                await conn.execute(f'''
                    UPDATE "{tenant_schema}".ik_itr_header
                    SET
                        sap_docentry=$1,
                        sap_docnum=$2,
                        series_id=$3,
                        journal_remarks=$4,
                        branch=$5,
                        branch_id=$6,
                        sap_status='Posted',
                        status='Open',
                        updated_at=NOW(),
                        updated_by=$7
                    WHERE itr_id=$8
                ''',

                    str(sap_response.get("DocEntry")),
                    str(sap_response.get("DocNum")),
                    sap_response.get("Series"),
                    sap_response.get("JournalMemo"),
                    sap_response.get("BPLName"),
                    str(sap_response.get("BPLID"))
                        if sap_response.get("BPLID")
                        else None,
                    user_id,
                    itr_id
                )

                return {
                    "status": "success",
                    "itr_id": itr_id,
                    "sap_docentry": sap_response.get(
                        "DocEntry"
                    ),
                    "sap_docnum": sap_response.get(
                        "DocNum"
                    ),
                    "sap_response": sap_response
                }

    @staticmethod
    async def is_bin_enabled(
        conn,
        tenant_schema: str,
        whs_code: str
    ):

        config = await get_sap_config_by_schema(
            conn,
            tenant_schema
        )

        data = await SAPApiClient.is_bin_enabled(
            config,
            whs_code
        )

        return data

    @staticmethod
    async def get_bin_details(
        conn,
        tenant_schema: str,
        item_code: str,
        whs_code: str
    ):

        config = await get_sap_config_by_schema(
            conn,
            tenant_schema
        )

        data = await SAPApiClient.get_bin_details(
            config,
            item_code,
            whs_code
        )

        return data

   
    # INVENTORY TRANSFER REQUEST SERIES
    # =====================================
    @staticmethod
    async def get_inventory_transfer_request_series(
        conn,
        tenant_schema: str
    ):

        config = await get_sap_config_by_schema(
            conn,
            tenant_schema
        )

        today = datetime.now().strftime(
            "%Y%m%d"
        )

        return await SAPApiClient.get_inventory_series(
            config=config,
            object_code="1250000001",
            date_f=today,
            date_t=today
        )

    # =====================================
    # STOCK TRANSFER SERIES
    # =====================================
    @staticmethod
    async def get_stock_transfer_series(
        conn,
        tenant_schema: str
    ):

        config = await get_sap_config_by_schema(
            conn,
            tenant_schema
        )

        today = datetime.now().strftime(
            "%Y%m%d"
        )

        return await SAPApiClient.get_inventory_series(
            config=config,
            object_code="67",
            date_f=today,
            date_t=today
        )

    @staticmethod
    async def get_itr_numbers(
        conn,
        tenant_schema: str,
        search: str = "",
        status: str = "",
        page: int = 1,
        per_page: int = 20
    ):

        conditions = [
            "sap_docentry IS NOT NULL",
            "status = 'Open'"
        ]

        values = []

        # -------------------------
        # SEARCH FILTER
        # -------------------------
        if search:

            conditions.append(f"""
            (
                itr_id ILIKE ${len(values)+1}
                OR sap_docentry ILIKE ${len(values)+1}
                OR sap_docnum ILIKE ${len(values)+1}
                OR remarks ILIKE ${len(values)+1}
                OR driver_name ILIKE ${len(values)+1}
                OR purpose ILIKE ${len(values)+1}
                OR sap_status ILIKE ${len(values)+1}
                OR status ILIKE ${len(values)+1}

                OR EXISTS
                (
                    SELECT 1
                    FROM "{tenant_schema}".ik_itr_item_line l
                    WHERE l.itr_id =
                        "{tenant_schema}".ik_itr_header.itr_id
                    AND
                    (
                        l.item_code ILIKE ${len(values)+1}
                        OR l.item_name ILIKE ${len(values)+1}
                    )
                )
            )
            """)

            values.append(f"%{search}%")

        where_clause = " AND ".join(
            conditions
        )

        # -------------------------
        # COUNT
        # -------------------------
        total_records = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM "{tenant_schema}".ik_itr_header
            WHERE {where_clause}
            """,
            *values
        )

        total_pages = (
            (total_records + per_page - 1)
            // per_page
        )

        offset = (
            (page - 1)
            * per_page
        )

        # -------------------------
        # DATA
        # -------------------------
        rows = await conn.fetch(
            f"""
            SELECT

                itr_id,
                series_id,

                itr_date,
                due_date,
                doc_date,

                branch,
                branch_id,

                from_wh_code,
                to_wh_code,

                remarks,
                journal_remarks,

                driver_name,
                oil,
                kilometer,
                purpose,

                sap_docentry,
                sap_docnum,

                sap_status,
                status,

                created_at,
                updated_at,

                created_by,
                updated_by

            FROM "{tenant_schema}".ik_itr_header

            WHERE {where_clause}

            ORDER BY created_at DESC

            LIMIT ${len(values)+1}
            OFFSET ${len(values)+2}
            """,
            *values,
            per_page,
            offset
        )

        return {
            "status": "success",
            "message": "ITR records fetched successfully",
            "meta": {
                "page": page,
                "per_page": per_page,
                "total_records": total_records,
                "total_pages": total_pages
            },
            "count": len(rows),
            "data": [
                dict(row)
                for row in rows
            ]
        }

    @staticmethod
    async def get_itr_details(
        conn,
        tenant_schema: str,
        itr_id: str
    ):

        header = await conn.fetchrow(f'''
            SELECT *
            FROM "{tenant_schema}".ik_itr_header
            WHERE itr_id = $1
        ''', itr_id)

        if not header:
            raise HTTPException(
                status_code=404,
                detail="ITR not found"
            )

        lines = await conn.fetch(f'''
            SELECT *
            FROM "{tenant_schema}".ik_itr_item_line
            WHERE itr_id = $1
            ORDER BY itr_item_line_id
        ''', itr_id)

        header_data = dict(header)

        header_data["created_date"] = (
            header_data["created_at"].strftime("%Y-%m-%d")
            if header_data.get("created_at")
            else None
        )

        header_data["updated_date"] = (
            header_data["updated_at"].strftime("%Y-%m-%d")
            if header_data.get("updated_at")
            else None
        )

        line_data = []

        for line in lines:

            serials = await conn.fetch(f'''
                SELECT
                    itr_serial_line_id,
                    itr_id,
                    itr_item_line_id,
                    serial_no,
                    mnf_serial_no,
                    qty,
                    created_at,
                    created_by,
                    updated_at,
                    updated_by,
                    schema_id
                FROM "{tenant_schema}".ik_itr_serial_line
                WHERE itr_item_line_id = $1
                ORDER BY itr_serial_line_id
            ''', line["itr_item_line_id"])

            row = dict(line)

            row["created_date"] = (
                row["created_at"].strftime("%Y-%m-%d")
                if row.get("created_at")
                else None
            )

            row["updated_date"] = (
                row["updated_at"].strftime("%Y-%m-%d")
                if row.get("updated_at")
                else None
            )

            row["serial_numbers"] = []

            for serial in serials:
                
                

                serial_data = dict(serial)

                serial_data["created_date"] = (
                    serial_data["created_at"].strftime("%Y-%m-%d")
                    if serial_data.get("created_at")
                    else None
                )

                serial_data["updated_date"] = (
                    serial_data["updated_at"].strftime("%Y-%m-%d")
                    if serial_data.get("updated_at")
                    else None
                )

                row["serial_numbers"].append(
                    serial_data
                )

                print("SERIAL ROW =", dict(serial))

            line_data.append(row)

        return {
            "header": header_data,
            "lines": line_data
        }
        @staticmethod
        async def get_bin_details(
            conn,
            item_code: str,
            whs_code: str
        ):

            query = f"""
                SELECT
                    bin_id,
                    bin_code,
                    warehouse_code,
                    is_active
                FROM ik_bin
                WHERE
                    warehouse_code = $1
                    AND is_active = TRUE
                ORDER BY bin_code
            """

            return await conn.fetch(
                query,
                whs_code
            )


    @staticmethod
    async def get_branch_by_warehouse(
        conn,
        tenant_schema: str,
        warehouse_code: str
    ):
        return await conn.fetchrow(
            f"""
            SELECT
                w.warehouse_code,
                w.warehouse_name,
                w.branch_id,
                b.branch_name
            FROM "{tenant_schema}".ik_warehouse w
            LEFT JOIN "{tenant_schema}".ik_branch b
                ON b.branch_id = w.branch_id
            WHERE w.warehouse_code = $1
            """,
            warehouse_code
        )

    @staticmethod
    async def get_recent_stock_transfers(
        request,
        db_pool,
        current_user,
        search: str = "",
        status: str = "",
        from_date: str = None,
        to_date: str = None,
        page: int = 1,
        per_page: int = 20
    ):

        tenant_schema = getattr(
            request.state,
            "schema"
        )

        user_id = str(
            current_user.get("user_id")
        )

        async with db_pool.acquire() as conn:

            conditions = [
                "created_by = $1"
            ]

            values = [user_id]

            # -------------------------
            # STATUS FILTER
            # -------------------------
            if status:
                conditions.append(
                    f"status = ${len(values)+1}"
                )
                values.append(status)

            # -------------------------
            # DATE FILTER
            # -------------------------
            if from_date:
                conditions.append(
                    f"it_date >= ${len(values)+1}"
                )
                values.append(from_date)

            if to_date:
                conditions.append(
                    f"it_date <= ${len(values)+1}"
                )
                values.append(to_date)

            # -------------------------
            # SEARCH FILTER
            # -------------------------
            if search:

                conditions.append(f"""
                (
                    it_id ILIKE ${len(values)+1}
                    OR from_wh_code ILIKE ${len(values)+1}
                    OR to_wh_code ILIKE ${len(values)+1}
                    OR sap_docentry ILIKE ${len(values)+1}
                    OR remarks ILIKE ${len(values)+1}
                    OR driver_name ILIKE ${len(values)+1}
                    OR purpose ILIKE ${len(values)+1}
                    OR sap_status ILIKE ${len(values)+1}
                    OR status ILIKE ${len(values)+1}

                    OR EXISTS
                    (
                        SELECT 1
                        FROM "{tenant_schema}".ik_it_item_line l
                        WHERE l.it_id = "{tenant_schema}".ik_it_header.it_id
                        AND
                        (
                            l.item_code ILIKE ${len(values)+1}
                            OR l.item_name ILIKE ${len(values)+1}
                        )
                    )

                    OR EXISTS
                    (
                        SELECT 1
                        FROM "{tenant_schema}".ik_it_serial_line s
                        WHERE s.it_id = "{tenant_schema}".ik_it_header.it_id
                        AND s.internal_serial_number ILIKE ${len(values)+1}
                    )

                    OR EXISTS
                    (
                        SELECT 1
                        FROM "{tenant_schema}".ik_it_batch_line b
                        WHERE b.it_id = "{tenant_schema}".ik_it_header.it_id
                        AND b.batch_number ILIKE ${len(values)+1}
                    )
                )
                """)

                values.append(f"%{search}%")

            where_clause = " AND ".join(
                conditions
            )

            # -------------------------
            # TOTAL COUNT
            # -------------------------
            count_query = f"""
                SELECT COUNT(*)
                FROM "{tenant_schema}".ik_it_header
                WHERE {where_clause}
            """

            total_records = await conn.fetchval(
                count_query,
                *values
            )

            total_pages = (
                (total_records + per_page - 1)
                // per_page
            )

            offset = (
                (page - 1)
                * per_page
            )

            # -------------------------
            # DATA QUERY
            # -------------------------
            query = f"""
                SELECT

                    it_id,
                    series_id,

                    it_date,
                    due_date,
                    doc_date,

                    branch,
                    branch_id,

                    from_wh_code,
                    to_wh_code,

                    remarks,
                    journal_remarks,

                    driver_name,
                    oil,
                    kilometer,
                    purpose,

                    sap_docentry,

                    sap_status,
                    status,

                    created_at,
                    updated_at,

                    created_by,
                    updated_by

                FROM
                "{tenant_schema}".ik_it_header

                WHERE {where_clause}

                ORDER BY created_at DESC

                LIMIT ${len(values)+1}
                OFFSET ${len(values)+2}
            """

            rows = await conn.fetch(
                query,
                *values,
                per_page,
                offset
            )

            return {
                "status": "success",
                "message": "Stock transfers fetched successfully",
                "meta": {
                    "page": page,
                    "per_page": per_page,
                    "total_records": total_records,
                    "total_pages": total_pages
                },
                "count": len(rows),
                "data": [
                    dict(row)
                    for row in rows
                ]
            }

    @staticmethod
    async def get_stock_transfer_details(
        conn,
        tenant_schema: str,
        it_id: str
    ):

        header = await conn.fetchrow(
            f"""
            SELECT *
            FROM "{tenant_schema}".ik_it_header
            WHERE it_id = $1
            """,
            it_id
        )

        if not header:
            raise HTTPException(
                status_code=404,
                detail="Stock Transfer not found"
            )

        header_data = dict(header)

        header_data["created_date"] = (
            header_data["created_at"].strftime("%Y-%m-%d")
            if header_data.get("created_at")
            else None
        )

        header_data["updated_date"] = (
            header_data["updated_at"].strftime("%Y-%m-%d")
            if header_data.get("updated_at")
            else None
        )

        lines = await conn.fetch(
            f"""
            SELECT *
            FROM "{tenant_schema}".ik_it_item_line
            WHERE it_id = $1
            ORDER BY it_item_line_id
            """,
            it_id
        )

        line_data = []

        for line in lines:

            row = dict(line)

            row["created_date"] = (
                row["created_at"].strftime("%Y-%m-%d")
                if row.get("created_at")
                else None
            )

            row["updated_date"] = (
                row["updated_at"].strftime("%Y-%m-%d")
                if row.get("updated_at")
                else None
            )

            # ==========================
            # SERIALS
            # ==========================
            serials = await conn.fetch(
                f"""
                SELECT
                    it_serial_line_id,
                    internal_serial_number,
                    quantity,
                    from_wh_code,
                    to_wh_code,
                    created_at
                FROM "{tenant_schema}".ik_it_serial_line
                WHERE it_item_line_id = $1
                ORDER BY it_serial_line_id
                """,
                line["it_item_line_id"]
            )

            row["serial_numbers"] = [
                dict(serial)
                for serial in serials
            ]

            # ==========================
            # BATCHES
            # ==========================
            batches = await conn.fetch(
                f"""
                SELECT
                    it_batch_line_id,
                    batch_number,
                    quantity,
                    from_wh_code,
                    to_wh_code,
                    created_at
                FROM "{tenant_schema}".ik_it_batch_line
                WHERE it_item_line_id = $1
                ORDER BY it_batch_line_id
                """,
                line["it_item_line_id"]
            )

            row["batch_numbers"] = [
                dict(batch)
                for batch in batches
            ]

            line_data.append(row)

        return {
            "status": "success",
            "header": header_data,
            "lines": line_data
        }