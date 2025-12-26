"""
Public Router - Hassas bilgiler gizlenmiş public endpoint'ler
About, Email, Phone bilgileri token olmadan erişilebilir ama maskelenmiş
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import models
from database import get_db

router = APIRouter(prefix="/public", tags=["Public"])


# ==================== SCHEMAS ====================

class PublicAboutRead(BaseModel):
    """Public about bilgisi - sadece description, vision, mission"""
    description: str
    vision: str
    mission: str


class PublicContactInfo(BaseModel):
    """Public iletişim bilgisi - maskelenmiş"""
    has_email: bool  # Email var mı?
    has_phone: bool  # Telefon var mı?
    contact_available: bool  # İletişim mevcut mu?


# ==================== ENDPOINTS ====================

@router.get("/about", response_model=PublicAboutRead)
def get_public_about(db: Session = Depends(get_db)):
    """
    Public about bilgisi
    Sadece description, vision ve mission döner
    Email, telefon gibi hassas bilgiler dahil DEĞİLDİR
    """
    about = db.query(models.About).first()
    if not about:
        # Default değerler
        return PublicAboutRead(
            description="Ahudio - AI destekli sesli asistan çözümleri",
            vision="İşletmelerin müşteri iletişimini yapay zeka ile dönüştürmek",
            mission="Her işletmeye erişilebilir, akıllı sesli asistan teknolojisi sunmak"
        )
    
    return PublicAboutRead(
        description=about.description,
        vision=about.vision,
        mission=about.mission
    )


@router.get("/contact-status", response_model=PublicContactInfo)
def get_contact_status(db: Session = Depends(get_db)):
    """
    İletişim durumu
    Hassas bilgiler (email, telefon numaraları) döndürülmez
    Sadece iletişim mevcut mu kontrolü yapılır
    """
    has_email = db.query(models.EmailAddress).first() is not None
    has_phone = db.query(models.PhoneNumber).first() is not None
    
    return PublicContactInfo(
        has_email=has_email,
        has_phone=has_phone,
        contact_available=has_email or has_phone
    )
