from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import schemas
import models
from database import get_db
from decode import verify_token

router = APIRouter(prefix="/emails", tags=["E-posta Adresleri"])


@router.get("/", response_model=list[schemas.EmailAddressRead])
def get_all_emails(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Tüm email adreslerini getir - token gerekli"""
    return db.query(models.EmailAddress).all()


@router.get("/{email_id}", response_model=schemas.EmailAddressRead)
def get_email(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Belirli bir email adresini getir - token gerekli"""
    email = db.query(models.EmailAddress).filter(models.EmailAddress.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email adresi bulunamadı")
    return email


@router.post("/", response_model=schemas.EmailAddressRead, status_code=201)
def create_email(
    email_data: schemas.EmailAddressCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Yeni email adresi ekle - token gerekli"""
    email = models.EmailAddress(value=email_data.value)
    db.add(email)
    db.commit()
    db.refresh(email)
    return email


@router.put("/{email_id}", response_model=schemas.EmailAddressRead)
def update_email(
    email_id: int,
    email_data: schemas.EmailAddressCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Email adresini güncelle - token gerekli"""
    email = db.query(models.EmailAddress).filter(models.EmailAddress.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email adresi bulunamadı")
    
    email.value = email_data.value
    db.commit()
    db.refresh(email)
    return email


@router.delete("/{email_id}", status_code=204)
def delete_email(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Email adresini sil - token gerekli"""
    email = db.query(models.EmailAddress).filter(models.EmailAddress.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email adresi bulunamadı")
    
    db.delete(email)
    db.commit()
    return None

