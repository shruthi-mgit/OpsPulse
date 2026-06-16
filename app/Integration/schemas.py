from pydantic import BaseModel


class GenerateUPIRequest(BaseModel):
    amount: float
    merchant_id: str
    terminalId: str
    merchantTranId: str
    billNumber: str