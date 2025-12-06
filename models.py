import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
from database import Base


class BusinessType(enum.Enum):
    DIS_KLINIGI = "dis-klinigi"
    RESTORAN = "restoran"
    E_TICARET = "e-ticaret"
    DIGER = "diger"


class VoiceType(enum.Enum):
    SES_1 = "ses-1"
    SES_2 = "ses-2"
    SES_3 = "ses-3"
    SES_4 = "ses-4"
    SES_5 = "ses-5"


class BehaviorType(enum.Enum):
    DAVRANIS_1 = "davranis-1"
    DAVRANIS_2 = "davranis-2"
    DAVRANIS_3 = "davranis-3"
    DAVRANIS_4 = "davranis-4"


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
    value = Column(String(50), nullable=False)


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    voice_type = Column(SAEnum(VoiceType), nullable=False, default=VoiceType.SES_1)
    behavior_type = Column(SAEnum(BehaviorType), nullable=False, default=BehaviorType.DAVRANIS_1)
    opening_message = Column(Text, nullable=False, default="Hoş geldiniz")
    closing_message = Column(Text, nullable=False, default="İyi günler")
    prompt = Column(Text, nullable=True, default="")