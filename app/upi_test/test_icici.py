import json
import base64
import requests

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
from datetime import datetime
import qrcode
# -------------------------
# Encrypt Request
# -------------------------
merchant_tran_id = datetime.now().strftime("%d%H%M%S%f")[:12]


payload = {
    "amount": "1.00",
    "merchantId": "612960",
    "terminalId": "5411",
    "merchantTranId": merchant_tran_id,
    "billNumber": "1001"
}

payload_json = json.dumps(payload)

with open("test.crt", "rb") as f:
    cert = x509.load_pem_x509_certificate(f.read())

public_key = cert.public_key()

encrypted = public_key.encrypt(
    payload_json.encode(),
    padding.PKCS1v15()
)

encrypted_text = base64.b64encode(encrypted).decode()

# -------------------------
# API Call
# -------------------------

url = "https://apibankingonesandbox.icici.bank.in/api/MerchantAPI/UPI/v0/QR3/612960"

headers = {
    "apikey": "VogOiGM8gFhZrua0mrzh8qCZd2mjyGQ6",
    "Content-Type": "text/plain"
}

response = requests.post(
    url,
    headers=headers,
    data=encrypted_text,
    timeout=60
)

print("Status:", response.status_code)

# -------------------------
# Decrypt Response
# -------------------------

with open("dadamotores.pfx", "rb") as f:
    pfx_data = f.read()

private_key, certificate, additional = pkcs12.load_key_and_certificates(
    pfx_data,
    b"123456"
)

cipher_bytes = base64.b64decode(response.text)

key_size = private_key.key_size // 8

decrypted_data = b""

for i in range(0, len(cipher_bytes), key_size):
    block = cipher_bytes[i:i + key_size]

    decrypted_block = private_key.decrypt(
        block,
        padding.PKCS1v15()
    )

    decrypted_data += decrypted_block

decrypted_response = json.loads(
    decrypted_data.decode("utf-8")
)

ref_id = decrypted_response["refId"]
amount = decrypted_response["Amount"]



response_data = {
    "merchant_tran_id": merchant_tran_id,
    "ref_id": ref_id,
    "upi_link": upi_link,
    "upi_status": "PENDING"
}

print(json.dumps(response_data, indent=4))