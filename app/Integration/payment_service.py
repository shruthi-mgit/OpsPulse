from app.Integration.sap_api_client import SAPApiClient
from app.config.config_service import get_sap_config_by_schema
from app.Integration.sap_session_cache import get_session, set_session
from fastapi import HTTPException
import logging
from datetime import datetime
from datetime import date
from app.scheduler.log_service import LogService
from fastapi.responses import JSONResponse

logger = logging.getLogger("sap-payment-service")

import json
import re

def extract_sap_error(error_msg: str):

    try:

        sap_error = json.loads(error_msg)

        msg = (
            sap_error.get("error", {})
            .get("message", error_msg)
        )

        msg = re.sub(
            r"\s*\[.*?\]\[line:\s*\d+\]",
            "",
            msg
        )

        msg = msg.replace("'", "")
        msg = msg.replace(" , ", " ")

        return msg.strip()

    except Exception:

        return error_msg

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

    return f"{prefix}{seq}"

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

    return f"ERROR_{num}"

class SapPaymentService:

    # =========================
    # CUSTOMER DETAILS
    # =========================
    @staticmethod
    async def get_customers(
        conn,
        tenant_schema: str,
        search: str = "",
        page: int = 1,
        per_page: int = 200
    ):
        try:

            offset = (page - 1) * per_page

            # =========================
            # SEARCH MODE
            # =========================
            if search and search.strip():

                search_value = f"%{search.strip()}%"

                count_query = f"""
                    SELECT COUNT(*)
                    FROM "{tenant_schema}".ik_bp
                    WHERE bp_type = 'C'
                    AND (
                        LOWER(bp_name) LIKE LOWER($1)
                        OR LOWER(bp_id) LIKE LOWER($1)
                    )
                """

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
                    AND (
                        LOWER(bp_name) LIKE LOWER($1)
                        OR LOWER(bp_id) LIKE LOWER($1)
                    )
                    ORDER BY bp_name
                    LIMIT $2 OFFSET $3
                """

                total_records = await conn.fetchval(
                    count_query,
                    search_value
                )

                rows = await conn.fetch(
                    query,
                    search_value,
                    per_page,
                    offset
                )

            # =========================
            # NORMAL MODE
            # =========================
            else:

                count_query = f"""
                    SELECT COUNT(*)
                    FROM "{tenant_schema}".ik_bp
                    WHERE bp_type = 'C'
                """

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
                    ORDER BY bp_name
                    LIMIT $1 OFFSET $2
                """

                total_records = await conn.fetchval(
                    count_query
                )

                rows = await conn.fetch(
                    query,
                    per_page,
                    offset
                )

            total_pages = (
                (total_records + per_page - 1) // per_page
                if total_records > 0 else 1
            )

            data = [
                {
                    "customer_code": r["customer_code"],
                    "customer_name": r["customer_name"],
                    "city": r["city"],
                    "country": r["country"],
                    "email": r["email"],
                    "balance": float(r["balance"] or 0)
                }
                for r in rows
            ]

            return {
                "status": "success",
                "meta": {
                    "page": page,
                    "per_page": per_page,
                    "total_records": total_records,
                    "total_pages": total_pages
                },
                "data": data
            }

        except Exception as e:

            logger.exception("Error fetching customers")

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": str(e)
                }
            )

    # =========================
    # CUSTOMER INVOICES
    # =========================
    @staticmethod
    async def get_invoices(
        customer_code: str,
        bpl_id: int,
        request,
        db_pool
    ):
        try:
            async with db_pool.acquire() as conn:

                from app.config.config_service import get_sap_config_by_schema

                tenant_schema = getattr(request.state, "schema")

                config = await get_sap_config_by_schema(
                    conn,
                    tenant_schema
                )

                data = await SAPApiClient.get_customer_due_invoices(
                    customer_code=customer_code,
                    bpl_id=bpl_id,
                    config=config
                )

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
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Failed to fetch invoice data: {str(e)}"
                }
            )

    # =========================
    # GL ACCOUNTS
    # =========================
    @staticmethod
    async def get_gl_accounts(
        conn,
        tenant_schema: str,
        search: str = ""
    ):
        try:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            rows = await SAPApiClient.get_gl_all(
                config
            )

            data = []

            for row in rows:

                account_name = row.get("Name", "")

                if (
                    search
                    and search.lower() not in account_name.lower()
                ):
                    continue

                data.append({
                    "account_code": row.get("Code"),
                    "account_name": row.get("Name"),
                    "is_active": row.get("ActiveAccount") == "tYES",
                    "balance": float(
                        row.get("Balance") or 0
                    ),
                    "is_control_account":
                        row.get("LockManualTransaction") == "tYES"
                })

            return success_response(data)

        except Exception as e:

            logger.exception(
                "Error fetching GL accounts"
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": str(e)
                }
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
                status_code=400,
                detail={"status": "error", "message": "Failed to fetch banks"}
            )

    # =========================
    # SUPPLIERS
    # =========================
    @staticmethod
    async def get_suppliers(
        conn,
        tenant_schema: str,
        search: str = "",
        page: int = 1,
        per_page: int = 200
    ):
        try:

            offset = (page - 1) * per_page

            values = []
            count_values = []

            # =========================
            # SEARCH MODE
            # =========================
            if search:

                count_query = f"""
                    SELECT COUNT(*)
                    FROM "{tenant_schema}".ik_bp
                    WHERE bp_type = 'S'
                    AND (
                        LOWER(bp_name) LIKE LOWER($1)
                        OR LOWER(bp_id) LIKE LOWER($1)
                    )             
                """

                query = f"""
                    SELECT
                        bp_id AS supplier_code,
                        bp_name AS supplier_name,
                        city,
                        country,
                        email,
                        balance,
                        debitor_account
                    FROM "{tenant_schema}".ik_bp
                    WHERE bp_type = 'S'
                    AND (
                        LOWER(bp_name) LIKE LOWER($1)
                        OR LOWER(bp_id) LIKE LOWER($1)
                    )
                    ORDER BY bp_name
                    LIMIT $2 OFFSET $3
                """

                search_value = f"%{search}%"

                count_values.append(search_value)

                values.extend([
                    search_value,
                    per_page,
                    offset
                ])

            # =========================
            # NORMAL PAGINATION
            # =========================
            else:

                count_query = f"""
                    SELECT COUNT(*)
                    FROM "{tenant_schema}".ik_bp
                    WHERE bp_type = 'S'
                """

                query = f"""
                    SELECT
                        bp_id AS supplier_code,
                        bp_name AS supplier_name,
                        city,
                        country,
                        email,
                        balance,
                        debitor_account
                    FROM "{tenant_schema}".ik_bp
                    WHERE bp_type = 'S'
                    ORDER BY bp_name
                    LIMIT $1 OFFSET $2
                """

                values.extend([
                    per_page,
                    offset
                ])

            # =========================
            # TOTAL COUNT
            # =========================
            total_records = await conn.fetchval(
                count_query,
                *count_values
            )

            # =========================
            # FETCH DATA
            # =========================
            rows = await conn.fetch(
                query,
                *values
            )
            print("PAGE =", page)
            print("OFFSET =", offset)
            print("ROWS =", len(rows))
            total_pages = (
                (total_records + per_page - 1) // per_page
            )

            data = [
                {
                    "supplier_code": r["supplier_code"],
                    "supplier_name": r["supplier_name"],
                    "city": r.get("city"),
                    "country": r.get("country"),
                    "email": r.get("email"),
                    "balance": r["balance"],
                    "debitor_account": r.get("debitor_account")
                }
                for r in rows
            ]
            return {
                "status": "success",
                "meta": {
                    "page": page,
                    "per_page": per_page,
                    "total_records": total_records,
                    "total_pages": total_pages
                },
                "data": data
            }

        except Exception:

            logger.exception("Error fetching suppliers")

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": "Failed to fetch suppliers"
                }
            )
    # =========================
    # SUPPLIER INVOICES
    # =========================
    @staticmethod
    async def get_supplier_invoices(
        vendor_code: str,
        bpl_id: int,
        request,
        db_pool
    ):
        try:
            from app.config.config_service import get_sap_config_by_schema

            async with db_pool.acquire() as conn:
                tenant_schema = getattr(request.state, "schema")

                config = await get_sap_config_by_schema(
                    conn,
                    tenant_schema
                )

            data = await SAPApiClient.get_vendor_due_invoices(
                vendor_code=vendor_code,
                bpl_id=bpl_id,
                config=config
            )

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
                status_code=400,
                detail={
                    "status": "error",
                    "message": "Failed to fetch vendor data"
                }
            )
    # =========================
    # BRANCHES
    # =========================
    @staticmethod
    async def get_branches(
        conn,
        tenant_schema: str,
        search: str = ""
    ):
        try:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            branches = await SAPApiClient.get_all_data(
                "SQLQueries('DADA_FtechBranches')/List",
                config
            )

            data = []

            for row in branches:

                branch_name = row.get("BPLName", "")

                if search and search.lower() not in branch_name.lower():
                    continue

                data.append({
                    "branch_id": row.get("BPLId"),
                    "branch_name": branch_name
                })

            return success_response(data)

        except Exception:
            logger.exception("Error fetching branches")

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": "Failed to fetch branches"
                }
            )
    # @staticmethod
    # def get_check_account(bank_code, bank_name, gl_accounts):

    #     # ✅ PRIORITY 1: Use BankCode (BEST MATCH)
    #     if bank_code:
    #         bank_code = bank_code.lower()

    #         for acc in gl_accounts:
    #             acc_name = acc["account_name"].lower()

    #             # Example: SBIN → match "state bank of india"
    #             if bank_code in acc_name:
    #                 return acc["account_code"]

    #             # Example: DEUT0019 → match last 4 digits (0019)
    #             if len(bank_code) >= 4:
    #                 suffix = bank_code[-4:]
    #                 if suffix in acc_name:
    #                     return acc["account_code"]

        # ✅ PRIORITY 2: fallback to BankName
        # if bank_name:
        #     bank_name_lower = bank_name.lower()

        #     for acc in gl_accounts:
        #         if bank_name_lower in acc["account_name"].lower():
        #             return acc["account_code"]

        # return None



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
                mode_of_payment = (
                    data.get("U_MDP")
                    or data.get("mode_of_payment")
                )

                payment_date_str = data.get("payment_date")
                if not payment_date_str:
                    raise HTTPException(400, "payment_date is required")

                payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()

                branch_id = data.get("branch_id")
                branch_name = data.get("branch_name")

                if not branch_id:
                    raise HTTPException(
                        status_code=400,
                        detail="branch_id is required"
                    )

                control_account_id = data.get("control_account_id")

                is_on_account = data.get(
                    "is_payment_onaccount",
                    False
                )

                user_remark = (data.get("remarks") or "").strip()

                system_remark = ""

                final_remarks = system_remark

                if user_remark:
                    final_remarks += f" - {user_remark}"
                # -------------------------
                # VALIDATION
                # -------------------------
                if payment_type_ui == "Customer":

                    if not data.get("customer_id"):
                        raise HTTPException(400, "Customer required")

                    if not is_on_account and not invoices:
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
                inv_total = sum(
                    float(
                        i.get("sum_applied")
                        or i.get("total_amount", 0)
                    )
                    for i in invoices
                )
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
                

                if payment_type_ui == "Customer":

                    if is_on_account:
                        expected_total = payment_total
                    else:
                        expected_total = inv_total

                else:
                    expected_total = acc_total


                payment_on_account = None

                if is_on_account:

                    if not control_account_id:
                        raise HTTPException(
                            400,
                            "control_account_id is required"
                        )

                    payment_on_account = payment_total
        
                if round(payment_total, 2) != round(expected_total, 2):
                    print("inv_total =", inv_total)
                    print("acc_total =", acc_total)
                    print("payment_total =", payment_total)
                    print("expected_total =", expected_total)
                    print("payments =", payments)
                    print("invoices =", invoices)
                    raise HTTPException(400, "Payment total mismatch")

                # -------------------------
                # GENERATE PAYMENT ID
                # -------------------------
                payment_id = str(await generate_id(
                    conn, tenant_schema, "ik_inc_payment_seq", "INCPH"
                ))

                # -------------------------
                # INSERT HEADER
                # -------------------------
                await conn.execute(f'''
                    INSERT INTO "{tenant_schema}".ik_inc_payment_header
                    (
                        payment_id,
                        payment_date,
                        customer_id,
                        customer_name,
                        payment_type,
                        remarks,
                        status,
                        created_by,
                        updated_by,
                        schema_id,
                        document_total,
                        is_pay_onaccount,
                        pay_onaccount_amount,
                        branch,
                        branch_id,
                        control_account_id,
                        mode_of_payment
                    )
                    VALUES
                    (
                        $1,$2,$3,$4,$5,$6,
                        'Open',
                        $7,$7,$8,$9,$10,$11,$12,$13,$14,$15
                    )
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
                    payment_on_account,
                    branch_name,
                    str(branch_id),
                    control_account_id,
                    mode_of_payment
                    )

                # -------------------------
                # INSERT INVOICES
                # -------------------------
                if payment_type_ui == "Customer":
                    for inv in invoices:

                        line_id = str(await generate_id(
                            conn, tenant_schema, "ik_inc_payment_line_seq", "INPIL"
                        ))

                        await conn.execute(f'''
                            INSERT INTO "{tenant_schema}".ik_inc_payment_inv_line
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                        ''',
                            line_id,
                            payment_id,
                            inv.get("doc_type"),
                            str(inv.get("doc_entry")),
                            str(inv.get("doc_num")) if inv.get("doc_num") is not None else None,
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
                            conn, tenant_schema, "ik_inc_payment_acct_line_seq", "INPAL"
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
                        "BPLID": int(branch_id),
                        "BPLName": branch_name,
                        "Remarks": final_remarks
                    }

                    if not is_on_account:

                        sap_payload["PaymentInvoices"] = [
                            {
                                "DocEntry": int(inv["doc_entry"]),
                                "SumApplied": float(
                                    inv.get("sum_applied")
                                    or inv.get("total_amount", 0)
                                )
                            }
                            for inv in invoices
                        ]
                else:
                    sap_payload = {
                        "DocType": "rAccount",
                        "DocDate": payment_date_str,
                        "TaxDate": payment_date_str,
                        "DueDate": payment_date_str,
                        "BPLID": int(branch_id),
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

                    def to_str(val):
                        return str(val) if val is not None else None

                    cash_account = None
                    cash_amount = None
                    bank_account = None
                    bank_amount = None
                    transfer_date = None

                    if payments.get("cash"):
                        cash_account = to_str(payments["cash"].get("account_id"))
                        cash_amount = float(payments["cash"].get("amount", 0))

                    if payments.get("transfer"):
                        bank_account = to_str(payments["transfer"].get("account_id"))
                        bank_amount = float(payments["transfer"].get("amount", 0))
                        transfer_date = payment_date if isinstance(payment_date, date) else None

                    if payments.get("checks"):
                        # ✅ One INSERT row per check, each with its own unique pay_line_id
                        for chk in payments["checks"]:
                            pay_line_id = str(await generate_id(   # ← INSIDE loop
                                conn, tenant_schema,
                                "ik_inc_payment_paymeans_seq", "INPPM"
                            ))
                            cheque_no = to_str(chk.get("CheckNumber"))
                            cheque_amount = float(chk.get("CheckSum", 0))
                            cheque_duedate = payment_date if isinstance(payment_date, date) else None
                            bank_name = to_str(
                                chk.get("BankName") or chk.get("bank_name") or
                                chk.get("banks") or chk.get("bank") or
                                chk.get("bank_code") or chk.get("bankName") or
                                chk.get("BankCode") or "bankname"
                            )
                            cheque_account = to_str(chk.get("CheckAccount"))

                            await conn.execute(f'''
                                INSERT INTO "{tenant_schema}".ik_inc_payment_paymeans_line
                                (payment_line_id, payment_id, cheque_account, cheque_no,
                                cheque_duedate, bank_name, cheque_amount, cash_account,
                                cash_amount, bank_account, transfer_date, bank_amount, schema_id)
                                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                            ''',
                                pay_line_id, payment_id,
                                cheque_account, cheque_no, cheque_duedate, bank_name, cheque_amount,
                                cash_account, cash_amount,       # shared across all check rows
                                bank_account, transfer_date, bank_amount,
                                tenant_schema
                            )

                    elif payments.get("cash") or payments.get("transfer"):
                        # ✅ No checks — insert single row for cash/transfer only
                        pay_line_id = str(await generate_id(
                            conn, tenant_schema,
                            "ik_inc_payment_paymeans_seq", "INPPM"
                        ))
                        await conn.execute(f'''
                            INSERT INTO "{tenant_schema}".ik_inc_payment_paymeans_line
                            (payment_line_id, payment_id, cheque_account, cheque_no,
                            cheque_duedate, bank_name, cheque_amount, cash_account,
                            cash_amount, bank_account, transfer_date, bank_amount, schema_id)
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                        ''',
                            pay_line_id, payment_id,
                            None, None, None, None, None,
                            cash_account, cash_amount,
                            bank_account, transfer_date, bank_amount,
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
                    sap_payload["TransferReference"] = ""
                    # sap_payload["U_MDP"] = "BankTransfer"
                if payments.get("card"):
                    sap_payload["PaymentCreditCards"] = payments["card"]

                if payments.get("checks"):
                    payment_checks = []
                    check_account = None  # SAP requires one G/L account at header level

                    for check in payments["checks"]:    # ← loop over all checks
                        check_account = (
                            check.get("CheckAccount") or
                            check.get("account_id") or
                            check.get("gl_account") or
                            check.get("glAccount") or
                            check.get("accountCode")
                        )

                        if not check_account:
                            raise HTTPException(400, "G/L Account is required for cheque")

                        exists = await conn.fetchval(f'''
                            SELECT 1
                            FROM "{tenant_schema}".ik_glaccount
                            WHERE account_id = $1 AND is_active = TRUE
                        ''', str(check_account))

                        if not exists:
                            raise HTTPException(400, f"Invalid G/L Account: {check_account}")

                        payment_checks.append({
                            "DueDate": payment_date_str,
                            "CheckNumber": check.get("CheckNumber"),
                            "BankCode": check.get("BankCode"),
                            "CheckSum": float(check.get("CheckSum", 0)),
                            "CountryCode": check.get("CountryCode", "IN"),
                            "CheckAccount": str(check_account)
                        })

                    sap_payload["CheckAccount"] = str(check_account)  # header-level (last/common account)
                    sap_payload["PaymentChecks"] = payment_checks      # ← full array sent to SAP

                if mode_of_payment:
                    sap_payload["U_MDP"] = mode_of_payment
                # -------------------------
                # CALL SAP
                # -------------------------
                from app.config.config_service import get_sap_config_by_schema
                tenant_schema = getattr(request.state, "schema")

                config = await get_sap_config_by_schema(
                    conn,
                    tenant_schema
                )
                error_msg = None
                
                if is_on_account:
                    sap_payload["ControlAccount"] = control_account_id
                try:

                    import json

                    print("\n========== FINAL SAP PAYLOAD ==========")
                    print(json.dumps(sap_payload, indent=2))
                    print("======================================")
                    sap_res = await SAPApiClient.post_incoming_payment(config, sap_payload)

                    import json
                    print("SAP RESPONSE:", json.dumps(sap_res, indent=2))

                    log_service = LogService(conn)

                    await log_service.log_success(
                        schema=tenant_schema,
                        schema_id=tenant_schema,
                        type="IncomingPayment",
                        msg=f"Incoming Payment Posted : {payment_id}",
                        payload=sap_payload
                    )
                    


                    await conn.execute(f'''
                        UPDATE "{tenant_schema}".ik_inc_payment_header
                        SET status='Close',
                            sap_status='Posted',
                            sap_docentry=$1,
                            sap_docnum=$2,
                            series_id=$3,
                            journal_remarks=$4,
                            updated_at=NOW()
                        WHERE payment_id=$5
                    ''',
                        str(sap_res.get("DocEntry")),
                        str(sap_res.get("DocNum")),
                        sap_res.get("Series"),
                        sap_res.get("JournalRemarks"),
                        payment_id
                    )
                    return {
                        "status": "success",
                        "payment_id": payment_id,
                        "sap_docentry": sap_res.get("DocEntry"),
                        "sap_docnum": sap_res.get("DocNum"),
                        "sap_payload": sap_payload,
                        "sap_response": sap_res
                    }
                except Exception as e:

                    error_msg = str(e)

                    # ✅ Update status (inside transaction)
                    await conn.execute(f'''
                        UPDATE "{tenant_schema}".ik_inc_payment_header
                        SET sap_status='Failed',
                            updated_at=NOW()
                        WHERE payment_id=$1
                    ''', payment_id)

                    # ✅ LOG ERROR using separate connection (IMPORTANT)
                
                    try:

                        async with db_pool.acquire() as log_conn:

                            log_service = LogService(log_conn)

                            await log_service.log_error(
                                schema=tenant_schema,
                                schema_id=tenant_schema,
                                type="IncomingPayment",
                                msg=error_msg,
                                payload=sap_payload
                            )

                    except Exception as log_ex:

                        print("LOGGING FAILED:", str(log_ex))
                    
                    clean_message = extract_sap_error(error_msg)

                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "error",
                            "payment_id": payment_id,
                            "sap_payload": sap_payload,
                            "message": clean_message
                        }
                    )

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

                is_on_account = data.get(
                    "is_payment_onaccount",
                    False
                )

                control_account_id = data.get(
                    "control_account_id"
                )

                # -------------------------
                # VALIDATION
                # -------------------------
                if payment_type not in ["Vendor", "Account"]:
                    raise HTTPException(400, "Invalid payment type")

                if payment_type == "Vendor":

                    if not data.get("vendor_id"):
                        raise HTTPException(400, "Vendor required")

                    if not is_on_account and not invoices:
                        raise HTTPException(
                            400,
                            "Invoices required"
                        )

                if payment_type == "Account":

                    if not accounts:
                        raise HTTPException(
                            400,
                            "Accounts required for account payment"
                        )

                branch_id = data.get("branch_id")
                branch_name = data.get("branch_name")

                if not branch_id:
                    raise HTTPException(
                        status_code=400,
                        detail="branch_id is required"
                    )

                # -------------------------
                # CALCULATE TOTALS
                # -------------------------
                inv_total = sum(
                    float(
                        i.get("sum_applied")
                        or i.get("total_amount", 0)
                    )
                    for i in invoices
                )
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
                payment_onaccount = None

                if payment_type == "Vendor":

                    if is_on_account:


                        if invoices:
                            raise HTTPException(
                                400,
                                "Invoices not allowed for Payment On Account"
                            )
                        total_amount = payment_total

                        payment_onaccount = payment_total

                    else:

                        total_amount = inv_total

                else:

                    total_amount = acc_total

                    is_on_account = True

                    payment_onaccount = acc_total

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
                    "OUTPH"
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
                        payment_onaccount,
                        branch,
                        branch_id,
                        control_account_id
            
                    )
                    VALUES ($1, CURRENT_DATE, $2, $3, $4, $5,
                            'Open', $6, $6, $7, $8,
                            $9, $10, $11, $12, $13)
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
                    payment_onaccount,
                    branch_name,
                    str(branch_id),
                    control_account_id

                )

                # -------------------------
                # INSERT INVOICE LINES
                # -------------------------
                if (
                    payment_type == "Vendor"
                    and not is_on_account
                    and invoices
                ):
                    for inv in invoices:

                        line_id = str(await generate_id(
                            conn,
                            tenant_schema,
                            "ik_out_payment_line_seq",
                            "OTPIL"
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
                            "ik_out_payment_acct_line_seq", "OTPAL"
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

                system_remark = ""

                final_remarks = system_remark

                if user_remark:
                    final_remarks += f" - {user_remark}"

                sap_payload = {
                    "DocType": "rSupplier" if payment_type == "Vendor" else "rAccount",
                    "DocDate": payment_date,
                    "TaxDate": payment_date,
                    "DueDate": payment_date,
                    "BPLID": int(branch_id),
                    "BPLName": branch_name,
                    "Remarks": final_remarks 
                }


                if payment_type == "Vendor":
                    sap_payload["CardCode"] = data.get("vendor_id")

                # -------------------------
                # INSERT PAYMENT MEANS (OUTGOING)
                # -------------------------
                if payments:

                    def to_str(val):
                        return str(val) if val is not None else None

                    def to_date(val):
                        if isinstance(val, date):
                            return val
                        if isinstance(val, str):
                            return datetime.strptime(val, "%Y-%m-%d").date()
                        return None

                    cash_account = None
                    cash_amount = None
                    bank_account = None
                    bank_amount = None
                    transfer_date = None

                    if payments.get("cash"):
                        cash_account = to_str(payments["cash"].get("account_id"))
                        cash_amount = float(payments["cash"].get("amount", 0))

                    if payments.get("transfer"):
                        bank_account = to_str(payments["transfer"].get("account_id"))
                        bank_amount = float(payments["transfer"].get("amount", 0))
                        transfer_date = to_date(payment_date)

                    if payments.get("checks"):
                        # ✅ One row per check
                        for chk in payments["checks"]:
                            pay_line_id = str(await generate_id(   # ← INSIDE loop
                                conn, tenant_schema,
                                "ik_out_payment_paymeans_seq", "OTPPM"
                            ))
                            cheque_no = to_str(chk.get("CheckNumber"))
                            cheque_amount = float(chk.get("CheckSum", 0))
                            cheque_duedate = to_date(payment_date)
                            bank_name = to_str(
                                chk.get("BankName") or chk.get("bank_name") or
                                chk.get("banks") or chk.get("bank") or
                                chk.get("bank_code") or chk.get("bankName") or
                                chk.get("BankCode") or "bank_name"
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
                                pay_line_id, payment_id,
                                cheque_account, cheque_no, cheque_duedate, bank_name, cheque_amount,
                                cash_account, cash_amount,
                                bank_account, transfer_date, bank_amount,
                                tenant_schema
                            )

                    elif payments.get("cash") or payments.get("transfer"):
                        # ✅ No checks — single row for cash/transfer only
                        pay_line_id = str(await generate_id(
                            conn, tenant_schema,
                            "ik_out_payment_paymeans_seq", "OTPPM"
                        ))
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
                            pay_line_id, payment_id,
                            None, None, None, None, None,
                            cash_account, cash_amount,
                            bank_account, transfer_date, bank_amount,
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
                    payment_checks = []
                    check_account = None

                    for check in payments["checks"]:    # ← loop over all checks
                        check_account = (
                            check.get("CheckAccount") or
                            check.get("account_id") or
                            check.get("gl_account") or
                            check.get("glAccount") or
                            check.get("accountCode")
                        )

                        if not check_account:
                            raise HTTPException(400, "G/L Account is required for cheque")

                        exists = await conn.fetchval(f'''
                            SELECT 1
                            FROM "{tenant_schema}".ik_glaccount
                            WHERE account_id = $1 AND is_active = TRUE
                        ''', str(check_account))

                        if not exists:
                            raise HTTPException(400, f"Invalid G/L Account: {check_account}")

                        payment_checks.append({
                            "DueDate": payment_date,
                            "CheckNumber": check.get("CheckNumber"),
                            "BankCode": check.get("BankCode"),
                            "CheckSum": float(check.get("CheckSum", 0)),
                            "CountryCode": check.get("CountryCode", "IN"),
                            "CheckAccount": str(check_account)
                        })

                    sap_payload["CheckAccount"] = str(check_account)
                    sap_payload["PaymentChecks"] = payment_checks
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
                            "SumPaid": float(acc["total_amount"])
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
                            "SumApplied": float(
                                inv.get("sum_applied")
                                or inv.get("total_amount", 0)
                            ),
                            "InvoiceType": (
                                inv.get("InvoiceType")
                                or inv.get("doc_type")
                                or inv.get("invoice_type")
                                or ""
                            )
                        }
                        for inv in invoices
                    ]

                # -------------------------
                # CALL SAP
                # -------------------------
                tenant_schema = getattr(request.state, "schema")

                if payment_type == "Vendor" and is_on_account:

                    sap_payload["ControlAccount"] = control_account_id

                config = await get_sap_config_by_schema(
                    conn,
                    tenant_schema
                )
                #print("SAP REQUEST:", sap_payload)
                error_msg = None

                try:
                    sap_res = await SAPApiClient.post_outgoing_payment(config, sap_payload)

                    log_service = LogService(conn)

                    await log_service.log_success(
                        schema=tenant_schema,
                        schema_id=tenant_schema,
                        type="OutgoingPayment",
                        msg=f"Outgoing Payment Posted : {payment_id}",
                        payload=sap_res
                    )


                    await conn.execute(f'''
                        UPDATE "{tenant_schema}".ik_out_payment_header
                        SET status='Close',
                            sap_status='Posted',
                            sap_docentry=$1,
                            sap_docnum=$2,
                            series_id=$3,
                            journal_remarks=$4,
                            updated_at=NOW()
                        WHERE payment_id=$5
                    ''',
                        str(sap_res.get("DocEntry")),
                        str(sap_res.get("DocNum")),
                        sap_res.get("Series"),
                        sap_res.get("JournalRemarks"),
                        payment_id
                    )

                    return {
                        "status": "success",
                        "payment_id": payment_id,
                        "sap_docentry": sap_res.get("DocEntry"),
                        "sap_docnum" : sap_res.get("DocNum"),
                        "sap_payload": sap_payload,
                        "sap_response": sap_res
                    }

                except Exception as e:


                    error_msg = str(e)

                    # ✅ Update status (inside transaction)
                    await conn.execute(f'''
                        UPDATE "{tenant_schema}".ik_out_payment_header
                        SET status='Failed', sap_status='Failed', updated_at=NOW()
                        WHERE payment_id=$1
                    ''', payment_id)

                    # ✅ LOG ERROR using separate connection (IMPORTANT)
                    try:

                        async with db_pool.acquire() as log_conn:

                            log_service = LogService(log_conn)

                            await log_service.log_error(
                                schema=tenant_schema,
                                schema_id=tenant_schema,
                                type="OutgoingPayment",
                                msg=error_msg,
                                payload=sap_payload
                            )

                    except Exception as log_ex:

                        print("LOGGING FAILED:", str(log_ex))

                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "error",
                            "payment_id": payment_id,
                            "sap_payload": sap_payload,
                            "message": extract_sap_error(error_msg)
                        }
                    )
                    

    @staticmethod
    async def get_recent_incoming_payments(
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

        tenant_schema = getattr(request.state, "schema")

        user_id = current_user.get("user_id") or current_user.get("userId")
        email = current_user.get("email") or current_user.get("sub")

        async with db_pool.acquire() as conn:

            conditions = []
            values = []

            if user_id:

                conditions.append(
                    f"TRIM(h.created_by) = ${len(values)+1}"
                )

                values.append(
                    str(user_id).strip()
                )

            elif email:

                conditions.append(
                    f"LOWER(h.created_by) = LOWER(${len(values)+1})"
                )

                values.append(email)

            else:

                return {
                    "status": "success",
                    "count": 0,
                    "data": []
                }

            # -------------------------
            # STATUS FILTER
            # -------------------------
            if status:

                conditions.append(
                    f"h.status = ${len(values)+1}"
                )

                values.append(status)

            # -------------------------
            # DATE FILTER
            # -------------------------
            if from_date:

                conditions.append(
                    f"h.payment_date >= ${len(values)+1}"
                )

                values.append(from_date)

            if to_date:

                conditions.append(
                    f"h.payment_date <= ${len(values)+1}"
                )

                values.append(to_date)

            # -------------------------
            # SEARCH FILTER
            # -------------------------
            if search:

                search_param = f"%{search}%"

                conditions.append(f"""
                (
                    h.payment_id ILIKE ${len(values)+1}
                    OR h.customer_id ILIKE ${len(values)+1}
                    OR h.customer_name ILIKE ${len(values)+1}
                    OR h.sap_docnum ILIKE ${len(values)+1}
                    OR h.sap_docentry ILIKE ${len(values)+1}

                    OR EXISTS
                    (
                        SELECT 1
                        FROM "{tenant_schema}".ik_inc_payment_inv_line l
                        WHERE l.payment_id = h.payment_id
                        AND l.doc_num ILIKE ${len(values)+1}
                    )
                )
                """)

                values.append(search_param)

            where_clause = " AND ".join(conditions)

            # -------------------------
            # COUNT
            # -------------------------
            count_query = f"""
                SELECT COUNT(*)
                FROM "{tenant_schema}".ik_inc_payment_header h
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

            query = f"""
                SELECT
                    h.payment_id,
                    h.payment_date,
                    h.customer_id,
                    h.customer_name,
                    h.document_total,
                    h.sap_docentry,
                    h.sap_docnum,
                    h.sap_status,
                    h.status,

                    (
                        SELECT l.doc_num
                        FROM "{tenant_schema}".ik_inc_payment_inv_line l
                        WHERE l.payment_id = h.payment_id
                        LIMIT 1
                    ) AS doc_num

                FROM "{tenant_schema}".ik_inc_payment_header h

                WHERE {where_clause}

                ORDER BY h.created_at DESC

                LIMIT ${len(values)+1}
                OFFSET ${len(values)+2}
            """

            result = await conn.fetch(
                query,
                *values,
                per_page,
                offset
            )

            data = [
                dict(row)
                for row in result
            ]

            return {
                "status": "success",
                "message": "Incoming payments fetched successfully",
                "meta": {
                    "page": page,
                    "per_page": per_page,
                    "total_records": total_records,
                    "total_pages": total_pages
                },
                "count": len(data),
                "data": data
            }
            

    @staticmethod
    async def get_recent_outgoing_payments(
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

        tenant_schema = getattr(request.state, "schema")

        user_id = current_user.get("user_id") or current_user.get("userId")
        email = current_user.get("email") or current_user.get("sub")

        async with db_pool.acquire() as conn:

            conditions = []
            values = []

            if user_id:

                conditions.append(
                    f"TRIM(h.created_by) = ${len(values)+1}"
                )

                values.append(
                    str(user_id).strip()
                )

            elif email:

                conditions.append(
                    f"LOWER(h.created_by) = LOWER(${len(values)+1})"
                )

                values.append(email)

            else:

                return {
                    "status": "success",
                    "count": 0,
                    "data": []
                }

            # -------------------------
            # STATUS FILTER
            # -------------------------
            if status:

                conditions.append(
                    f"h.status = ${len(values)+1}"
                )

                values.append(status)

            # -------------------------
            # DATE FILTER
            # -------------------------
            if from_date:

                conditions.append(
                    f"h.payment_date >= ${len(values)+1}"
                )

                values.append(from_date)

            if to_date:

                conditions.append(
                    f"h.payment_date <= ${len(values)+1}"
                )

                values.append(to_date)

            # -------------------------
            # SEARCH FILTER
            # -------------------------
            if search:

                search_param = f"%{search}%"

                conditions.append(f"""
                (
                    h.payment_id ILIKE ${len(values)+1}
                    OR h.vendor_id ILIKE ${len(values)+1}
                    OR h.vendor_name ILIKE ${len(values)+1}
                    OR h.sap_docnum ILIKE ${len(values)+1}
                    OR h.sap_docentry ILIKE ${len(values)+1}

                    OR EXISTS
                    (
                        SELECT 1
                        FROM "{tenant_schema}".ik_out_payment_inv_line l
                        WHERE l.payment_id = h.payment_id
                        AND l.doc_num ILIKE ${len(values)+1}
                    )
                )
                """)

                values.append(search_param)

            where_clause = " AND ".join(conditions)

            # -------------------------
            # TOTAL COUNT
            # -------------------------
            count_query = f"""
                SELECT COUNT(*)
                FROM "{tenant_schema}".ik_out_payment_header h
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
                    h.payment_id,
                    h.payment_date,
                    h.vendor_id,
                    h.vendor_name,
                    h.document_total,
                    h.sap_docentry,
                    h.sap_docnum,
                    h.sap_status,
                    h.status,

                    (
                        SELECT l.doc_num
                        FROM "{tenant_schema}".ik_out_payment_inv_line l
                        WHERE l.payment_id = h.payment_id
                        LIMIT 1
                    ) AS doc_num

                FROM "{tenant_schema}".ik_out_payment_header h

                WHERE {where_clause}

                ORDER BY h.created_at DESC

                LIMIT ${len(values)+1}
                OFFSET ${len(values)+2}
            """

            result = await conn.fetch(
                query,
                *values,
                per_page,
                offset
            )

            data = [
                dict(row)
                for row in result
            ]

            return {
                "status": "success",
                "message": "Outgoing payments fetched successfully",
                "meta": {
                    "page": page,
                    "per_page": per_page,
                    "total_records": total_records,
                    "total_pages": total_pages
                },
                "count": len(data),
                "data": data
            }
    
    @staticmethod
    async def get_branch_series(
        conn,
        tenant_schema: str,
        branch_id: str,
        object_code: str
    ):
        try:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            today = datetime.now().strftime("%Y%m%d")

            rows = await SAPApiClient.get_branch_series(
                config=config,
                object_code=object_code,
                date_f=today,
                date_t=today,
                branch_id=branch_id
            )

            data = []

            for row in rows:

                data.append({
                    "branch_id": row.get("BPLId"),
                    "branch_name": row.get("BPLName"),
                    "series": row.get("Series"),
                    "series_name": row.get("SeriesName"),
                    "indicator": row.get("Indicator"),
                    "group_code": row.get("GroupCode"),
                    "from_date": row.get("From Date"),
                    "to_date": row.get("To Date")
                })

            return success_response(data)

        except Exception as e:

            logger.exception("Error fetching branch series")

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Failed to fetch branch series: {str(e)}"
                }
            )

    @staticmethod
    async def get_ip_controled_glaccount(
        conn,
        tenant_schema: str
    ):
        try:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            sap_res = await SAPApiClient.get_ip_controled_glaccount(
                config,
                "A15431000"
            )

            return {
                "status": "success",
                "data": sap_res
            }

        except Exception as e:

            logger.exception("Error fetching controlled GL accounts")

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Failed to fetch controlled GL accounts: {str(e)}"
                }
            )
    @staticmethod
    async def get_cash_gl_accounts(request, db_pool):

        tenant_schema = getattr(request.state, "schema")

        async with db_pool.acquire() as conn:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            sap_res = await SAPApiClient.get_cash_gl_accounts(config)

            return {
                "status": "success",
                "data": sap_res
            }
    @staticmethod
    async def get_control_accounts(request, db_pool):

        tenant_schema = getattr(request.state, "schema")

        async with db_pool.acquire() as conn:

            from app.config.config_service import get_sap_config_by_schema

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            sap_res = await SAPApiClient.get_control_accounts(config)

            return {
                "status": "success",
                "data": sap_res
            }

    @staticmethod
    async def get_gl_master(
        conn,
        tenant_schema: str
    ):
        try:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            rows = await SAPApiClient.get_gl_master(
                config
            )

            data = [
                {
                    "account_code": r.get("Code"),
                    "account_name": r.get("Name"),
                    "is_active": r.get("ActiveAccount"),
                    "balance": r.get("Balance"),
                    "is_control_account": r.get("LockManualTransaction")
                }
                for r in rows
            ]

            return {
                "status": "success",
                "count": len(data),
                "data": data
            }

        except Exception as e:

            logger.exception("Error fetching GL Master")

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Failed to fetch GL Master: {str(e)}"
                }
            )
    
    @staticmethod
    async def get_merchant_mapping(
        conn,
        tenant_schema: str
    ):
        try:

            rows = await conn.fetch(
                f"""
                SELECT
                    m.merchant_id,
                    m.gl_account,
                    g.account_name AS gl_account_name,
                    m.qr_string_vpa,
                    m.branch,
                    m.branch_id
                FROM "{tenant_schema}".ik_merchant_id m
                LEFT JOIN "{tenant_schema}".ik_glaccount g
                    ON g.account_id = m.gl_account
                ORDER BY m.merchant_id
                """
            )

            data = [
                {
                    "merchant_id": row["merchant_id"],
                    "gl_account": row["gl_account"],
                    "gl_account_name": row["gl_account_name"],
                    "qr_string_vpa": row["qr_string_vpa"],
                    "branch": row["branch"],
                    "branch_id": row["branch_id"]
                }
                for row in rows
            ]

            return {
                "status": "success",
                "count": len(data),
                "data": data
            }

        except Exception as e:

            logger.exception(
                "Error fetching merchant mappings"
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Failed to fetch merchant mappings: {str(e)}"
                }
            )
    # =========================
    # GET PAYMENT MEANS LINES
    # =========================
    @staticmethod
    async def get_payment_means_lines(
        conn,
        tenant_schema: str,
        payment_id: str
    ):
        try:
            rows = await conn.fetch(f'''
                SELECT
                    payment_line_id,
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
                    schema_id,
                    upi_status,
                    upi_url,
                    upi_utr,
                    upi_qr_ref,
                    upi_confirmed_at,
                    upi_retry_count
                FROM "{tenant_schema}".ik_inc_payment_paymeans_line
                WHERE payment_id = $1
            ''', payment_id)
 
            data = [
                {
                    "payment_line_id": r["payment_line_id"],
                    "payment_id": r["payment_id"],
                    "cheque_account": r["cheque_account"],
                    "cheque_no": r["cheque_no"],
                    "cheque_duedate": r["cheque_duedate"].isoformat() if r["cheque_duedate"] else None,
                    "bank_name": r["bank_name"],
                    "cheque_amount": float(r["cheque_amount"]) if r["cheque_amount"] is not None else None,
                    "cash_account": r["cash_account"],
                    "cash_amount": float(r["cash_amount"]) if r["cash_amount"] is not None else None,
                    "bank_account": r["bank_account"],
                    "transfer_date": r["transfer_date"].isoformat() if r["transfer_date"] else None,
                    "bank_amount": float(r["bank_amount"]) if r["bank_amount"] is not None else None,
                    "schema_id": r["schema_id"],
                    "upi_status": r["upi_status"],
                    "upi_url": r["upi_url"],      
                    "upi_utr": r["upi_utr"],
                    "upi_qr_ref": r["upi_qr_ref"],
                    "upi_confirmed_at": r["upi_confirmed_at"].isoformat() if r["upi_confirmed_at"] else None,
                    "upi_retry_count": r["upi_retry_count"]
                }
                for r in rows
            ]
 
            return {
                "status": "success",
                "count": len(data),
                "data": data
            }
 
        except Exception:
            logger.exception("Error fetching payment means lines")
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": "Failed to fetch payment means lines"
                }
            )
           
           
    # =========================
    # PATCH PAYMENT MEANS LINE
    # =========================
    @staticmethod
    async def patch_payment_means_line(
        conn,
        tenant_schema: str,
        payment_id: str,
        payload: dict
    ):
        try:
            allowed_fields = {
                "cheque_account",
                "cheque_no",
                "cheque_duedate",
                "bank_name",
                "cheque_amount",
                "cash_account",
                "cash_amount",
                "bank_account",
                "transfer_date",
                "bank_amount",
                "upi_status",
                "upi_url",
                "upi_utr",
                "upi_qr_ref",
                "upi_confirmed_at",
                "upi_retry_count"
            }
 
            updates = {
                k: v for k, v in payload.items()
                if k in allowed_fields
            }
 
            if not updates:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "error",
                        "message": "No valid fields provided for update"
                    }
                )
 
            set_clauses = []
            values = []
 
            for i, (field, value) in enumerate(updates.items(), start=1):
                set_clauses.append(f"{field} = ${i}")
                values.append(value)
 
            values.append(payment_id)  # $N
 
            set_sql = ", ".join(set_clauses)
            n = len(updates)
 
            query = f'''
                UPDATE "{tenant_schema}".ik_inc_payment_paymeans_line
                SET {set_sql}
                WHERE payment_id = ${n + 1}
                RETURNING
                    payment_line_id,
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
                    schema_id,
                    upi_status,
                    upi_url,
                    upi_utr,
                    upi_qr_ref,
                    upi_confirmed_at,
                    upi_retry_count
            '''
 
            rows = await conn.fetch(query, *values)
 
            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "status": "error",
                        "message": "No payment means lines found for this payment_id"
                    }
                )
 
            data = [
                {
                    "payment_line_id": r["payment_line_id"],
                    "payment_id": r["payment_id"],
                    "cheque_account": r["cheque_account"],
                    "cheque_no": r["cheque_no"],
                    "cheque_duedate": r["cheque_duedate"].isoformat() if r["cheque_duedate"] else None,
                    "bank_name": r["bank_name"],
                    "cheque_amount": float(r["cheque_amount"]) if r["cheque_amount"] is not None else None,
                    "cash_account": r["cash_account"],
                    "cash_amount": float(r["cash_amount"]) if r["cash_amount"] is not None else None,
                    "bank_account": r["bank_account"],
                    "transfer_date": r["transfer_date"].isoformat() if r["transfer_date"] else None,
                    "bank_amount": float(r["bank_amount"]) if r["bank_amount"] is not None else None,
                    "schema_id": r["schema_id"],
                    "upi_status": r["upi_status"],
                    "upi_url": r["upi_url"],      
                    "upi_utr": r["upi_utr"],
                    "upi_qr_ref": r["upi_qr_ref"],
                    "upi_confirmed_at": r["upi_confirmed_at"].isoformat() if r["upi_confirmed_at"] else None,
                    "upi_retry_count": r["upi_retry_count"]
                }
                for r in rows
            ]
 
            return {
                "status": "success",
                "message": "Payment means lines updated successfully",
                "count": len(data),
                "data": data
            }
 
        except HTTPException:
            raise
 
        except Exception:
            logger.exception("Error updating payment means lines")
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": "Failed to update payment means lines"
                }
            )
           
    # =========================
    # CREATE INCOMING PAYMENT (SAP DIRECT)
    # =========================
    @staticmethod
    async def create_incoming_payment_sap(
        request,
        payload: dict,
        db_pool,
        current_user: dict
    ):
        try:
            async with db_pool.acquire() as conn:
 
                tenant_schema = getattr(request.state, "schema", None) \
                    or current_user.get("company_schema")
 
                config = await get_sap_config_by_schema(
                    conn,
                    tenant_schema
                )
                payment_id = payload.get("CounterReference")
                print("PAYLOAD PAYMENT ID =", payload.get("U_PaymentId"))
                print("COUNTER REF =", payload.get("CounterReference"))

                # Forward the full payload as-is to SAP
                sap_response = await SAPApiClient.post_incoming_payment(
                    config,
                    payload
                )

                log_service = LogService(conn)

                await log_service.log_success(
                    schema=tenant_schema,
                    schema_id=tenant_schema,
                    type="IncomingPayment",
                    msg=f"Incoming Payment Posted : {payment_id}",
                    payload=payload
                )
                if payment_id:

                    await conn.execute(
                        f'''
                        UPDATE "{tenant_schema}".ik_inc_payment_header
                        SET
                            status = 'Close',
                            sap_status = 'Posted',
                            sap_docentry = $1,
                            sap_docnum = $2,
                            series_id = $3,
                            journal_remarks = $4,
                            updated_at = NOW()
                        WHERE payment_id = $5
                        ''',
                        str(sap_response.get("DocEntry")),
                        str(sap_response.get("DocNum")),
                        sap_response.get("Series"),
                        sap_response.get("JournalRemarks"),
                        payment_id
                    )
                return {
                    "status": "success",
                    "message": "Incoming payment created successfully in SAP",
                    "payment_id": payment_id,
                    "sap_docentry": sap_response.get("DocEntry"),
                    "sap_docnum": sap_response.get("DocNum"),
                    "sap_request": payload,
                    "sap_response": sap_response
                }
 
        except HTTPException:
            raise
 
        except Exception as e:

            error_msg = str(e)

            if payment_id:

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

            try:

                async with db_pool.acquire() as log_conn:

                    log_service = LogService(log_conn)

                    await log_service.log_error(
                        schema=tenant_schema,
                        schema_id=tenant_schema,
                        type="IncomingPayment",
                        msg=error_msg,
                        payload=payload
                    )

            except Exception as log_ex:

                print("LOGGING FAILED:", str(log_ex))

            raise Exception(
                extract_sap_error(error_msg)
            )

    # =========================

    # CREATE INCOMING PAYMENT (SAVE TO DB ONLY)

    # =========================

    @staticmethod

    async def create_incoming_db_sap(

        request,

        payload: dict,

        db_pool,

        current_user: dict

    ):

        try:

            async with db_pool.acquire() as conn:

                async with conn.transaction():
    
                    tenant_schema = (

                        getattr(request.state, "schema", None)

                        or current_user.get("company_schema")

                    )

                    user_id = str(current_user.get("user_id"))

                    # -------------------------
                    # READ INVOICE / ACCOUNT LINES
                    # -------------------------

                    payment_invoices = (
                        payload.get("PaymentInvoices")
                        or payload.get("PaymentInvoicesCollection")
                        or []
                    )

                    account_lines = (
                        payload.get("AccountPayments")
                        or payload.get("PaymentAccounts")
                         or payload.get("accounts")
                        or []
                    )

                    # -------------------------
                    # CALCULATE DOCUMENT TOTAL
                    # -------------------------

                    doc_total = 0

                    for inv in payment_invoices:
                        doc_total += float(
                            inv.get("SumApplied")
                            or inv.get("AppliedAmount")
                            or inv.get("total_amount")
                            or 0
                        )

                    for acc in account_lines:
                        doc_total += float(
                            acc.get("SumPaid")
                            or acc.get("Amount")
                            or acc.get("total_amount")
                            or 0
                        )

                    if doc_total == 0:

                        payments = payload.get("payments", {})

                        cash = payments.get("cash", {})
                        transfer = (
                            payments.get("transfer")
                            or payments.get("upi")
                            or {}
                        )


                        doc_total = (
                            float(
                                cash.get("amount")
                                or cash.get("total_amount")
                                or payload.get("CashSum")
                                or 0
                            )
                            +
                            float(
                                transfer.get("amount")
                                or transfer.get("total_amount")
                                or payload.get("TransferSum")
                                or 0
                            )
                        )

                    # -------------------------
                    # GENERATE PAYMENT ID
                    # -------------------------


                    payment_id = str(await generate_id(

                        conn, tenant_schema, "ik_inc_payment_seq", "INCPH"

                    ))
    
                    # -------------------------

                    # EXTRACT FIELDS FROM PAYLOAD

                    # -------------------------

                    from datetime import datetime, date

                    payment_date = (
                        payload.get("DocDate")
                        or payload.get("payment_date")
                    )

                    if payment_date:
                        if isinstance(payment_date, str):
                            payment_date = datetime.strptime(
                                payment_date,
                                "%Y-%m-%d"
                            ).date()
                    else:
                        payment_date = date.today()

                    card_code = (
                        payload.get("CardCode")
                        or payload.get("customer_id")
                    )

                    customer_name = ( payload.get("customer_name")
                        or payload.get("CardName")
                    )

                    branch_id = (
                        payload.get("BPLID")
                        or payload.get("branch_id")
                    )

                    branch_name = (
                        payload.get("BPLName")
                        or payload.get("branch_name")
                    )
                    payment_type = (
                        payload.get("payment_type")
                        or (
                            "Account"
                            if payload.get("DocType") == "rAccount"
                            else "Customer"
                        )
                    )

                    if payment_type == "Customer":
                        customer_name_value = customer_name
                    else:
                        customer_name_value = None

                    remarks = (
                        payload.get("Remarks")
                        or payload.get("remarks")
                        or ""
                    )
                    transfer_date = payment_date

                    transfer_date = (
                        payload.get("TransferDate")
                        or payload.get("payment_date")
                    )

                    if transfer_date and isinstance(transfer_date, str):
                        transfer_date = datetime.strptime(
                            transfer_date,
                            "%Y-%m-%d"
                        ).date()
                    is_pay_onaccount = bool(
                        payload.get("is_payment_onaccount", False)
                    )

                    control_account_id = (
                        payload.get("control_account_id")
                    )

                    # INSERT HEADER

                    # -------------------------

                    await conn.execute(f'''
                        INSERT INTO "{tenant_schema}".ik_inc_payment_header
                        (
                            payment_id,
                            payment_date,
                            customer_id,
                            customer_name,
                            payment_type,
                            mode_of_payment,
                            remarks,
                            is_pay_onaccount,
                            control_account_id,
                            status,
                            sap_status,
                            created_by,
                            updated_by,
                            schema_id,
                            document_total,
                            branch,
                            branch_id
                        )
                        VALUES
                        (
                            $1,$2,$3,$4,$5,$6,$7,
                            $8,
                            $9,
                            'Draft',
                            'Pending',
                            $10,$10,$11,$12,$13,$14
                        )
                    ''',

                        payment_id,
                        payment_date,
                        card_code,
                        customer_name_value,
                        payment_type,
                        payload.get("U_MDP") or None,
                        remarks,

                        is_pay_onaccount,
                        control_account_id,

                        user_id,
                        tenant_schema,
                        doc_total,
                        branch_name,
                        str(branch_id) if branch_id else None
                    )
    
                    # -------------------------
                    # INSERT INVOICE LINES
                    # -------------------------

                    payment_invoices = (
                        payload.get("PaymentInvoices")
                        or payload.get("PaymentInvoicesCollection")
                        or payload.get("invoices")
                        or []
                    )

                    for inv in payment_invoices:

                        inv_line_id = str(
                            await generate_id(
                                conn,
                                tenant_schema,
                                "ik_inc_payment_line_seq",
                                "INPIL"
                            )
                        )

                        print("INVOICE ROW =", inv)

                        await conn.execute(
                            f'''
                            INSERT INTO "{tenant_schema}".ik_inc_payment_inv_line
                            (
                                payment_line_id,
                                payment_id,
                                doc_type,
                                doc_entry,
                                doc_num,
                                balance_due,
                                total_amount,
                                overdue_days,
                                schema_id
                            )
                            VALUES
                            (
                                $1,$2,$3,$4,$5,$6,$7,$8,$9
                            )
                            ''',

                            inv_line_id,
                            payment_id,

                            str(
                                inv.get("InvoiceType")
                                or inv.get("doc_type")
                                or ""
                            ),

                            str(
                                inv.get("DocEntry")
                                or inv.get("doc_entry")
                                or ""
                            ),

                            str(
                                inv.get("DocNum")
                                or inv.get("doc_num")
                                or ""
                            ),

                            float(
                                inv.get("BalanceDue")
                                or inv.get("balance_due")
                                or 0
                            ),

                            float(
                                inv.get("SumApplied")
                                or inv.get("AppliedAmount")
                                or inv.get("total_amount")
                                or 0
                            ),

                            int(
                                inv.get("OverdueDays")
                                or inv.get("overdue_days")
                                or 0
                            ),

                            

                            tenant_schema
                        )
                    # -------------------------
                    # INSERT ACCOUNT LINES
                    # -------------------------

                    account_lines = (
                        payload.get("AccountPayments")
                        or payload.get("PaymentAccounts")
                        or payload.get("accounts")
                        or []
                    )

                    for acc in account_lines:

                        acct_line_id = str(
                            await generate_id(
                                conn,
                                tenant_schema,
                                "ik_inc_payment_acct_line_seq",
                                "INPAL"
                            )
                        )

                        await conn.execute(f'''
                            INSERT INTO "{tenant_schema}".ik_inc_payment_acct_line
                            (
                                payment_line_id,
                                payment_id,
                                account_id,
                                account_name,
                                remarks,
                                total_amount,
                                schema_id
                            )
                            VALUES
                            (
                                $1,$2,$3,$4,$5,$6,$7
                            )
                        ''',

                            acct_line_id,
                            payment_id,

                            str(
                                acc.get("account_id")
                                or acc.get("AccountCode")
                                or ""
                            ),

                            str(
                                acc.get("AccountName")
                                or acc.get("account_name")
                                or ""
                            ),

                            str(
                                acc.get("Remarks")
                                or ""
                            ),

                            float(
                                acc.get("SumPaid")
                                or acc.get("total_amount")
                                or 0
                            ),

                            tenant_schema
                        )
                    # -------------------------

                    # INSERT PAYMENT MEANS LINE

                    # -------------------------

                    pay_line_id = str(await generate_id(

                        conn, tenant_schema,

                        "ik_inc_payment_paymeans_seq", "INPPM"

                    ))
    
                    payments = payload.get("payments", {})

                    cash = payments.get("cash", {})

                    transfer = (
                        payments.get("transfer")
                        or payments.get("upi")
                        or {}
                    )

                    cash_account = (
                        cash.get("account_id")
                        or payload.get("CashAccount")
                    )

                    cash_amount = float(
                        cash.get("amount")
                        or cash.get("total_amount")
                        or payload.get("CashSum")
                        or 0
                    ) or None

                    bank_account = (
                        transfer.get("account_id")
                        or payload.get("TransferAccount")
                    )

                    print("PAYMENTS =", payments)
                    print("TRANSFER =", transfer)
                    print("BANK_ACCOUNT =", bank_account)
                    bank_amount = float(
                        transfer.get("amount")
                        or transfer.get("total_amount")
                        or payload.get("TransferSum")
                        or 0
                    ) or None

                    transfer_date = payload.get("TransferDate")

                    if transfer_date:
                        if isinstance(transfer_date, str):
                            transfer_date = datetime.strptime(
                                transfer_date,
                                "%Y-%m-%d"
                            ).date()
                    else:
                        transfer_date = payment_date

                    check_account  = payload.get("CheckAccount")

                    cheque_no      = None

                    cheque_amount  = None

                    cheque_duedate = None

                    bank_name      = None
    
                    checks = payload.get("PaymentChecks", [])

                    if checks:

                        chk            = checks[0]

                        cheque_no      = str(chk.get("CheckNumber")) if chk.get("CheckNumber") else None

                        cheque_amount  = float(chk.get("CheckSum") or 0) or None

                        cheque_duedate = payment_date

                        bank_name      = str(chk.get("BankCode") or chk.get("BankName") or "")
    
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

                        check_account,

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
    
                    return {

                        "status": "success",

                        "message": "Incoming payment saved successfully",

                        "payment_id": payment_id

                    }
    
        except HTTPException:

            raise
    
        except Exception as e:

            error_msg = extract_sap_error(str(e))

            logger.exception("Error saving incoming payment to DB")

            raise HTTPException(

                status_code=400,

                detail={

                    "status": "error",

                    "message": error_msg

                }

            )
    
    @staticmethod
    async def get_incoming_payment_by_id(
        conn,
        tenant_schema: str,
        payment_id: str
    ):
        header = await conn.fetchrow(f'''
            SELECT *
            FROM "{tenant_schema}".ik_inc_payment_header
            WHERE payment_id = $1
        ''', payment_id)

        if not header:
            raise HTTPException(
                status_code=404,
                detail="Incoming payment not found"
            )

        invoices = await conn.fetch(f'''
            SELECT *
            FROM "{tenant_schema}".ik_inc_payment_inv_line
            WHERE payment_id = $1
        ''', payment_id)

        accounts = await conn.fetch(f'''
            SELECT *
            FROM "{tenant_schema}".ik_inc_payment_acct_line
            WHERE payment_id = $1
        ''', payment_id)

        paymeans = await conn.fetch(f'''
            SELECT *
            FROM "{tenant_schema}".ik_inc_payment_paymeans_line
            WHERE payment_id = $1
        ''', payment_id)

        return {
            "status": "success",
            "data": {
                "header": dict(header),
                "invoice_lines": [dict(r) for r in invoices],
                "account_lines": [dict(r) for r in accounts],
                "payment_means": [dict(r) for r in paymeans]
            }
        }
    @staticmethod
    async def get_outgoing_payment_by_id(
        conn,
        tenant_schema: str,
        payment_id: str
    ):
        header = await conn.fetchrow(f'''
            SELECT *
            FROM "{tenant_schema}".ik_out_payment_header
            WHERE payment_id = $1
        ''', payment_id)

        if not header:
            raise HTTPException(
                status_code=404,
                detail="Outgoing payment not found"
            )

        invoices = await conn.fetch(f'''
            SELECT *
            FROM "{tenant_schema}".ik_out_payment_inv_line
            WHERE payment_id = $1
        ''', payment_id)

        accounts = await conn.fetch(f'''
            SELECT *
            FROM "{tenant_schema}".ik_out_payment_acct_line
            WHERE payment_id = $1
        ''', payment_id)

        paymeans = await conn.fetch(f'''
            SELECT *
            FROM "{tenant_schema}".ik_out_payment_paymeans_line
            WHERE payment_id = $1
        ''', payment_id)

        return {
            "status": "success",
            "data": {
                "header": dict(header),
                "invoice_lines": [dict(r) for r in invoices],
                "account_lines": [dict(r) for r in accounts],
                "payment_means": [dict(r) for r in paymeans]
            }
        }
    
    @staticmethod
    async def get_incoming_payment_report(
        conn,
        tenant_schema: str,
        doc_key: int
    ):
        try:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            rows = await SAPApiClient.get_incoming_payment_report(
                config,
                doc_key
            )

            return {
                "status": "success",
                "data": rows
            }

        except Exception as e:

            logger.exception(
                "Error fetching Incoming Payment Report"
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Failed to fetch Incoming Payment Report: {str(e)}"
                }
            )
    @staticmethod
    async def get_outgoing_payment_report(
        conn,
        tenant_schema: str,
        doc_key: int
    ):
        try:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            rows = await SAPApiClient.get_outgoing_payment_report(
                config,
                doc_key
            )

            return {
                "status": "success",
                "data": rows
            }

        except Exception as e:

            logger.exception(
                "Error fetching Outgoing Payment Report"
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Failed to fetch Outgoing Payment Report: {str(e)}"
                }
            )

    @staticmethod
    async def get_outgoing_payment_cheque_report(
        conn,
        tenant_schema: str,
        check_key: int
    ):
        try:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            rows = await SAPApiClient.get_outgoing_payment_cheque_report(
                config,
                check_key
            )

            return {
                "status": "success",
                "data": rows
            }

        except Exception as e:

            logger.exception(
                "Error fetching Outgoing Payment Cheque Report"
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Failed to fetch Outgoing Payment Cheque Report: {str(e)}"
                }
            )

    @staticmethod
    async def get_house_bank_accounts(
        conn,
        tenant_schema: str
    ):
        try:

            config = await get_sap_config_by_schema(
                conn,
                tenant_schema
            )

            rows = await SAPApiClient.get_house_bank_accounts(
                config
            )

            data = [
                {
                    "bank_code": row.get("BankCode"),
                    "account_no": row.get("AccNo"),
                    "branch": row.get("Branch"),
                    "gl_account": row.get("GLAccount"),
                    "country": row.get("Country")
                }
                for row in rows
            ]

            return {
                "status": "success",
                "count": len(data),
                "data": data
            }

        except Exception as e:

            logger.exception(
                "Error fetching House Bank Accounts"
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Failed to fetch House Bank Accounts: {str(e)}"
                }
            )

    @staticmethod
    async def process_pending_upi_payments(
        request,
        db_pool,
        current_user
    ):
        async with db_pool.acquire() as conn:

            tenant_schema = (
                getattr(request.state, "schema", None)
                or current_user.get("company_schema")
            )

            rows = await conn.fetch(f"""
                SELECT h.payment_id
                FROM "{tenant_schema}".ik_inc_payment_header h
                INNER JOIN "{tenant_schema}".ik_inc_payment_paymeans_line p
                    ON h.payment_id = p.payment_id
                WHERE
                    p.upi_status = 'SUCCESS'
                    AND h.sap_status = 'Pending'
            """)

            for row in rows:

                payment_id = row["payment_id"]

                try:

                    # Build SAP payload from DB
                    payload = await SapPaymentService.create_incoming_db_sap(
                        conn,
                        tenant_schema,
                        payment_id
                    )

                    # Post to SAP
                    await SapPaymentService.create_incoming_payment_sap(
                        request=request,
                        payload=payload,
                        db_pool=db_pool,
                        current_user=current_user
                    )

                except Exception as e:

                    await SapPaymentService.log_scheduler_error(
                        conn,
                        tenant_schema,
                        payment_id,
                        payload if 'payload' in locals() else {},
                        str(e)
                    )

                    continue

    @staticmethod
    async def log_scheduler_error(
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
                sap_status = 'Failed',
                updated_at = NOW()
            WHERE payment_id = $1
            """,
            payment_id
        )

    @staticmethod
    async def build_sap_payload_from_db(
        conn,
        tenant_schema: str,
        payment_id: str
    ):

        header = await conn.fetchrow(
            f"""
            SELECT *
            FROM "{tenant_schema}".ik_inc_payment_header
            WHERE payment_id = $1
            """,
            payment_id
        )

        if not header:
            raise Exception(
                f"Incoming payment not found: {payment_id}"
            )

        invoice_rows = await conn.fetch(
            f"""
            SELECT *
            FROM "{tenant_schema}".ik_inc_payment_inv_line
            WHERE payment_id = $1
            """,
            payment_id
        )

        account_rows = await conn.fetch(
            f"""
            SELECT *
            FROM "{tenant_schema}".ik_inc_payment_acct_line
            WHERE payment_id = $1
            """,
            payment_id
        )

        paymeans = await conn.fetchrow(
            f"""
            SELECT *
            FROM "{tenant_schema}".ik_inc_payment_paymeans_line
            WHERE payment_id = $1
            LIMIT 1
            """,
            payment_id
        )

        payment_date = header["payment_date"]

        is_on_account = bool(
            header["is_pay_onaccount"]
        )

        payment_type = (
            header["payment_type"]
            or "Customer"
        )

        invoice_type_map = {
            "A/R Invoice": "it_Invoice",
            "Invoice": "it_Invoice",
            "A/R Credit Memo": "it_CredItnote",
            "Credit Memo": "it_CredItnote",
            "AR Down Payment": "it_DownPayment",
            "Down Payment": "it_DownPayment"
        }

        # ==========================================
        # ACCOUNT PAYMENT
        # ==========================================
        if payment_type == "Account":

            payload = {
                "DocType": "rAccount",
                "DocDate": payment_date.strftime("%Y-%m-%d"),
                "TaxDate": payment_date.strftime("%Y-%m-%d"),
                "DueDate": payment_date.strftime("%Y-%m-%d"),
                "BPLID": (
                    int(header["branch_id"])
                    if header["branch_id"]
                    else None
                ),
                "CounterReference": payment_id,
                "Remarks": header["remarks"] or "",
                "U_MDP": (
                    header["mode_of_payment"]
                    or "BankTransfer"
                )
            }

            payload["PaymentAccounts"] = [
                {
                    "AccountCode": row["account_id"],
                    "SumPaid": float(
                        row["total_amount"] or 0
                    )
                }
                for row in account_rows
            ]

        # ==========================================
        # CUSTOMER PAYMENT
        # ==========================================
        else:

            payload = {
                "DocType": "rCustomer",
                "DocDate": payment_date.strftime("%Y-%m-%d"),
                "TaxDate": payment_date.strftime("%Y-%m-%d"),
                "DueDate": payment_date.strftime("%Y-%m-%d"),
                "CardCode": header["customer_id"],
                "CardName": header["customer_name"],
                "BPLID": (
                    int(header["branch_id"])
                    if header["branch_id"]
                    else None
                ),
                "BPLName": header["branch"],
                "CounterReference": payment_id,
                "Remarks": header["remarks"] or "",
                "U_MDP": (
                    header["mode_of_payment"]
                    or "UPI"
                )
            }

            # ======================================
            # CUSTOMER ON ACCOUNT
            # ======================================
            if is_on_account:

                payload["PaymentInvoices"] = []

                if header["control_account_id"]:

                    payload["ControlAccount"] = (
                        header["control_account_id"]
                    )

            # ======================================
            # CUSTOMER INVOICE PAYMENT
            # ======================================
            else:

                payload["PaymentInvoices"] = [
                    {
                        "DocEntry": int(
                            row["doc_entry"]
                        ),
                        "SumApplied": float(
                            row["total_amount"] or 0
                        ),
                        "InvoiceType": (
                            row["doc_type"]
                            if str(row["doc_type"]).startswith("it_")
                            else invoice_type_map.get(
                                str(row["doc_type"]).strip(),
                                "it_Invoice"
                            )
                        )
                    }
                    for row in invoice_rows
                ]

        # ==========================================
        # PAYMENT MEANS
        # ==========================================
        if paymeans:

            payload["TransferAccount"] = (
                paymeans["bank_account"]
            )

            payload["TransferSum"] = float(
                paymeans["bank_amount"] or 0
            )

            payload["TransferDate"] = (
                paymeans["transfer_date"].strftime("%Y-%m-%d")
                if paymeans["transfer_date"]
                else payment_date.strftime("%Y-%m-%d")
            )

            payload["TransferReference"] = (
                paymeans["upi_utr"] or ""
            )

            payload["U_IKQRUTR"] = (
                paymeans["upi_utr"] or ""
            )

            payload["U_IKQRDE"] = (
                paymeans["upi_qr_ref"]
                or payment_id
            )

        print("=" * 100)
        print("PAYMENT ID =", payment_id)
        print(
            "SAP PAYLOAD =",
            json.dumps(
                payload,
                indent=4,
                default=str
            )
        )
        print("=" * 100)

        return payload