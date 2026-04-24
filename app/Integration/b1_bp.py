import logging

logger = logging.getLogger("sap-bp-service")


class SapBPService:

    # =========================
    # MAP BP TYPE
    # =========================
    @staticmethod
    def map_type(card_type: str):

        if card_type == "cCustomer":
            return "C"

        if card_type == "cSupplier":
            return "S"

        # ❌ Ignore Leads completely
        return None


    # =========================
    # SAVE BUSINESS PARTNER
    # =========================
    @staticmethod
    async def save_bp(conn, tenant_schema: str, data: dict):

        try:
            # =========================
            # BASIC FIELDS
            # =========================
            bp_id = data.get("CardCode")      # ✅ PRIMARY KEY
            bp_name = data.get("CardName") or bp_id

            if not bp_id:
                raise ValueError("bp_id required")

            if not bp_name:
                raise ValueError("bp_name required")

            # =========================
            # TYPE MAPPING
            # =========================
            bp_type = SapBPService.map_type(
                data.get("CardType")
            )

            # ❌ SKIP LEADS
            if not bp_type:
                return

            # =========================
            # BASIC DETAILS
            # =========================
            city = data.get("City")
            zipcode = data.get("ZipCode")
            country = data.get("Country")

            email = data.get("EmailAddress") or "noemail@dummy.com"

            phone = data.get("Phone1")
            mobile = data.get("Cellular")

            # =========================
            # ADDRESS + GST EXTRACTION
            # =========================
            street = None
            gst = None

            addresses = data.get("BPAddresses") or []

            if addresses:
                addr = addresses[0]

                # street
                street = addr.get("Street") or addr.get("Block")

                # GST (IMPORTANT FIX ✅)
                gst = addr.get("GSTIN")

            # =========================
            # PAN (fallback)
            # =========================
            pan = data.get("FederalTaxID")
            balance = data.get("CurrentAccountBalance", 0)

            # =========================
            # INSERT / UPDATE
            # =========================
            await conn.execute(
                f"""
                INSERT INTO "{tenant_schema}".ik_bp
                (
                    bp_id,
                    bp_name,
                    bp_type,
                    city,
                    zipcode,
                    street_name,
                    telephone_number,
                    country,
                    email,
                    mobile_number,
                    is_active,
                    gst_number,
                    pan_number,
                    balance
                )
                VALUES
                ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,TRUE,$11,$12,$13)

                ON CONFLICT (bp_id)
                DO UPDATE SET
                    bp_name = EXCLUDED.bp_name,
                    bp_type = EXCLUDED.bp_type,
                    city = EXCLUDED.city,
                    zipcode = EXCLUDED.zipcode,
                    street_name = EXCLUDED.street_name,
                    telephone_number = EXCLUDED.telephone_number,
                    country = EXCLUDED.country,
                    email = EXCLUDED.email,
                    mobile_number = EXCLUDED.mobile_number,
                    gst_number = EXCLUDED.gst_number,
                    pan_number = EXCLUDED.pan_number,
                    balance = EXCLUDED.balance,   -- ✅ IMPORTANT
                    is_active = TRUE
                """,
                bp_id,
                bp_name,
                bp_type,
                city,
                zipcode,
                street,
                phone,
                country,
                email,
                mobile,
                gst,
                pan,
                balance   # ✅ NEW PARAM
            )
            #logger.info(f"✅ BP saved: {bp_id}")

        except Exception as e:
            logger.exception(f"❌ Failed to save BP: {data.get('CardCode')}")
            raise