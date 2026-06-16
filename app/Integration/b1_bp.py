
import logging

logger = logging.getLogger("sap-bp-service")


class SapBPService:

    # =========================
    # MAP BP TYPE
    # =========================
    @staticmethod
    def map_type(card_type: str):

        mapping = {
            "cCustomer": "C",
            "cSupplier": "S"
        }

        return mapping.get(card_type)

    # =========================
    # PREPARE BP ROW
    # =========================
    @staticmethod
    def prepare_bp(data: dict):

        bp_id = data.get("CardCode")

        if not bp_id:
            return None

        bp_type = SapBPService.map_type(
            data.get("CardType")
        )

        # Skip Leads
        if not bp_type:
            return None

        addr = next(
            iter(data.get("BPAddresses") or []),
            {}
        )

        return (
            bp_id,
            data.get("CardName") or bp_id,
            bp_type,
            data.get("City"),
            data.get("ZipCode"),
            addr.get("Street") or addr.get("Block"),
            data.get("Phone1"),
            data.get("Country"),
            (
                data.get("EmailAddress")
                or ""
            ).strip() or f"{bp_id.lower()}@dummy.com",
            data.get("Cellular"),
            addr.get("GSTIN"),
            data.get("FederalTaxID"),
            float(data.get("CurrentAccountBalance") or 0),
            data.get("DebitorAccount")
        )

    # =========================
    # BULK SAVE BP
    # =========================
    @staticmethod
    async def save_bulk_bp(
        conn,
        tenant_schema: str,
        bp_data: list,
        user_id: str,
        schema_id: str
    ):

        try:

            rows = []

            # =========================
            # PREPARE ROWS
            # =========================
            for data in bp_data:

                row = SapBPService.prepare_bp(data)

                if row:
                    rows.append(
                        (
                            *row,
                            user_id,
                            user_id,
                            schema_id
                        )
                    )

            if not rows:

                logger.info(
                    "⚠️ No valid BP rows found"
                )

                return

            # =========================
            # UPSERT QUERY
            # =========================
            query = f"""
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
                    balance,
                    debitor_account,
                    created_by,
                    updated_by,
                    schema_id
                )

                VALUES
                (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
                    TRUE,
                    $11,$12,
                    $13,
                    $14,
                    $15,$16,$17
                )

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
                    balance = EXCLUDED.balance,
                    debitor_account = EXCLUDED.debitor_account,
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by,
                    is_active = TRUE
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
                #     f"✅ BP Chunk Synced: "
                #     f"{min(i + chunk_size, total)} / {total}"
                # )

            # logger.info(
            #     f"✅ Bulk BP Sync Completed: "
            #     f"{total} rows"
            # )

        except Exception:

            logger.exception(
                "❌ Bulk BP Sync Failed"
            )

            raise

