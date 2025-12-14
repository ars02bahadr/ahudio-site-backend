from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import schemas
import models
from database import get_db
from decode import ACCESS_TOKEN_EXPIRE_MINUTES, verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["Kimlik Doğrulama"])


@router.post("/login/", response_model=schemas.LoginSuperAdmin)
def login_super_admin(username: str, password: str, db: Session = Depends(get_db)):
    """Super admin girişi"""
    admin = db.query(models.SuperAdmin).filter(models.SuperAdmin.username == username).first()
    
    # İlk admin kullanıcısı yoksa oluştur
    if not admin and username == "admin":
        hashed_password = get_password_hash(password)
        createNewAdmin = models.SuperAdmin(
            username=username,
            password_hash=hashed_password
        )
        db.add(createNewAdmin)
        db.commit()
        db.refresh(createNewAdmin)
        
        # JWT token oluştur
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        return schemas.LoginSuperAdmin(
            username=username, 
            access_token=access_token,
            token_type="bearer"
        )
    
    # Kullanıcı bulunamadıysa
    if not admin:
        raise HTTPException(status_code=401, detail="Kullanici adi veya sifre hatali")
    
    # Şifre kontrolü
    if not verify_password(password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Kullanici adi veya sifre hatali")
    
    # JWT token oluştur
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    return schemas.LoginSuperAdmin(
        username=username,
        access_token=access_token,
        token_type="bearer"
    )

