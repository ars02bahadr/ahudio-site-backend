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


# About Schemas
class AboutBase(BaseModel):
    description: str
    vision: str
    mission: str

class AboutUpdate(AboutBase):
    pass

class AboutRead(AboutBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Email Address Schemas
class EmailAddressCreate(BaseModel):
    value: str

class EmailAddressRead(EmailAddressCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Phone Number Schemas
class PhoneNumberCreate(BaseModel):
    value: str  # Telefon numarası
    name: Optional[str] = None  # İsim (opsiyonel)

class PhoneNumberUpdate(BaseModel):
    value: Optional[str] = None
    name: Optional[str] = None

class PhoneNumberRead(BaseModel):
    id: int
    vapi_id: str
    value: str
    name: Optional[str] = None
    assistant_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_at_local: datetime
    updated_at_local: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# Voice Schemas
class VoiceBase(BaseModel):
    model: Optional[str] = None
    voice_id: Optional[str] = None
    provider: Optional[str] = None
    stability: Optional[float] = None
    similarity_boost: Optional[float] = None

class VoiceCreate(VoiceBase):
    assistant_id: int

class VoiceRead(VoiceBase):
    id: int
    assistant_id: int
    model_config = ConfigDict(from_attributes=True)


# Model Schema (VAPI model bilgisi için)
class ModelRead(BaseModel):
    model: Optional[str] = None
    provider: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    messages: Optional[list] = None  # System message ve diğer mesajlar
    tool_ids: Optional[list] = None


# Assistant Schemas
class AssistantBase(BaseModel):
    name: str
    first_message: Optional[str] = None
    voicemail_message: Optional[str] = None
    end_call_message: Optional[str] = None

class AssistantCreate(AssistantBase):
    voice_type: Optional[str] = None  # voice_id değeri - Backend VAPI'den otomatik doldurur
    behavior_type: Optional[str] = None  # model değeri (örn: "gpt-4o-mini") - Backend VAPI'den otomatik doldurur
    system_prompt: Optional[str] = None  # System message content - model.messages[0].content

class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    first_message: Optional[str] = None
    voicemail_message: Optional[str] = None
    end_call_message: Optional[str] = None
    voice_type: Optional[str] = None
    behavior_type: Optional[str] = None
    system_prompt: Optional[str] = None  # System message content - model.messages[0].content

class AssistantRead(AssistantBase):
    id: int
    vapi_id: str
    org_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_at_local: datetime
    updated_at_local: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class AssistantWithVoice(AssistantRead):
    voice: Optional[VoiceRead] = None
    model: Optional[ModelRead] = None
    model_config = ConfigDict(from_attributes=True)


# Dashboard Statistics Schemas
class BasicStats(BaseModel):
    """Temel istatistikler"""
    total_calls: int
    successful_calls: int
    failed_calls: int
    active_calls: int
    total_cost: float  # $ formatında

class DetailedStats(BaseModel):
    """Detaylı metrikler"""
    average_call_duration: Optional[str] = None  # "MM:SS" formatında
    today_calls: int
    week_calls: int
    success_rate: float  # % formatında

class CallTypeStats(BaseModel):
    """Çağrı türleri istatistikleri"""
    web_call: int
    outbound_phone: int
    inbound_phone: int

class DashboardStats(BaseModel):
    """Dashboard istatistikleri"""
    basic_stats: BasicStats
    detailed_stats: DetailedStats
    call_type_stats: CallTypeStats


