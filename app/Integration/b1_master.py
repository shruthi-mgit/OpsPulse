import logging

logger = logging.getLogger("sap-master-service")


class SapMasterService:

    # ===============================
    # BRANCH
    # ===============================
    @staticmethod
    async def save_branch(conn, tenant_schema: str, data: dict):

        branch_id = str(data.get("Code"))
        branch_name = data.get("Name")

        if branch_id is None:
            raise ValueError("branch_id required")

        if not branch_name:
            raise ValueError("branch_name required")

        await conn.execute(
            f"""
            INSERT INTO "{tenant_schema}".ik_branch
            (
                branch_id,
                branch_name,
                is_active
            )
            VALUES
            ($1,$2,TRUE)

            ON CONFLICT (branch_id)
            DO UPDATE SET
                branch_name = EXCLUDED.branch_name,
                is_active = TRUE
            """,
            branch_id,
            branch_name,
        )

    # ===============================
    # BANK
    # ===============================
    @staticmethod
    async def save_bank(conn, tenant_schema: str, data: dict):

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
                is_active
            )
            VALUES
            ($1,$2,TRUE)

            ON CONFLICT (bank_id)
            DO UPDATE SET
                bank_name = EXCLUDED.bank_name,
                is_active = TRUE
            """,
            bank_id,
            bank_name,
        )

   
    # GL ACCOUNT
    # ===============================
    @staticmethod
    async def save_glaccount(conn, tenant_schema: str, data: dict):

        account_id = data.get("Code")
        account_name = data.get("Name")

        if not account_id:
            raise ValueError("account_id required")

        if not account_name:
            raise ValueError("account_name required")

        await conn.execute(
            f"""
            INSERT INTO "{tenant_schema}".ik_glaccount
            (
                account_id,
                account_name,
                is_active
            )
            VALUES
            ($1,$2,TRUE)

            ON CONFLICT (account_id)
            DO UPDATE SET
                account_name = EXCLUDED.account_name,
                is_active = TRUE
            """,
            account_id,
            account_name,
        )