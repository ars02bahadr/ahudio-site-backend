from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from models import BusinessType

class MessageCreate(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    business_type: BusinessType
    message: Optional[str] = None
    phone_number: Optional[str] = None

class MessageRead(MessageCreate):
    id: int
    created_at: datetime

    # Pydantic V2 için yeni config yapısı
    model_config = ConfigDict(from_attributes=True)