import httpx
from datetime import datetime
import time

TIMEOUT = httpx.Timeout(30.0)
SESSION_TIMEOUT = 1500


class SAPApiClient:

    session = None

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

        # ✅ reuse session if not expired
        if SAPApiClient.session:
            if time.time() - SAPApiClient.session["timestamp"] < SESSION_TIMEOUT:
                return SAPApiClient.session["cookies"]

        url = f"{config['base_url']}/Login"

        payload = {
            "CompanyDB": config["sap_db"],
            "UserName": config["sap_username"],
            "Password": config["sap_password"],
        }

        r = await SAPApiClient.client.post(url, json=payload)
        r.raise_for_status()

        SAPApiClient.session = {
            "cookies": r.cookies,
            "timestamp": time.time()
        }

        print(f"✅ SAP login success for DB: {config['sap_db']}")

        return SAPApiClient.session["cookies"]

    # =========================
    # GENERIC PAGINATION
    # =========================
    @staticmethod
    async def get_all_data(endpoint: str, config: dict):

        if (
            not SAPApiClient.session
            or time.time() - SAPApiClient.session["timestamp"] > SESSION_TIMEOUT
        ):
            await SAPApiClient.login(config)

        base_url = config["base_url"]

        all_data = []
        next_endpoint = endpoint

        while next_endpoint:

            url = f"{base_url}/{next_endpoint}"

            r = await SAPApiClient.client.get(
                url,
                cookies=SAPApiClient.session["cookies"]
            )

            if r.status_code == 401:
                SAPApiClient.session = None  # reset expired session
                await SAPApiClient.login(config)
                continue

            r.raise_for_status()

            data = r.json()
            all_data.extend(data.get("value", []))

            next_link = data.get("@odata.nextLink")

            if next_link:
                next_endpoint = next_link.replace(f"{base_url}/", "")
            else:
                next_endpoint = None

        return all_data

    # =========================
    # MASTER APIs
    # =========================
    @staticmethod
    async def get_branches_all(config):
        return await SAPApiClient.get_all_data(
            "Branches?$select=Code,Name", config
        )

    @staticmethod
    async def get_banks_all(config):
        return await SAPApiClient.get_all_data(
            "Banks?$select=BankCode,BankName", config
        )

    @staticmethod
    async def get_gl_all(config):
        return await SAPApiClient.get_all_data(
            "ChartOfAccounts?$select=Code,Name,ActiveAccount", config
        )

    @staticmethod
    async def get_bp_all(config):
        return await SAPApiClient.get_all_data(
            "BusinessPartners?"
            "$select=CardCode,CardName,CardType,ZipCode,Country,EmailAddress,City,BPAddresses"
            "&$filter=CardType eq 'cCustomer' or CardType eq 'cSupplier'",
            config
        )

    @staticmethod
    async def get_bp_customers(config):
        return await SAPApiClient.get_all_data(
            "BusinessPartners?"
            "$select=CardCode,CardName,CardType,ZipCode,Country,EmailAddress,City,BPAddresses"
            "&$filter=CardType eq 'cCustomer'",
            config
        )

    @staticmethod
    async def get_bp_suppliers(config):
        return await SAPApiClient.get_all_data(
            "BusinessPartners?"
            "$select=CardCode,CardName,CardType"
            "&$filter=CardType eq 'cSupplier'",
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
    async def get_customer_due_invoices(customer_code: str, config: dict):

        if (
            not SAPApiClient.session
            or time.time() - SAPApiClient.session["timestamp"] > SESSION_TIMEOUT
        ):
            await SAPApiClient.login(config)

        base_url = config["base_url"]
        endpoint = f"sml.svc/IK_CUSTOMER_BALANCEDUEParameters(P_CUSTOMERCODE='{customer_code}')/IK_CUSTOMER_BALANCEDUE"

        all_data = []

        while endpoint:

            url = f"{base_url}/{endpoint}"

            r = await SAPApiClient.client.get(
                url,
                cookies=SAPApiClient.session["cookies"]
            )

            if r.status_code == 401:
                SAPApiClient.session = None  # reset expired session
                await SAPApiClient.login(config)
                continue

            r.raise_for_status()

            data = r.json()
            all_data.extend(data.get("value", []))

            next_link = data.get("@odata.nextLink")

            if next_link:
                if not next_link.startswith("sml.svc"):
                    endpoint = "sml.svc/" + next_link
                else:
                    endpoint = next_link
            else:
                endpoint = None

        return all_data

    # =========================
    # VENDOR APIs
    # =========================
    @staticmethod
    async def get_vendor_due_invoices(vendor_code: str, config: dict):

        if (
            not SAPApiClient.session
            or time.time() - SAPApiClient.session["timestamp"] > SESSION_TIMEOUT
        ):
            await SAPApiClient.login(config)

        base_url = config["base_url"]
        endpoint = f"sml.svc/IK_VENDOR_BALANCEDUEParameters(P_VENDORCODE='{vendor_code}')/IK_VENDOR_BALANCEDUE"

        all_data = []

        while endpoint:

            url = f"{base_url}/{endpoint}"

            r = await SAPApiClient.client.get(
                url,
                cookies=SAPApiClient.session["cookies"]
            )

            if r.status_code == 401:
                SAPApiClient.session = None  # reset expired session
                await SAPApiClient.login(config)
                continue

            r.raise_for_status()

            data = r.json()
            all_data.extend(data.get("value", []))

            next_link = data.get("@odata.nextLink")

            if next_link:
                if not next_link.startswith("sml.svc"):
                    endpoint = "sml.svc/" + next_link
                else:
                    endpoint = next_link
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

        if (
            not SAPApiClient.session
            or time.time() - SAPApiClient.session["timestamp"] > SESSION_TIMEOUT
        ):
            await SAPApiClient.login(config)

        url = f"{config['base_url']}/IncomingPayments"

        r = await SAPApiClient.client.post(
            url,
            json=payload,
            cookies=SAPApiClient.session["cookies"]
        )

        if r.status_code == 401:
            SAPApiClient.session = None
            await SAPApiClient.login(config)

            r = await SAPApiClient.client.post(
                url,
                json=payload,
                cookies=SAPApiClient.session["cookies"]
            )

        r.raise_for_status()

        return r.json()

    @staticmethod
    async def post_outgoing_payment(config, payload):

        # -------------------------
        # SESSION CHECK
        # -------------------------
        if (
            not SAPApiClient.session
            or time.time() - SAPApiClient.session["timestamp"] > SESSION_TIMEOUT
        ):
            await SAPApiClient.login(config)

        # -------------------------
        # OUTGOING PAYMENT URL
        # -------------------------
        url = f"{config['base_url']}/VendorPayments"

        # -------------------------
        # CALL SAP
        # -------------------------
        r = await SAPApiClient.client.post(
            url,
            json=payload,
            cookies=SAPApiClient.session["cookies"]
        )

        # -------------------------
        # SESSION EXPIRED → RETRY
        # -------------------------
        if r.status_code == 401:
            SAPApiClient.session = None
            await SAPApiClient.login(config)

            r = await SAPApiClient.client.post(
                url,
                json=payload,
                cookies=SAPApiClient.session["cookies"]
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