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


class MessageList(BaseModel):
    items: list[MessageRead]
    page_number: int
    page_size: int
    total_count: Optional[int] = None
    total_pages: Optional[int] = None
    has_next_page: Optional[bool] = None
    has_previous_page: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

class LoginSuperAdmin(BaseModel):
    username: str
    access_token: str
    token_type: str = "bearer"
    model_config = ConfigDict(from_attributes=True)


