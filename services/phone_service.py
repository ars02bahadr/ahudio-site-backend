import json
from sqlalchemy.orm import Session
from datetime import datetime
import models
from services.vapi_service import VAPIService


async def sync_phone_from_vapi(vapi_phone: dict, db: Session) -> models.PhoneNumber:
    """VAPI'den gelen telefon numarası verisini veritabanına kaydet veya güncelle"""
    vapi_service = VAPIService()
    
    # Mevcut telefon numarasını kontrol et
    existing = db.query(models.PhoneNumber).filter(
        models.PhoneNumber.vapi_id == vapi_phone.get("id")
    ).first()
    
    if existing:
        # Güncelle
        existing.org_id = vapi_phone.get("orgId")
        existing.assistant_id = vapi_phone.get("assistantId")
        existing.value = vapi_phone.get("number", "")
        existing.name = vapi_phone.get("name")
        existing.credential_id = vapi_phone.get("credentialId")
        existing.provider = vapi_phone.get("provider")
        existing.number_e164_check_enabled = str(vapi_phone.get("numberE164CheckEnabled", False)).lower()
        existing.status = vapi_phone.get("status")
        existing.provider_resource_id = vapi_phone.get("providerResourceId")
        existing.created_at = vapi_service.parse_datetime(vapi_phone.get("createdAt"))
        existing.updated_at = vapi_service.parse_datetime(vapi_phone.get("updatedAt"))
        
        phone = existing
    else:
        # Yeni oluştur
        new_phone = models.PhoneNumber(
            vapi_id=vapi_phone.get("id"),
            org_id=vapi_phone.get("orgId"),
            assistant_id=vapi_phone.get("assistantId"),
            value=vapi_phone.get("number", ""),
            name=vapi_phone.get("name"),
            credential_id=vapi_phone.get("credentialId"),
            provider=vapi_phone.get("provider"),
            number_e164_check_enabled=str(vapi_phone.get("numberE164CheckEnabled", False)).lower(),
            status=vapi_phone.get("status"),
            provider_resource_id=vapi_phone.get("providerResourceId"),
            created_at=vapi_service.parse_datetime(vapi_phone.get("createdAt")),
            updated_at=vapi_service.parse_datetime(vapi_phone.get("updatedAt"))
        )
        db.add(new_phone)
        db.flush()
        phone = new_phone
    
    db.commit()
    db.refresh(phone)
    return phone

