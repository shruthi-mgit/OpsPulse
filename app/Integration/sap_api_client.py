import httpx

from app.Integration.sap_session_cache import (
    get_session,
    set_session,
    delete_session
)
TIMEOUT = httpx.Timeout(
    connect=30.0,
    read=300.0,
    write=300.0,
    pool=300.0
)

class SAPApiClient:


    # Reusable client
    client = httpx.AsyncClient(
        verify=False,
        timeout=TIMEOUT
    )

    # =========================
    # LOGIN
    # =========================
    @staticmethod
    async def login(config):

        user_id = config["user_id"]
        schema_id = config["schema_id"]

        # =========================================
        # CHECK EXISTING SESSION
        # =========================================
        existing_session = await get_session(
            user_id=user_id,
            schema_id=schema_id
        )

        if existing_session:

            return {
                "B1SESSION": existing_session["session_id"]
            }

        # =========================================
        # SAP LOGIN
        # =========================================
        url = f"{config['base_url']}/Login"

        payload = {
            "CompanyDB": config["sap_db"],
            "UserName": config["sap_username"],
            "Password": config["sap_password"],
        }

        r = await SAPApiClient.client.post(
            url,
            json=payload
        )

        r.raise_for_status()

        session_id = r.cookies.get("B1SESSION")

        # =========================================
        # SAVE SESSION
        # =========================================
        await set_session(
            user_id=user_id,
            schema_id=schema_id,
            sap_user_name=config["sap_username"],
            session_id=session_id,
            sap_db=config["sap_db"],
            password=config["sap_password"]
        )

        print(f"✅ SAP login success for DB: {config['sap_db']}")

        return {
            "B1SESSION": session_id
        }

    # =========================
    # GENERIC PAGINATION
    # =========================
    @staticmethod
    async def get_all_data(endpoint: str, config: dict):

        base_url = config["base_url"]

        all_data = []
        next_endpoint = endpoint

        cookies = await SAPApiClient.login(config)

        while next_endpoint:

            url = f"{base_url}/{next_endpoint}"

            r = await SAPApiClient.client.get(
                url,
                cookies=cookies
            )

            if r.status_code == 401:

                await delete_session(
                    config["user_id"],
                    config["schema_id"]
                )

                cookies = await SAPApiClient.login(config)

                r = await SAPApiClient.client.get(
                    url,
                    cookies=cookies
                )

            if r.status_code >= 400:

                print("\n========== SAP ERROR ==========")
                print("URL:", url)
                print("STATUS:", r.status_code)
                print("BODY:", r.text)
                print("===============================\n")

                r.raise_for_status()

            try:
                data = r.json()
            except Exception:
                print("Invalid JSON Response:")
                print(r.text)
                raise

            all_data.extend(
                data.get("value", [])
            )

            next_link = data.get("@odata.nextLink")

            if next_link:
                next_endpoint = next_link.replace(
                    f"{base_url}/",
                    ""
                )
            else:
                next_endpoint = None

        return all_data
    # =========================
    # STREAM PAGINATION
    # =========================
    @staticmethod
    async def stream_data(endpoint: str, config: dict):

        base_url = config["base_url"]

        next_endpoint = endpoint

        cookies = await SAPApiClient.login(config)

        while next_endpoint:

            url = f"{base_url}/{next_endpoint}"

            

            r = await SAPApiClient.client.get(
                url,
                cookies=cookies
            )

            if r.status_code == 401:

                await delete_session(
                    config["user_id"],
                    config["schema_id"]
                )

                cookies = await SAPApiClient.login(config)


            r.raise_for_status()

            data = r.json()

            # ✅ return one page
            yield data.get("value", [])

            next_link = data.get("@odata.nextLink")

            if next_link:
                next_endpoint = next_link.replace(
                    f"{base_url}/",
                    ""
                )
            else:
                next_endpoint = None
    # =========================
    # MASTER APIs
    # =========================
    @staticmethod
    async def get_branches_all(config):
        return await SAPApiClient.get_all_data(
            "SQLQueries('DADA_FtechBranches')/List", config
        )

    @staticmethod
    async def get_banks_all(config):
        return await SAPApiClient.get_all_data(
            "Banks?$select=BankCode,BankName", config
        )

    @staticmethod
    async def get_gl_all(config):
        query = (
            "ChartOfAccounts"
            "?$select=Code,Name,ActiveAccount,Balance"
            "&$filter=ActiveAccount eq 'tYES' "
            "and ValidFor eq 'tYES' "
            "and LockManualTransaction eq 'tNO'"
        )
        return await SAPApiClient.get_all_data(query, config)

    @staticmethod
    async def get_bp_all(config):

        query = (
            "BusinessPartners?"
            "$select="
            "CardCode,"
            "CardName,"
            "CardType,"
            "City,"
            "ZipCode,"
            "Country,"
            "EmailAddress,"
            "Phone1,"
            "Cellular,"
            "CurrentAccountBalance,"
            "FederalTaxID,"
            "DebitorAccount"
            "&$filter=CardType eq 'cCustomer' or CardType eq 'cSupplier'"
        )

        async for page in SAPApiClient.stream_data(
            query,
            config
        ):
            yield page
    @staticmethod
    async def get_bp_customers(config):
        query = (
            "BusinessPartners?"
            "$select=CardCode,CardName,CardType,City,Country,Balance"
            "&$filter=CardType eq 'cCustomer'"
            "&$orderby=CardName"
        )
        return await SAPApiClient.get_all_data(query, config)

    @staticmethod
    async def get_bp_suppliers(config):
        query = (
            "BusinessPartners?"
            "$select=CardCode,CardName,CardType,ZipCode,Country,EmailAddress,City,Balance"
            "&$filter=CardType eq 'cSupplier'"
            "&$orderby=CardName"
        )
        return await SAPApiClient.get_all_data(query, config)

    # =========================
    # WAREHOUSE APIs
    # =========================
    @staticmethod
    async def get_warehouses_all(config):

        query = (
            "Warehouses?$filter=Inactive eq 'tNO'"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )

    # =========================
    # ITEM APIs
    # =========================
    @staticmethod
    async def get_items_all(config):

        query = (
            "Items?"
            "$select="
            "ItemCode,"
            "ItemName,"
            "ItemsGroupCode,"
            "InventoryItem,"
            "SalesItem,"
            "PurchaseItem,"
            "DefaultWarehouse,"
            "ManageSerialNumbers,"
            "ManageBatchNumbers,"
            "Valid"
        )

        async for page in SAPApiClient.stream_data(
            query,
            config
        ):
            yield page

    # =========================
    # SERIAL NUMBER APIs
    # =========================
    @staticmethod
    async def get_serial_numbers(
        config,
        item_code: str,
        whs_code: str
    ):

        endpoint = (
            f"sml.svc/IK_SERIALDETAILSParameters("
            f"P_ITEMCODE='{item_code}',"
            f"P_WHSCODE='{whs_code}'"
            f")/IK_SERIALDETAILS"
        )

        base_url = config["base_url"]

        cookies = await SAPApiClient.login(config)

        all_data = []
        skip = 0

        while True:

            url = f"{base_url}/{endpoint}?$skip={skip}"

            print("SAP URL =>", url)

            r = await SAPApiClient.client.get(
                url,
                cookies=cookies
            )

            if r.status_code == 401:

                await delete_session(
                    config["user_id"],
                    config["schema_id"]
                )

                cookies = await SAPApiClient.login(config)

                r = await SAPApiClient.client.get(
                    url,
                    cookies=cookies
                )

            if r.status_code >= 400:

                print("SAP ERROR =>", r.text)
                break

            data = r.json()

            rows = data.get("value", [])

            if not rows:
                break

            all_data.extend(rows)

            print(f"Fetched {len(rows)} records")

            # stop when last page received
            if len(rows) < 20:
                break

            skip += 20

        return all_data


    @staticmethod
    async def get_batch_numbers(
        config,
        item_code: str,
        whs_code: str
    ):

        query = (
            "SQLQueries('BatchDetails')/List"
            f"?ItemCode='{item_code}'"
            f"&WhsCode='{whs_code}'"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )
    # =========================
    # CUSTOMER APIs
    # =========================
    @staticmethod
    async def get_customer_by_code(customer_code: str, config: dict):
        return await SAPApiClient.get_all_data(
            f"BusinessPartners?$filter=CardCode eq '{customer_code}'",
            config
        )

    @staticmethod
    async def get_customer_due_invoices(
        customer_code: str,
        bpl_id: int,
        config: dict
    ):
        base_url = config["base_url"]

        endpoint = (
            f"sml.svc/"
            f"IK_CUSTOMER_BALANCEDUEParameters("
            f"P_CUSTOMERCODE='{customer_code}',"
            f"P_BPLID={bpl_id}"
            f")/IK_CUSTOMER_BALANCEDUE"
        )

        all_data = []

        cookies = await SAPApiClient.login(config)

        while endpoint:
            url = f"{base_url}/{endpoint}"

            r = await SAPApiClient.client.get(
                url,
                cookies=cookies
            )

            if r.status_code == 500:
                await delete_session(
                    config["user_id"],
                    config["schema_id"]
                )

                cookies = await SAPApiClient.login(config)
                continue

            r.raise_for_status()

            data = r.json()
            all_data.extend(data.get("value", []))

            next_link = data.get("@odata.nextLink")

            if next_link:
                endpoint = (
                    next_link
                    if next_link.startswith("sml.svc")
                    else f"sml.svc/{next_link}"
                )
            else:
                endpoint = None

        return all_data

    # =========================
    # VENDOR APIs
    # =========================
    @staticmethod
    async def get_vendor_due_invoices(
        vendor_code: str,
        bpl_id: int,
        config: dict
    ):
        base_url = config["base_url"]

        endpoint = (
            f"sml.svc/"
            f"IK_VENDOR_BALANCEDUEParameters("
            f"P_VENDORCODE='{vendor_code}',"
            f"P_BPLID={bpl_id}"
            f")/IK_VENDOR_BALANCEDUE"
        )

        all_data = []

        cookies = await SAPApiClient.login(config)

        while endpoint:

            url = f"{base_url}/{endpoint}"

            r = await SAPApiClient.client.get(
                url,
                cookies=cookies
            )

            if r.status_code == 401:
                await delete_session(
                    config["user_id"],
                    config["schema_id"]
                )

                cookies = await SAPApiClient.login(config)
                continue

            r.raise_for_status()

            data = r.json()
            all_data.extend(data.get("value", []))

            next_link = data.get("@odata.nextLink")

            if next_link:
                endpoint = (
                    next_link
                    if next_link.startswith("sml.svc")
                    else f"sml.svc/{next_link}"
                )
            else:
                endpoint = None

        return all_data

    # =========================
    # DASHBOARD APIs
    # =========================
    @staticmethod
    async def get_open_ar_invoices(config):
        return await SAPApiClient.get_all_data(
            "Invoices?$filter=DocumentStatus eq 'bost_Open'",
            config
        )

    @staticmethod
    async def get_open_ap_invoices(config):
        return await SAPApiClient.get_all_data(
            "PurchaseInvoices?$filter=DocumentStatus eq 'bost_Open'",
            config
        )

    @staticmethod
    async def get_incoming_payments(config):
        return await SAPApiClient.get_all_data(
            "IncomingPayments",
            config
        )

    @staticmethod
    async def get_outgoing_payments(config):
        return await SAPApiClient.get_all_data(
            "VendorPayments",
            config
        )

    @staticmethod
    async def post_incoming_payment(config, payload):


        url = f"{config['base_url']}/IncomingPayments"

        cookies = await SAPApiClient.login(config)

        r = await SAPApiClient.client.post(
            url,
            json=payload,
            cookies=cookies
        )

        if r.status_code == 401:

            await delete_session(
                config["user_id"],
                config["schema_id"]
            )

            cookies = await SAPApiClient.login(config)

            r = await SAPApiClient.client.post(
                url,
                json=payload,
                cookies=cookies
            )

        if r.status_code >= 400:

            print("\n========== SAP ERROR ==========")
            print(r.text)
            print("==============================")

            raise Exception(r.text)

        return r.json()

    @staticmethod
    async def post_outgoing_payment(config, payload):


        # -------------------------
        # OUTGOING PAYMENT URL
        # -------------------------
        url = f"{config['base_url']}/VendorPayments"

        cookies = await SAPApiClient.login(config)

        # -------------------------
        # CALL SAP
        # -------------------------
        r = await SAPApiClient.client.post(
            url,
            json=payload,
            cookies=cookies
        )

        # -------------------------
        # SESSION EXPIRED → RETRY
        # -------------------------
        if r.status_code == 500:

            await delete_session(
                config["user_id"],
                config["schema_id"]
            )

            cookies = await SAPApiClient.login(config)

            r = await SAPApiClient.client.post(
                url,
                json=payload,
                cookies=cookies
            )

        # -------------------------
        # ERROR HANDLING
        # -------------------------
        if r.status_code >= 400:
            print("SAP ERROR RESPONSE:", r.text)

        if r.status_code >= 400:
            print("SAP ERROR FULL:", r.text)
            raise Exception(r.text)

        # -------------------------
        # RETURN RESPONSE
        # -------------------------
        return r.json()

    @staticmethod
    async def post_stock_transfer(config, payload):

        url = f"{config['base_url']}/StockTransfers"

        cookies = await SAPApiClient.login(config)

        r = await SAPApiClient.client.post(
            url,
            json=payload,
            cookies=cookies
        )

        # Session expired
        if r.status_code == 500:

            await delete_session(
                config["user_id"],
                config["schema_id"]
            )

            cookies = await SAPApiClient.login(config)

            r = await SAPApiClient.client.post(
                url,
                json=payload,
                cookies=cookies
            )

        if r.status_code >= 400:
            print("SAP STOCK TRANSFER ERROR:", r.text)
            raise Exception(r.text)

        return r.json()
    @staticmethod
    async def get_branch_series(
        config,
        object_code: str,
        date_f: str,
        date_t: str,
        branch_id: str
    ):

        query = (
            "SQLQueries('DADA_FetchBranchSeries')/List"
            f"?Object='{object_code}'"
            f"&DateF='{date_f}'"
            f"&DateT='{date_t}'"
            f"&BranchID='{branch_id}'"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )
    
    @staticmethod
    async def get_inventory_series(
        config,
        object_code: str,
        date_f: str,
        date_t: str
    ):

        query = (
            "SQLQueries('DADA_InventorySeries')/List"
            f"?Object='{object_code}'"
            f"&DateF='{date_f}'"
            f"&DateT='{date_t}'"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )

    @staticmethod
    async def get_ip_controled_glaccount(
        config,
        father_account_key: str
    ):

        query = (
            "ChartOfAccounts"
            "?$select=Code,Name,ActiveAccount"
            f"&$filter=FatherAccountKey eq '{father_account_key}'"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )
    
    @staticmethod
    async def get_cash_gl_accounts(config):

        query = (
            "ChartOfAccounts"
            "?$select=Code,Name,ActiveAccount"
            "&$filter=(Code eq 'A15410002' or Code eq 'A15410001')"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )
    
    @staticmethod
    async def get_control_accounts(config):

        query = (
            "ChartOfAccounts"
            "?$select=Code,Name,ActiveAccount"
            "&$filter=LockManualTransaction eq 'tYES' and Code ne 'A15320011'"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )
    @staticmethod
    async def post_inventory_transfer_request(
        config,
        payload
    ):

        url = f"{config['base_url']}/InventoryTransferRequests"

        cookies = await SAPApiClient.login(config)

        r = await SAPApiClient.client.post(
            url,
            json=payload,
            cookies=cookies
        )

        # =====================================
        # SESSION EXPIRED
        # =====================================

        if r.status_code == 401:

            await delete_session(
                config["user_id"],
                config["schema_id"]
            )

            cookies = await SAPApiClient.login(config)

            r = await SAPApiClient.client.post(
                url,
                json=payload,
                cookies=cookies
            )

        # =====================================
        # SAP ERROR
        # =====================================

        if r.status_code >= 500:

            print(
                "SAP INVENTORY TRANSFER REQUEST ERROR:",
                r.text
            )

            try:

                sap_error = r.json()

            except Exception:

                sap_error = {
                    "error": {
                        "message": r.text
                    }
                }

            raise Exception(r.text)

        # =====================================
        # SUCCESS
        # =====================================

        return r.json()

    @staticmethod
    async def get_single_data(
        endpoint: str,
        config: dict
    ):

        base_url = config["base_url"]

        url = f"{base_url}/{endpoint}"

        cookies = await SAPApiClient.login(config)

        r = await SAPApiClient.client.get(
            url,
            cookies=cookies
        )

        if r.status_code == 500:

            await delete_session(
                config["user_id"],
                config["schema_id"]
            )

            cookies = await SAPApiClient.login(config)

            r = await SAPApiClient.client.get(
                url,
                cookies=cookies
            )

        r.raise_for_status()

        return r.json()
    
    @staticmethod
    async def is_bin_enabled(
        config,
        whs_code: str
    ):

        query = (
            f"Warehouses('{whs_code}')"
            "?$select=EnableBinLocations"
        )

        return await SAPApiClient.get_single_data(
            query,
            config
        )

    @staticmethod
    async def get_bin_details(
        config,
        item_code: str,
        whs_code: str
    ):

        query = (
            "SQLQueries('BINDetails_GET_V0')/List"
            f"?Itemcode='{item_code}'"
            f"&WhsCode='{whs_code}'"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )
    # @staticmethod
    # async def get_outgoing_gl_accounts(config):

    #     query = (
    #         "ChartOfAccounts"
    #         "?$select=Code,Name,ActiveAccount,Balance"
    #         "&$filter=ActiveAccount eq 'tYES' "
    #         "and ValidFor eq 'tYES' "
    #         "and LockManualTransaction eq 'tNO'"
    #     )

    #     return await SAPApiClient.get_all_data(
    #         query,
    #         config
    #     )

    @staticmethod
    async def get_bins_all(config):

        query = (
            "BinLocations"
            "?$select="
            "AbsEntry,"
            "BinCode,"
            "Warehouse,"
            "Inactive"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )

    # =========================
    # MID INFO APIs
    # =========================
    @staticmethod
    async def get_merchant_ids_all(config):

        return await SAPApiClient.get_all_data(
            "SQLQueries('DADAQR_MIDInfo')/List",
            config
        )

   
    @staticmethod
    async def get_gl_master(config):

        query = (
            "ChartOfAccounts"
            "?$select="
            "Code,"
            "Name,"
            "ActiveAccount,"
            "Balance,"
            "LockManualTransaction"
            "&$filter=ActiveAccount eq 'tYES'"
            "&$count=true"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )

    @staticmethod
    async def get_incoming_payment_report(
        config,
        doc_key: int
    ):

        query = (
            f"sml.svc/IK_INCOMING_PAYMENTParameters"
            f"(DocKey={doc_key})"
            f"/IK_INCOMING_PAYMENT"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )
    
    @staticmethod
    async def get_outgoing_payment_report(
        config,
        doc_key: int
    ):

        query = (
            f"sml.svc/IK_OUTGOING_PAYMENTParameters"
            f"(DocKey={doc_key})"
            f"/IK_OUTGOING_PAYMENT"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )
    
    @staticmethod
    async def get_outgoing_payment_cheque_report(
        config,
        check_key: int
    ):

        query = (
            f"sml.svc/IK_OUTGOING_PAYMENT_CHEQUEParameters"
            f"(CheckKey={check_key})"
            f"/IK_OUTGOING_PAYMENT_CHEQUE"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )

    @staticmethod
    async def get_house_bank_accounts(config):

        query = (
            "HouseBankAccounts"
            "?$select="
            "BankCode,"
            "AccNo,"
            "Branch,"
            "GLAccount,"
            "Country"
        )

        return await SAPApiClient.get_all_data(
            query,
            config
        )