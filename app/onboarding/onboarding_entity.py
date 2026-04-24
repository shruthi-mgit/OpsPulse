from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional
class CreateOnboardingRequest(BaseModel):

    company_name: str
    company_phone_no: str
    company_street: str
    company_city: str
    company_state: str
    company_zipcode: str
    company_website: str
    industry_type: str
    headoffice_location: str
    company_gst: str
    registration_number: str

    user_name: str
    email: EmailStr
    user_phone_no: str

    email_id: EmailStr
    email_pwd: str
    smtp_server: str
    smtp_port: str

    base_url: str
    sap_username: str
    sap_password: str
    sap_db: str


class UpdateOnboardingRequest(BaseModel):

    company_phone_no: Optional[str] = None
    company_street: Optional[str] = None
    company_city: Optional[str] = None
    company_state: Optional[str] = None
    company_zipcode: Optional[str] = None
    company_website: Optional[str] = None
    company_name: Optional[str] = None 
    industry_type: Optional[str] = None
    headoffice_location: Optional[str] = None
    company_gst: Optional[str] = None
    registration_number: Optional[str] = None
    user_name: Optional[str] = None
    email: Optional[EmailStr] = None
    user_phone_no: Optional[str] = None
    email_id: Optional[str] = None
    email_pwd: Optional[str] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[str] = None
    base_url: Optional[str] = None
    sap_username: Optional[str] = None
    sap_password: Optional[str] = None
    sap_db: Optional[str] = None

    is_active: Optional[bool] = None