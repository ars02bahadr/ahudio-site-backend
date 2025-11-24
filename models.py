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