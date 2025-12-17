from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import schemas
import models
from database import get_db
from decode import verify_token
from services.vapi_service import VAPIService
from services.phone_service import sync_phone_from_vapi

router = APIRouter(prefix="/phones", tags=["Telefon Numaraları"])


@router.get("/", response_model=list[schemas.PhoneNumberRead])
async def get_all_phones(db: Session = Depends(get_db)):
    """Tüm telefon numaralarını getir - önce VAPI'den çek, sonra veritabanına kaydet"""
    vapi_service = VAPIService()
    
    try:
        vapi_phones = await vapi_service.get_phone_numbers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'den veri çekilemedi: {str(e)}")
    
    # VAPI'den gelen tüm telefon numaralarını veritabanına kaydet
    for vapi_phone in vapi_phones:
        await sync_phone_from_vapi(vapi_phone, db)
    
    # Veritabanından tüm telefon numaralarını getir
    return db.query(models.PhoneNumber).all()


@router.get("/{phone_id}", response_model=schemas.PhoneNumberRead)
async def get_phone(phone_id: int, db: Session = Depends(get_db)):
    """Belirli bir telefon numarasını getir - önce VAPI'den çek, sonra veritabanına kaydet"""
    phone = db.query(models.PhoneNumber).filter(models.PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Telefon numarası bulunamadı")
    
    vapi_service = VAPIService()
    
    try:
        # VAPI'den bu telefon numarasını çek
        vapi_phone = await vapi_service.get_phone_number(phone.vapi_id)
        # Veritabanını güncelle
        phone = await sync_phone_from_vapi(vapi_phone, db)
    except Exception as e:
        # VAPI'den çekilemezse veritabanından getir
        pass
    
    return phone


@router.post("/", response_model=schemas.PhoneNumberRead, status_code=201)
async def create_phone(
    phone_data: schemas.PhoneNumberCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """VAPI'de yeni telefon numarası oluştur - token gerekli"""
    vapi_service = VAPIService()
    
    # VAPI'ye gönderilecek veri
    # VAPI API'si sadece provider ve credentialId bekliyor (VAPI API dokümantasyonuna göre)
    # number, name, assistantId, value gibi alanlar kabul edilmiyor
    vapi_data = {
        "provider": phone_data.provider
    }
    
    # credentialId varsa ekle
    if phone_data.credential_id:
        vapi_data["credentialId"] = phone_data.credential_id
    
    try:
        vapi_response = await vapi_service.create_phone_number(vapi_data)
    except Exception as e:
        # Hata mesajını daha detaylı göster
        error_detail = str(e)
        raise HTTPException(status_code=500, detail=f"VAPI'de telefon numarası oluşturulamadı: {error_detail}")
    
    # Veritabanına kaydet
    # VAPI'den dönen tüm bilgileri veritabanına kaydet
    new_phone = models.PhoneNumber(
        vapi_id=vapi_response.get("id"),
        org_id=vapi_response.get("orgId"),
        assistant_id=vapi_response.get("assistantId"),
        value=vapi_response.get("number") or "",
        name=vapi_response.get("name"),
        credential_id=vapi_response.get("credentialId"),
        provider=vapi_response.get("provider"),
        number_e164_check_enabled=str(vapi_response.get("numberE164CheckEnabled", False)).lower(),
        status=vapi_response.get("status"),
        provider_resource_id=vapi_response.get("providerResourceId"),
        created_at=vapi_service.parse_datetime(vapi_response.get("createdAt")),
        updated_at=vapi_service.parse_datetime(vapi_response.get("updatedAt"))
    )
    db.add(new_phone)
    db.commit()
    db.refresh(new_phone)
    return new_phone


@router.patch("/{phone_id}", response_model=schemas.PhoneNumberRead)
async def update_phone(
    phone_id: int,
    phone_data: schemas.PhoneNumberUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """VAPI'de telefon numarasını güncelle - token gerekli"""
    phone = db.query(models.PhoneNumber).filter(models.PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Telefon numarası bulunamadı")
    
    vapi_service = VAPIService()
    
    # VAPI'ye gönderilecek veri
    # VAPI API'si sadece provider ve credentialId güncellemesini kabul eder
    vapi_data = {}
    if phone_data.provider is not None:
        vapi_data["provider"] = phone_data.provider
    if phone_data.credential_id is not None:
        vapi_data["credentialId"] = phone_data.credential_id
    
    # Boş dict kontrolü
    if not vapi_data:
        raise HTTPException(status_code=400, detail="Güncellenecek alan belirtilmedi. Sadece provider ve credential_id güncellenebilir.")
    
    try:
        vapi_response = await vapi_service.update_phone_number(phone.vapi_id, vapi_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'de telefon numarası güncellenemedi: {str(e)}")
    
    # Veritabanını güncelle
    # VAPI'den dönen tüm bilgileri veritabanına kaydet
    if phone_data.provider is not None:
        phone.provider = vapi_response.get("provider", phone_data.provider)
    if phone_data.credential_id is not None:
        phone.credential_id = vapi_response.get("credentialId", phone_data.credential_id)
    
    # VAPI'den dönen diğer alanları da güncelle
    phone.value = vapi_response.get("number", phone.value)
    phone.name = vapi_response.get("name", phone.name)
    phone.assistant_id = vapi_response.get("assistantId", phone.assistant_id)
    
    phone.updated_at = vapi_service.parse_datetime(vapi_response.get("updatedAt"))
    
    db.commit()
    db.refresh(phone)
    return phone


@router.delete("/{phone_id}", status_code=204)
async def delete_phone(
    phone_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """VAPI'den telefon numarasını sil - token gerekli"""
    phone = db.query(models.PhoneNumber).filter(models.PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Telefon numarası bulunamadı")
    
    vapi_service = VAPIService()
    
    try:
        await vapi_service.delete_phone_number(phone.vapi_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'den telefon numarası silinemedi: {str(e)}")
    
    # Telefon numarasını sil
    db.delete(phone)
    db.commit()
    return None

