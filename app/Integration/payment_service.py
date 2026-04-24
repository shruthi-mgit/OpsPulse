from app.Integration.sap_api_client import SAPApiClient
from app.config.config_service import get_sap_config
from app.Integration.sap_session_cache import get_session, set_session
from fastapi import HTTPException
import logging
from datetime import datetime
from datetime import date

logger = logging.getLogger("sap-payment-service")



# =========================
# COMMON RESPONSE FORMAT
# =========================
def success_response(data):
    return {
        "status": "success",
        "data": data
    }


async def generate_id(conn, tenant_schema, seq_name, prefix):

    seq = await conn.fetchval(
        f'SELECT nextval(\'"{tenant_schema}".{seq_name}\')'
    )

    return f"{prefix}_{str(seq).zfill(14)}"

async def generate_error_id(conn, tenant_schema):
    last_id = await conn.fetchval(f'''
        SELECT error_id FROM "{tenant_schema}".ik_error
        ORDER BY error_id DESC
        LIMIT 1
    ''')

    if last_id:
        num = int(last_id.split("_")[1]) + 1
    else:
        num = 1

    return f"ERROR_{str(num).zfill(14)}"

async def log_error(conn, tenant_schema, module, operation, ref_id, error_msg, payload):
    try:
        error_id = await generate_error_id(conn, tenant_schema)

        await conn.execute(f"""
            INSERT INTO "{tenant_schema}".ik_error
            (error_id, schema_id, module, operation, ref_id, error_desc, payload)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
        """,
            error_id,
            tenant_schema,
            module,
            operation,
            ref_id,
            error_msg,
            payload
        )
    except Exception as log_ex:
        logger.error(f"Failed to log error: {str(log_ex)}")

class SapPaymentService:

    # =========================
    # CUSTOMER DETAILS
    # =========================
    @staticmethod
    async def get_customers(conn, tenant_schema: str, search: str = ""):
        try:
            query = f"""
                SELECT 
                    bp_id AS customer_code,
                    bp_name AS customer_name,
                    city,
                    country,
                    email,
                    balance
                FROM "{tenant_schema}".ik_bp
                WHERE bp_type = 'C'
            """

            values = []
            param_index = 1

            if search:
                query += f" AND LOWER(bp_name) LIKE LOWER(${param_index})"
                values.append(f"%{search}%")
                param_index += 1

            query += " ORDER BY bp_name"

            rows = await conn.fetch(query, *values)

            data = [
                {
                    "customer_code": r["customer_code"],
                    "customer_name": r["customer_name"],
                    "city": r.get("city"),
                    "country": r.get("country"),
                    "email": r.get("email"),
                    "balance": r.get("balance")
                }
                for r in rows
            ]

            return success_response(data)

        except Exception:
            logger.exception("Error fetching customers")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": "Failed to fetch customers"}
            )

    # =========================
    # CUSTOMER INVOICES
    # =========================
    @staticmethod
    async def get_invoices(customer_code: str, request, db_pool):
        try:
            async with db_pool.acquire() as conn:

                from app.config.config_service import get_sap_config
                config = await get_sap_config(conn)
                
                data = await SAPApiClient.get_customer_due_invoices(customer_code, config)

                formatted = [
                    {
                        "doc_entry": i.get("DocEntry"),
                        "doc_num": i.get("DocNum"),
                        "document_type": i.get("DocumentType"),
                        "customer_code": i.get("CustomerCode"),
                        "customer_name": i.get("CustomerName"),
                        "balance_due": i.get("BalancDue_LC"),
                        "overdue_days": i.get("OverdueDays"),
                    }
                    for i in (data or [])
                ]

                return success_response(formatted)

        except Exception as e:
            logger.exception("Error fetching invoices")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": f"Failed to fetch invoice data: {str(e)}"}
            )

    # =========================
    # GL ACCOUNTS
    # =========================
    @staticmethod
    async def get_gl_accounts(conn, tenant_schema: str, search: str = ""):
        try:
            query = f"""
                SELECT 
                    account_id AS account_code,
                    account_name,
                    is_active,
                    balance
                FROM "{tenant_schema}".ik_glaccount
                WHERE is_active = TRUE
            """

            values = []
            param_index = 1

            if search:
                query += f" AND LOWER(account_name) LIKE LOWER(${param_index})"
                values.append(f"%{search}%")
                param_index += 1

            query += " ORDER BY account_name"

            rows = await conn.fetch(query, *values)

            data = [
                {
                    "account_code": r["account_code"],
                    "account_name": r["account_name"],
                    "is_active": r["is_active"],
                    "balance": r["balance"]
                }
                for r in rows
            ]

            return success_response(data)

        except Exception:
            logger.exception("Error fetching GL accounts")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": "Failed to fetch GL accounts"}
            )

    # =========================
    # BANKS
    # =========================
    @staticmethod
    async def get_banks(conn, tenant_schema: str, search: str = ""):
        try:
            query = f"""
                SELECT 
                    bank_id AS bank_code,
                    bank_name
                FROM "{tenant_schema}".ik_bank
                WHERE 1=1
            """

            values = []
            param_index = 1

            if search:
                query += f" AND LOWER(bank_name) LIKE LOWER(${param_index})"
                values.append(f"%{search}%")
                param_index += 1

            query += " ORDER BY bank_name"

            rows = await conn.fetch(query, *values)

            data = [
                {
                    "bank_code": r["bank_code"],
                    "bank_name": r["bank_name"]
                }
                for r in rows
            ]

            return success_response(data)

        except Exception:
            logger.exception("Error fetching banks")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": "Failed to fetch banks"}
            )

    # =========================
    # SUPPLIERS
    # =========================
    @staticmethod
    async def get_suppliers(conn, tenant_schema: str, search: str = ""):
        try:
            query = f"""
                SELECT 
                    bp_id AS supplier_code,
                    bp_name AS supplier_name,
                    city,
                    country,
                    email,
                    balance
                FROM "{tenant_schema}".ik_bp
                WHERE bp_type = 'S'
            """

            values = []
            param_index = 1

            if search:
                query += f" AND bp_name ILIKE ${param_index}"
                values.append(f"%{search}%")
                param_index += 1

            query += " ORDER BY bp_name"

            rows = await conn.fetch(query, *values)

            data = [
                {
                    "supplier_code": r["supplier_code"],
                    "supplier_name": r["supplier_name"],
                    "city": r.get("city"),
                    "country": r.get("country"),
                    "email": r.get("email"),
                    "balance": r.get("balance")
                }
                for r in rows
            ]

            return success_response(data)

        except Exception:
            logger.exception("Error fetching suppliers")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": "Failed to fetch suppliers"}
            )
    # =========================
    # SUPPLIER INVOICES
    # =========================
    @staticmethod
    async def get_supplier_invoices(vendor_code: str, request, db_pool):

        try:
            from app.config.config_service import get_sap_config

            async with db_pool.acquire() as conn:
                config = await get_sap_config(conn)

            data = await SAPApiClient.get_vendor_due_invoices(vendor_code, config)

            formatted = [
                {
                    "doc_entry": i.get("DocEntry"),
                    "doc_num": i.get("DocNum"),
                    "document_type": i.get("DocumentType"),
                    "vendor_code": i.get("VendorCode"),
                    "vendor_name": i.get("VendorName"),
                    "balance_due": i.get("BalancDue_LC"),
                    "overdue_days": i.get("OverdueDays"),
                }
                for i in (data or [])
            ]

            return success_response(formatted)

        except Exception:
            logger.exception("Error fetching vendor invoices")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": "Failed to fetch vendor data"}
            )
    # =========================
    # BRANCHES
    # =========================
    @staticmethod
    async def get_branches(conn, tenant_schema: str, search: str = ""):
        try:
            query = f"""
                SELECT branch_id, branch_name
                FROM {tenant_schema}.ik_branch
                WHERE is_active = true
            """

            params = []

            if search:
                query += " AND LOWER(branch_name) LIKE LOWER($1)"
                params.append(f"%{search}%")

            rows = await conn.fetch(query, *params)

            formatted = [
                {
                    "branch_code": row["branch_id"],   # keep as string
                    "branch_name": row["branch_name"],
                }
                for row in rows
            ]

            return success_response(formatted)

        except Exception:
            logger.exception("Error fetching branches from DB")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": "Failed to fetch branches"}
            )
    
    @staticmethod
    def get_check_account(bank_code, bank_name, gl_accounts):

        # ✅ PRIORITY 1: Use BankCode (BEST MATCH)
        if bank_code:
            bank_code = bank_code.lower()

            for acc in gl_accounts:
                acc_name = acc["account_name"].lower()

                # Example: SBIN → match "state bank of india"
                if bank_code in acc_name:
                    return acc["account_code"]

                # Example: DEUT0019 → match last 4 digits (0019)
                if len(bank_code) >= 4:
                    suffix = bank_code[-4:]
                    if suffix in acc_name:
                        return acc["account_code"]

        # ✅ PRIORITY 2: fallback to BankName
        if bank_name:
            bank_name_lower = bank_name.lower()

            for acc in gl_accounts:
                if bank_name_lower in acc["account_name"].lower():
                    return acc["account_code"]

        return None



    @staticmethod
    async def create_incoming_payment(request, data, db_pool, current_user):

        tenant_schema = getattr(request.state, "schema")
        user_id = str(current_user.get("user_id"))

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                # -------------------------
                # READ INPUT
                # -------------------------
                payment_type_ui = data.get("payment_type")
                invoices = data.get("invoices") or []
                accounts = data.get("accounts") or []
                payments = data.get("payments") or {}

                payment_date_str = data.get("payment_date")
                if not payment_date_str:
                    raise HTTPException(400, "payment_date is required")

                payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()

                user_remark = (data.get("remarks") or "").strip()

                system_remark = "Posted from PayOpsB1"

                final_remarks = system_remark

                if user_remark:
                    final_remarks += f" - {user_remark}"
                # -------------------------
                # VALIDATION
                # -------------------------
                if payment_type_ui == "Customer":

                    if not data.get("customer_id"):
                        raise HTTPException(400, "Customer required")

                    if not invoices:
                        raise HTTPException(400, "Invoices required")

                    if "accounts" in data:
                        raise HTTPException(400, "Accounts not allowed for Customer")

                elif payment_type_ui == "Account":

                    if not accounts:
                        raise HTTPException(400, "Accounts required")

                    if "invoices" in data:
                        raise HTTPException(400, "Invoices not allowed for Account")

                else:
                    raise HTTPException(400, "Invalid payment type")

                if not payments:
                    raise HTTPException(400, "At least one payment method required")

                # -------------------------
                # TOTAL CALCULATION
                # -------------------------
                inv_total = sum(float(i.get("total_amount", 0)) for i in invoices)
                acc_total = sum(float(a.get("total_amount", 0)) for a in accounts)

                payment_total = 0

                if payments.get("cash"):
                    payment_total += float(payments["cash"].get("amount", 0))

                if payments.get("transfer"):
                    payment_total += float(payments["transfer"].get("amount", 0))

                if payments.get("card"):
                    payment_total += sum(float(c.get("CreditSum", 0)) for c in payments["card"])

                if payments.get("checks"):
                    payment_total += sum(float(c.get("CheckSum", 0)) for c in payments["checks"])

                expected_total = inv_total if payment_type_ui == "Customer" else acc_total

                # -------------------------
                # ON ACCOUNT LOGIC FIX
                # -------------------------
                is_on_account = False
                payment_on_account = None

                if payment_type_ui == "Account":
                    is_on_account = True
                    payment_on_account = float(expected_total)
        
                if round(payment_total, 2) != round(expected_total, 2):
                    raise HTTPException(400, "Payment total mismatch")

                # -------------------------
                # GENERATE PAYMENT ID
                # -------------------------
                payment_id = str(await generate_id(
                    conn, tenant_schema, "ik_inc_payment_seq", "INCPT"
                ))

                # -------------------------
                # INSERT HEADER
                # -------------------------
                await conn.execute(f'''
                    INSERT INTO "{tenant_schema}".ik_inc_payment_header
                    (
                        payment_id, payment_date, customer_id, customer_name,
                        payment_type, remarks, status,
                        created_by, updated_by, schema_id, document_total,
                        is_payment_onaccount,
                        payment_on_account
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,'Open',$7,$7,$8,$9,$10,$11)
                ''',
                    payment_id,
                    payment_date,
                    data.get("customer_id") if payment_type_ui == "Customer" else None,
                    data.get("customer_name") if payment_type_ui == "Customer" else None,
                    payment_type_ui,
                    final_remarks,
                    user_id,
                    tenant_schema,
                    expected_total,
                    is_on_account,
                    payment_on_account
                )

                # -------------------------
                # INSERT INVOICES
                # -------------------------
                if payment_type_ui == "Customer":
                    for inv in invoices:

                        line_id = str(await generate_id(
                            conn, tenant_schema, "ik_inc_payment_line_seq", "INCPL"
                        ))

                        await conn.execute(f'''
                            INSERT INTO "{tenant_schema}".ik_inc_payment_inv_line
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                        ''',
                            line_id,
                            payment_id,
                            inv.get("doc_type"),
                            str(inv.get("doc_entry")),
                            inv.get("doc_num"),
                            inv.get("balance_due"),
                            inv.get("total_amount"),
                            inv.get("overdue_days"),
                            tenant_schema
                        )

                # -------------------------
                # INSERT ACCOUNTS
                # -------------------------
                if payment_type_ui == "Account":
                    for acc in accounts:

                        line_id = str(await generate_id(
                            conn, tenant_schema, "ik_inc_payment_acct_line_seq", "INCAL"
                        ))

                        await conn.execute(f'''
                            INSERT INTO "{tenant_schema}".ik_inc_payment_acct_line
                            VALUES ($1,$2,$3,$4,$5,$6,$7)
                        ''',
                            line_id,
                            payment_id,
                            acc.get("account_id"),
                            acc.get("account_name"),
                            acc.get("remarks"),
                            acc.get("total_amount"),
                            tenant_schema
                        )

                # -------------------------
                # BUILD SAP PAYLOAD
                # -------------------------
                if payment_type_ui == "Customer":
                    sap_payload = {
                        "DocType": "rCustomer",
                        "DocDate": payment_date_str,
                        "TaxDate": payment_date_str,
                        "DueDate": payment_date_str,
                        "CardCode": data["customer_id"],
                        "Remarks": final_remarks,
                        "PaymentInvoices": [
                            {
                                "DocEntry": int(inv["doc_entry"]),
                                "SumApplied": float(inv["total_amount"])
                            }
                            for inv in invoices
                        ]
                    }
                else:
                    sap_payload = {
                        "DocType": "rAccount",
                        "DocDate": payment_date_str,
                        "TaxDate": payment_date_str,
                        "DueDate": payment_date_str,
                        "Remarks": final_remarks,
                        "PaymentAccounts": [
                            {
                                "AccountCode": acc["account_id"],
                                "SumPaid": float(acc["total_amount"])
                            }
                            for acc in accounts
                        ]
                    }

                # -------------------------
                # INSERT PAYMENT MEANS (INCOMING)
                # -------------------------
                if payments:

                    pay_line_id = str(await generate_id(
                        conn, tenant_schema,
                        "ik_inc_payment_paymeans_seq", "INCPM"
                    ))

                    cash_account = None
                    cash_amount = None
                    bank_account = None
                    bank_amount = None
                    transfer_date = None
                    cheque_account = None
                    cheque_no = None
                    cheque_amount = None
                    cheque_duedate = None
                    bank_name = None


                    def to_str(val):
                        return str(val) if val is not None else None

                    if payments.get("cash"):
                        cash_account = to_str(payments["cash"].get("account_id"))
                        cash_amount = float(payments["cash"].get("amount", 0))

                    if payments.get("transfer"):
                        bank_account = to_str(payments["transfer"].get("account_id"))
                        bank_amount = float(payments["transfer"].get("amount", 0))
                        transfer_date = payment_date if isinstance(payment_date, date) else None   

                    if payments.get("checks"):
                        chk = payments["checks"][0]
                        cheque_no = to_str(chk.get("CheckNumber"))
                        cheque_amount = float(chk.get("CheckSum", 0))
                        cheque_duedate = payment_date if isinstance(payment_date, date) else None  
                        bank_name = to_str(
                            chk.get("BankName") or 
                            chk.get("bank_name") or
                            chk.get("banks") or 
                            chk.get("bank") or
                            chk.get("bank_code") or
                            chk.get("bankName") or
                            chk.get("BankCode") or 
                            "bankname"
                        )          
                        cheque_account = to_str(chk.get("CheckAccount"))  

                    await conn.execute(f'''
                        INSERT INTO "{tenant_schema}".ik_inc_payment_paymeans_line
                        (
                            payment_line_id, payment_id,
                            cheque_account, cheque_no, cheque_duedate, bank_name, cheque_amount,
                            cash_account, cash_amount,
                            bank_account, transfer_date, bank_amount,
                            schema_id
                        )
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                    ''',
                        pay_line_id,
                        payment_id,
                        cheque_account,
                        cheque_no,
                        cheque_duedate,
                        bank_name,
                        cheque_amount,
                        cash_account,
                        cash_amount,
                        bank_account,
                        transfer_date,
                        bank_amount,
                        tenant_schema
                    )
                # -------------------------
                # PAYMENT MEANS
                # -------------------------
                if payments.get("cash"):
                    sap_payload["CashAccount"] = payments["cash"]["account_id"]
                    sap_payload["CashSum"] = float(payments["cash"]["amount"])

                if payments.get("transfer"):
                    sap_payload["TransferAccount"] = payments["transfer"]["account_id"]
                    sap_payload["TransferSum"] = float(payments["transfer"]["amount"])
                    sap_payload["TransferDate"] = payment_date_str

                if payments.get("card"):
                    sap_payload["PaymentCreditCards"] = payments["card"]

                if payments.get("checks"):
                    check = payments["checks"][0]

                    gl_rows = await conn.fetch(f'''
                        SELECT account_id AS account_code, account_name
                        FROM "{tenant_schema}".ik_glaccount
                        WHERE is_active = TRUE
                    ''')

                    gl_accounts = [dict(r) for r in gl_rows]

                    bank_code = (
                        check.get("BankCode") or
                        check.get("bank_code") or
                        check.get("bankCode")
                    )

                    bank_name = (
                        check.get("BankName") or
                        check.get("bank_name") or
                        check.get("bankName")
                    )

                    check_account = SapPaymentService.get_check_account(
                        bank_code,
                        bank_name,
                        gl_accounts
                    )

                    if not check_account:
                        raise HTTPException(400, f"No GL account mapped for bank: {check.get('BankName')}")

                    sap_payload["CheckAccount"] = check_account

                    sap_payload["PaymentChecks"] = [{
                        "DueDate": payment_date_str,
                        "CheckNumber": check["CheckNumber"],
                        "BankCode": check.get("BankCode"),
                        "CheckSum": float(check["CheckSum"]),
                        "CountryCode": check.get("CountryCode", "IN"),
                        "CheckAccount": check_account
                    }]

                # -------------------------
                # CALL SAP
                # -------------------------
                from app.config.config_service import get_sap_config
                config = await get_sap_config(conn)

                try:
                    sap_res = await SAPApiClient.post_incoming_payment(config, sap_payload)

                    import json
                    print("SAP RESPONSE:", json.dumps(sap_res, indent=2))

                    await conn.execute(f'''
                        UPDATE "{tenant_schema}".ik_inc_payment_header
                        SET status='Open', sap_docentry=$1, updated_at=NOW()
                        WHERE payment_id=$2
                    ''',
                        str(sap_res.get("DocEntry")),
                        payment_id
                    )

                    return {
                        "status": "success",
                        "payment_id": payment_id,
                        "sap_docentry": sap_res.get("DocEntry"),
                        "sap_payload": sap_payload, 
                        "sap_response": sap_res 
                    }

                except Exception as e:

                    await conn.execute(f'''
                        UPDATE "{tenant_schema}".ik_inc_payment_header
                        SET status='Failed', updated_at=NOW()
                        WHERE payment_id=$1
                    ''', payment_id)

                    # ✅ LOG ERROR
                    await log_error(
                        conn,
                        tenant_schema,
                        module="INCOMING_PAYMENT",
                        operation="SAP_POST",
                        ref_id=payment_id,
                        error_msg=str(e),
                        payload=sap_payload
                    )

                    return {
                        "status": "error",
                        "error": str(e),
                        "payment_id": payment_id,
                        "sap_payload": sap_payload,
                        "sap_response": str(e)
                    }


    @staticmethod
    async def create_outgoing_payment(request, data, db_pool, current_user):

        tenant_schema = getattr(request.state, "schema")
        user_id = str(current_user.get("user_id"))

        async with db_pool.acquire() as conn:
            async with conn.transaction():

                # -------------------------
                # INPUT
                # -------------------------
                invoices = data.get("invoices", [])
                accounts = data.get("accounts", [])
                payments = data.get("payments", {})
                payment_type = data.get("payment_type")

                # -------------------------
                # VALIDATION
                # -------------------------
                if payment_type not in ["Vendor", "Account"]:
                    raise HTTPException(400, "Invalid payment type")

                if payment_type == "Account" and not accounts:
                    raise HTTPException(400, "Accounts required for account payment")

                if not payments:
                    raise HTTPException(400, "At least one payment method required")

                # -------------------------
                # CALCULATE TOTALS
                # -------------------------
                inv_total = sum(float(i.get("total_amount", 0)) for i in invoices)
                acc_total = sum(float(a.get("total_amount", 0)) for a in accounts)

                payment_total = 0

                if payments.get("cash"):
                    payment_total += float(payments["cash"].get("amount", 0))

                if payments.get("transfer"):
                    payment_total += float(payments["transfer"].get("amount", 0))

                if payments.get("card"):
                    payment_total += sum(float(c.get("CreditSum", 0)) for c in payments["card"])

                if payments.get("checks"):
                    payment_total += sum(float(c.get("CheckSum", 0)) for c in payments["checks"])

                # -------------------------
                # FINAL TOTAL LOGIC
                # -------------------------
                if payment_type == "Vendor":
                    total_amount = inv_total if invoices else payment_total
                else:
                    total_amount = acc_total
                is_on_account = True if payment_type == "Account" else False
                payment_onaccount = float(total_amount) if is_on_account else None

                # -------------------------
                # VALIDATE TOTAL
                # -------------------------
                if round(payment_total, 2) != round(total_amount, 2):
                    raise HTTPException(400, "Payment total mismatch")

                # -------------------------
                # GENERATE PAYMENT ID
                # -------------------------
                payment_id = str(await generate_id(
                    conn,
                    tenant_schema,
                    "ik_out_payment_seq",
                    "OUTPT"
                ))

                # -------------------------
                # INSERT HEADER
                # -------------------------
                await conn.execute(f'''
                    INSERT INTO "{tenant_schema}".ik_out_payment_header
                    (
                        payment_id, payment_date,
                        vendor_id, vendor_name,
                        payment_type, remarks,
                        status, created_by, updated_by,
                        schema_id, document_total,
                        is_payment_onaccount,
                        payment_onaccount
                    )
                    VALUES ($1, CURRENT_DATE, $2, $3, $4, $5,
                            'Open', $6, $6, $7, $8,
                            $9, $10)
                ''',
                    payment_id,
                    data.get("vendor_id") if payment_type == "Vendor" else None,
                    data.get("vendor_name") if payment_type == "Vendor" else None,
                    payment_type,
                    data.get("remarks"),
                    user_id,
                    tenant_schema,
                    total_amount,
                    is_on_account,
                    payment_onaccount
                )

                # -------------------------
                # INSERT INVOICE LINES
                # -------------------------
                if payment_type == "Vendor" and invoices:
                    for inv in invoices:
                        line_id = str(await generate_id(
                            conn, tenant_schema,
                            "ik_out_payment_line_seq", "OUTPL"
                        ))

                        await conn.execute(f'''
                            INSERT INTO "{tenant_schema}".ik_out_payment_inv_line
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                        ''',
                            line_id,
                            payment_id,
                            inv.get("doc_type"),
                            str(inv.get("doc_entry")),
                            inv.get("doc_num"),
                            inv.get("balance_due"),
                            inv.get("total_amount"),
                            inv.get("overdue_days"),
                            tenant_schema
                        )

                # -------------------------
                # INSERT ACCOUNT LINES
                # -------------------------
                if payment_type == "Account":
                    for acc in accounts:
                        line_id = str(await generate_id(
                            conn, tenant_schema,
                            "ik_out_payment_line_seq", "OUTPL"
                        ))

                        await conn.execute(f'''
                            INSERT INTO "{tenant_schema}".ik_out_payment_acct_line
                            VALUES ($1,$2,$3,$4,$5,$6,$7)
                        ''',
                            line_id,
                            payment_id,
                            str(acc["account_id"]),
                            acc["account_name"],
                            acc.get("remarks"),
                            acc["total_amount"],
                            tenant_schema
                        )

                # -------------------------
                # PREPARE SAP PAYLOAD
                # -------------------------
                payment_date = data.get("payment_date")

                user_remark = (data.get("remarks") or "").strip()

                system_remark = "Auto generated by Payops-B1"

                final_remarks = system_remark

                if user_remark:
                    final_remarks += f" - {user_remark}"

                sap_payload = {
                    "DocType": "rSupplier" if payment_type == "Vendor" else "rAccount",
                    "DocDate": payment_date,
                    "TaxDate": payment_date,
                    "DueDate": payment_date,
                    "Remarks": final_remarks 
                }


                if payment_type == "Vendor":
                    sap_payload["CardCode"] = data.get("vendor_id")

                # -------------------------
                # INSERT PAYMENT MEANS (OUTGOING)
                # -------------------------
                if payments:

                    pay_line_id = str(await generate_id(
                        conn, tenant_schema,
                        "ik_out_payment_paymeans_seq", "OUTPM"
                    ))

                    cash_account = None
                    cash_amount = None
                    bank_account = None
                    bank_amount = None
                    transfer_date = None
                    cheque_account = None
                    cheque_no = None
                    cheque_amount = None
                    cheque_duedate = None
                    bank_name = None

                    def to_str(val):
                        return str(val) if val is not None else None

                    def to_date(val):
                        if isinstance(val, date):
                            return val
                        if isinstance(val, str):
                            return datetime.strptime(val, "%Y-%m-%d").date()
                        return None

                    if payments.get("cash"):
                        cash_account = to_str(payments["cash"].get("account_id"))
                        cash_amount = float(payments["cash"].get("amount", 0))

                    if payments.get("transfer"):
                        bank_account = to_str(payments["transfer"].get("account_id"))
                        bank_amount = float(payments["transfer"].get("amount", 0))
                        transfer_date = to_date(payment_date)
                    if payments.get("checks"):
                        chk = payments["checks"][0]
                        cheque_no = to_str(chk.get("CheckNumber"))
                        cheque_amount = float(chk.get("CheckSum", 0))
                        cheque_duedate = to_date(payment_date)  
                        bank_name = to_str(
                            chk.get("BankName") or 
                            chk.get("bank_name") or
                            chk.get("banks") or 
                            chk.get("bank") or
                            chk.get("bank_code") or
                            chk.get("bankName") or
                            chk.get("BankCode") or 
                            "bank_name"
                        )      
                        cheque_account = to_str(chk.get("CheckAccount"))

                    await conn.execute(f'''
                        INSERT INTO "{tenant_schema}".ik_out_payment_paymeans_line
                        (
                            payment_line_id, payment_id,
                            cheque_account, cheque_no, cheque_duedate, bank_name, cheque_amount,
                            cash_account, cash_amount,
                            bank_account, transfer_date, bank_amount,
                            schema_id
                        )
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                    ''',
                        pay_line_id,
                        payment_id,
                        cheque_account,
                        cheque_no,
                        cheque_duedate,
                        bank_name,
                        cheque_amount,
                        cash_account,
                        cash_amount,
                        bank_account,
                        transfer_date,
                        bank_amount,
                        tenant_schema
                    )
                # -------------------------
                # PAYMENT MEANS
                # -------------------------
                # CASH
                if payments.get("cash"):
                    sap_payload["CashAccount"] = payments["cash"]["account_id"]
                    sap_payload["CashSum"] = float(payments["cash"]["amount"])


                # TRANSFER
                if payments.get("transfer"):
                    sap_payload["TransferAccount"] = payments["transfer"]["account_id"]
                    sap_payload["TransferSum"] = float(payments["transfer"]["amount"])
                    sap_payload["TransferDate"] = payment_date


                # CHECK (SAFE VERSION)
                if payments.get("checks"):
                    check = payments["checks"][0]

                    # fetch GL accounts
                    gl_rows = await conn.fetch(f'''
                        SELECT account_id AS account_code, account_name
                        FROM "{tenant_schema}".ik_glaccount
                        WHERE is_active = TRUE
                    ''')
                    gl_accounts = [dict(r) for r in gl_rows]

                    # get mapped GL account
                    bank_code = (
                        check.get("BankCode") or
                        check.get("bank_code") or
                        check.get("bankCode")
                    )

                    bank_name = (
                        check.get("BankName") or
                        check.get("bank_name") or
                        check.get("bankName")
                    )

                    check_account = SapPaymentService.get_check_account(
                        bank_code,
                        bank_name,
                        gl_accounts
                    )

                    if not check_account:
                        raise HTTPException(400, f"No GL account mapped for bank: {check.get('BankName')}")

                    sap_payload["CheckAccount"] = check_account

                    sap_payload["PaymentChecks"] = [{
                        "DueDate": payment_date,
                        "CheckNumber": check["CheckNumber"],
                        "BankCode": check.get("BankCode"),
                        "CheckSum": float(check["CheckSum"]),
                        "CountryCode": check.get("CountryCode", "IN"),
                        "CheckAccount": check_account
                    }]
                # CARD (SAFE VERSION)
                if payments.get("card"):
                    card = payments["card"][0]

                    payment_card = {
                        "CreditCard": card["CreditCard"],
                        "CreditAcct": card["CreditAcct"],
                        "CreditSum": float(card["CreditSum"])
                    }

                    # ADD ONLY IF EXISTS (NO None)
                    if card.get("CreditCardNumber"):
                        payment_card["CreditCardNumber"] = card["CreditCardNumber"]

                    if card.get("CardValidUntil"):
                        payment_card["CardValidUntil"] = card["CardValidUntil"]

                    if card.get("VoucherNum"):
                        payment_card["VoucherNum"] = card["VoucherNum"]

                    if card.get("PaymentMethodCode") is not None:
                        payment_card["PaymentMethodCode"] = card["PaymentMethodCode"]

                    sap_payload["PaymentCreditCards"] = [payment_card]
                
                if payment_type == "Account":
                    sap_payload["PaymentAccounts"] = [
                        {
                            "AccountCode": acc["account_id"],
                            "SumPaid": float(acc["total_amount"]),
                            "Decription": acc.get("remarks", ""),
                            "AccountName": acc.get("account_name"),
                            "GrossAmount": float(acc["total_amount"])
                        }
                        for acc in accounts
                    ]
                
                # -------------------------
                # SAP INVOICES (ONLY IF EXISTS)
                # -------------------------
                if payment_type == "Vendor" and invoices:
                    sap_payload["PaymentInvoices"] = [
                        {
                            "DocEntry": int(inv["doc_entry"]),
                            "SumApplied": float(inv["total_amount"]),
                            "InvoiceType": "it_PurchaseInvoice"
                        }
                        for inv in invoices
                    ]

                # -------------------------
                # CALL SAP
                # -------------------------
                config = await get_sap_config(conn)

                #print("SAP REQUEST:", sap_payload)

                try:
                    sap_res = await SAPApiClient.post_outgoing_payment(config, sap_payload)

                    await conn.execute(f'''
                        UPDATE "{tenant_schema}".ik_out_payment_header
                        SET status='Open',
                            sap_docentry=$1,
                            updated_at=NOW()
                        WHERE payment_id=$2
                    ''',
                        str(sap_res.get("DocEntry")),
                        payment_id
                    )

                    return {
                        "status": "success",
                        "payment_id": payment_id,
                        "sap_docentry": sap_res.get("DocEntry"),
                        "sap_payload": sap_payload,
                        "sap_response": sap_res
                    }

                except Exception as e:

                    await conn.execute(f'''
                        UPDATE "{tenant_schema}".ik_out_payment_header
                        SET status='Failed',
                            updated_at=NOW()
                        WHERE payment_id=$1
                    ''', payment_id)

                    # ✅ LOG ERROR
                    await log_error(
                        conn,
                        tenant_schema,
                        module="OUTGOING_PAYMENT",
                        operation="SAP_POST",
                        ref_id=payment_id,
                        error_msg=str(e),
                        payload=sap_payload
                    )

                    return {
                        "status": "error",
                        "payment_id": payment_id,
                        "sap_payload": sap_payload,
                        "sap_response": str(e)
                    }

    @staticmethod
    async def get_recent_incoming_payments(request, db_pool, current_user):
        tenant_schema = getattr(request.state, "schema")

        user_id = current_user.get("user_id") or current_user.get("userId")
        email = current_user.get("email") or current_user.get("sub")

        async with db_pool.acquire() as conn:

            if user_id:
                result = await conn.fetch(f'''
                    SELECT 
                        h.payment_id,
                        h.payment_date,
                        h.customer_id,
                        h.customer_name,
                        h.document_total,
                        h.sap_docentry,
                        h.status,

                        (
                            SELECT l.doc_num
                            FROM "{tenant_schema}".ik_inc_payment_inv_line l
                            WHERE l.payment_id = h.payment_id
                            LIMIT 1
                        ) AS doc_num

                    FROM "{tenant_schema}".ik_inc_payment_header h
                    WHERE TRIM(h.created_by) = $1
                    ORDER BY h.created_at DESC
                    LIMIT 5
                ''', str(user_id).strip())

            elif email:
                result = await conn.fetch(f'''
                    SELECT 
                        h.payment_id,
                        h.payment_date,
                        h.customer_id,
                        h.customer_name,
                        h.document_total,
                        h.sap_docentry,
                        h.status,

                        (
                            SELECT l.doc_num
                            FROM "{tenant_schema}".ik_inc_payment_inv_line l
                            WHERE l.payment_id = h.payment_id
                            LIMIT 1
                        ) AS doc_num

                    FROM "{tenant_schema}".ik_inc_payment_header h
                    WHERE LOWER(h.created_by) = LOWER($1)
                    ORDER BY h.created_at DESC
                    LIMIT 5
                ''', email)

            else:
                result = []

            data = [dict(row) for row in result]

            return {
                "status": "success",
                "message": "Recent incoming payments fetched successfully",
                "count": len(data),
                "data": data
            }

        

    @staticmethod
    async def get_recent_outgoing_payments(request, db_pool, current_user):

        tenant_schema = getattr(request.state, "schema")

        user_id = current_user.get("user_id") or current_user.get("userId")
        email = current_user.get("email") or current_user.get("sub")

        async with db_pool.acquire() as conn:

            if user_id:
                result = await conn.fetch(f'''
                    SELECT 
                        h.payment_id,
                        h.payment_date,
                        h.vendor_id,
                        h.vendor_name,
                        h.document_total,
                        h.sap_docentry,
                        h.status,

                        (
                            SELECT l.doc_num
                            FROM "{tenant_schema}".ik_out_payment_inv_line l
                            WHERE l.payment_id = h.payment_id
                            LIMIT 1
                        ) AS doc_num

                    FROM "{tenant_schema}".ik_out_payment_header h
                    WHERE TRIM(h.created_by) = $1
                    ORDER BY h.created_at DESC
                    LIMIT 5
                ''', str(user_id).strip())

            elif email:
                result = await conn.fetch(f'''
                    SELECT 
                        h.payment_id,
                        h.payment_date,
                        h.vendor_id,
                        h.vendor_name,
                        h.document_total,
                        h.sap_docentry,
                        h.status,

                        (
                            SELECT l.doc_num
                            FROM "{tenant_schema}".ik_out_payment_inv_line l
                            WHERE l.payment_id = h.payment_id
                            LIMIT 1
                        ) AS doc_num

                    FROM "{tenant_schema}".ik_out_payment_header h
                    WHERE LOWER(h.created_by) = LOWER($1)
                    ORDER BY h.created_at DESC
                    LIMIT 5
                ''', email)

            else:
                result = []

            data = [dict(row) for row in result]

            return {
                "status": "success",
                "message": "Recent outgoing payments fetched successfully",
                "count": len(data),
                "data": data
            }