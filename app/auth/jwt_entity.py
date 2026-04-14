"""
JWT Entity Model
Pydantic models for JWT database operations
"""
from pydantic import BaseModel
from typing import Optional


class JWTResponse(BaseModel):
    """JWT Response Model for database storage"""
    jwt_id: str
    jwt_token: str
    user_id: str
    role: str

    class Config:
        from_attributes = True

class JWTUpdate(BaseModel):
    """Model for updating JWT record"""
    jwt_token: Optional[str] = None
    role: Optional[str] = None