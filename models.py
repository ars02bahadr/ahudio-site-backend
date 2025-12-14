import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
from database import Base


class BusinessType(enum.Enum):
    DIS_KLINIGI = "dis-klinigi"
    RESTORAN = "restoran"
    E_TICARET = "e-ticaret"
    DIGER = "diger"




class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, index=True)
    phone_number = Column(String(50), nullable=True)
    company = Column(String(200), nullable=True)
    business_type = Column(SAEnum(BusinessType), nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())






class SuperAdmin(Base):
    __tablename__ = "super_admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)


class About(Base):
    __tablename__ = "about"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False, default="Ahudio hakkında açıklama")
    vision = Column(Text, nullable=False, default="Vizyonumuz")
    mission = Column(Text, nullable=False, default="Misyonumuz")


class EmailAddress(Base):
    __tablename__ = "email_addresses"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(String(200), nullable=False)


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id = Column(Integer, primary_key=True, index=True)
    vapi_id = Column(String(200), unique=True, nullable=False, index=True)  # VAPI'den gelen id
    org_id = Column(String(200), nullable=True)
    assistant_id = Column(String(200), nullable=True)  # VAPI assistant ID
    value = Column(String(50), nullable=False)  # Telefon numarası
    name = Column(String(200), nullable=True)
    credential_id = Column(String(200), nullable=True)
    provider = Column(String(50), nullable=True)
    number_e164_check_enabled = Column(String(10), nullable=True, default="false")
    status = Column(String(50), nullable=True)
    provider_resource_id = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at_local = Column(DateTime(timezone=True), server_default=func.now())
    updated_at_local = Column(DateTime(timezone=True), onupdate=func.now())


class Voice(Base):
    __tablename__ = "voices"

    id = Column(Integer, primary_key=True, index=True)
    assistant_id = Column(Integer, nullable=False, index=True)
    model = Column(String(100), nullable=True)
    voice_id = Column(String(200), nullable=True)
    provider = Column(String(50), nullable=True)
    stability = Column(String(50), nullable=True)
    similarity_boost = Column(String(50), nullable=True)


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(Integer, primary_key=True, index=True)
    vapi_id = Column(String(200), unique=True, nullable=False, index=True)  # VAPI'den gelen id
    org_id = Column(String(200), nullable=True)
    name = Column(String(200), nullable=False)
    voice_type = Column(String(50), nullable=True)
    behavior_type = Column(String(50), nullable=True)
    first_message = Column(Text, nullable=True)
    voicemail_message = Column(Text, nullable=True)
    end_call_message = Column(Text, nullable=True)
    model_data = Column(Text, nullable=True)  # JSON olarak saklanacak
    transcriber_data = Column(Text, nullable=True)  # JSON olarak saklanacak
    silence_timeout_seconds = Column(Integer, nullable=True)
    client_messages = Column(Text, nullable=True)  # JSON array olarak saklanacak
    server_messages = Column(Text, nullable=True)  # JSON array olarak saklanacak
    end_call_phrases = Column(Text, nullable=True)  # JSON array olarak saklanacak
    hipaa_enabled = Column(String(10), nullable=True, default="false")
    background_denoising_enabled = Column(String(10), nullable=True, default="false")
    start_speaking_plan = Column(Text, nullable=True)  # JSON olarak saklanacak
    is_server_url_secret_set = Column(String(10), nullable=True, default="false")
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at_local = Column(DateTime(timezone=True), server_default=func.now())
    updated_at_local = Column(DateTime(timezone=True), onupdate=func.now())