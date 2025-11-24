from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from models import BusinessType


class MessageCreate(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    business_type: BusinessType
    message: Optional[str] = None


class MessageRead(MessageCreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True