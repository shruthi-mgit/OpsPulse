import json
import base64
import requests

from pathlib import Path
from datetime import datetime

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
from app.database.connection import (
    ICICI_BASE_URL,
    ICICI_PFX_PASSWORD,
    ICICI_CERT_FILE,
    ICICI_PFX_FILE
)



class UPIService:

   
    @staticmethod
    async def generate_upi(
        conn,
        tenant_schema,
        payment_id,
        merchant_id,
        merchant_tran_id,
        amount,
        terminal_id,
        bill_number
    ):

        merchant_cfg = await conn.fetchrow(
            f"""
            SELECT
                merchant_id,
                qr_string_vpa,
                bank_api_key
            FROM "{tenant_schema}".ik_glaccount
            WHERE merchant_id = $1
            """,
            merchant_id
        )

        if not merchant_cfg:
            return {
                "status": "error",
                "message": f"Merchant configuration not found for {merchant_id}"
            }

        api_key = merchant_cfg["bank_api_key"]
        vpa = merchant_cfg["qr_string_vpa"]

        print("merchant_id =", merchant_id)
        print("vpa =", vpa)
        print("api_key exists =", bool(api_key))
        # # merchant_id = "612960"
        # api_key = "VogOiGM8gFhZrua0mrzh8qCZd2mjyGQ6"
        # vpa = "dadauat@icici"

        # merchant_tran_id = (
        #     f"{payment_id.replace('_', '')}"
        #     f"{datetime.now().strftime('%d%H%M%S%f')}"
        # )

        payload = {
            "amount": f"{float(amount):.2f}",
            "merchantId": merchant_id,
            "terminalId": terminal_id,
            "merchantTranId": merchant_tran_id,
            "billNumber": bill_number
        }

        payload_json = json.dumps(payload)

        BASE_DIR = Path(__file__).resolve().parent.parent

        crt_path = (
            BASE_DIR /
            "upi_test" /
            ICICI_CERT_FILE
        )

        pfx_path = (
            BASE_DIR /
            "upi_test" /
            ICICI_PFX_FILE
        )
        # ---------------------------------
        # Encrypt
        # ---------------------------------
        
        print("CRT PATH =", crt_path)
        print("PFX PATH =", pfx_path)

        print("CRT EXISTS =", crt_path.exists())
        print("PFX EXISTS =", pfx_path.exists())

        print("ICICI_BASE_URL =", ICICI_BASE_URL)
        with open(crt_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(
                f.read()
            )
        
        

        public_key = cert.public_key()

        encrypted = public_key.encrypt(
            payload_json.encode(),
            padding.PKCS1v15()
        )

        encrypted_text = (
            base64.b64encode(encrypted)
            .decode()
        )

        # ---------------------------------
        # API Call
        # ---------------------------------

        url = (
            f"{ICICI_BASE_URL}"
            f"/api/MerchantAPI/UPI/v0/QR3/{merchant_id}"
        )
                
        headers = {
            "apikey": api_key,
            "Content-Type": "text/plain"
        }
        try:

            response = requests.post(
                url,
                headers=headers,
                data=encrypted_text,
                timeout=60
            )

        except Exception as e:

            return {
                "status": "error",
                "message": f"ICICI Connection Error: {str(e)}"
            }

        print("STATUS =", response.status_code)
        print("RESPONSE TEXT =", response.text)

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"ICICI API Error {response.status_code}",
                "response": response.text
            }
        # ---------------------------------
        # Decrypt
        # ---------------------------------

        with open(pfx_path, "rb") as f:
            pfx_data = f.read()

        private_key, certificate, additional = (
            pkcs12.load_key_and_certificates(
                pfx_data,
                ICICI_PFX_PASSWORD.encode()
            )
        )

        cipher_bytes = base64.b64decode(
            response.text
        )

        key_size = private_key.key_size // 8

        decrypted_data = b""

        for i in range(
            0,
            len(cipher_bytes),
            key_size
        ):

            block = cipher_bytes[
                i:i + key_size
            ]

            decrypted_block = (
                private_key.decrypt(
                    block,
                    padding.PKCS1v15()
                )
            )

            decrypted_data += decrypted_block

        decrypted_response = json.loads(
            decrypted_data.decode("utf-8")
        )

        if decrypted_response.get("success") != "true":
            return {
                "status": "error",
                "message": decrypted_response.get("message"),
                "response": decrypted_response
            }

        ref_id = decrypted_response["refId"]

        upi_link = (
            f"upi://pay"
            f"?pa={vpa}"
            f"&pn=Dadamotors"
            f"&tr={ref_id}"
            f"&am={amount}"
            f"&cu=INR"
            f"&mc=5411"
        )

        print("url =", url)
        print("headers =", headers)
        

        payment_id = merchant_tran_id.split("_")[0]

        result = await conn.execute(
            f'''
            UPDATE "{tenant_schema}".ik_inc_payment_paymeans_line
            SET
                upi_qr_ref = $1,
                upi_status = $2
            WHERE payment_id = $3
            ''',
            ref_id,
            "PENDING",
            payment_id
        )

        print("UPDATE RESULT =", result)


        return {
            "status": "success",
            "merchant_tran_id":
                merchant_tran_id,
            "ref_id": ref_id,
            "upi_status": "PENDING"
        }

#  cd D:\Project\OpsPulseB1\app\upi_test  
#>> python test_icici.py        