from datetime import  timedelta

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas
from database import engine, Base, get_db
from decode import ACCESS_TOKEN_EXPIRE_MINUTES, verify_password, get_password_hash, create_access_token, verify_token
import uvicorn


app = FastAPI(title="Basit Tek-Request Form API")

# CORS Ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

# Test için Ana Sayfa Endpoint'i
@app.get("/")
def read_root():
    return {"status": "ok", "message": "API Calisiyor! /docs adresine gidin."}

@app.post("/contactUs/", response_model=schemas.MessageRead, status_code=201)
def create_message(message: schemas.MessageCreate, db: Session = Depends(get_db)):
    db_obj = models.Message(
        name=message.name,
        email=message.email,
        company=message.company,
        business_type=message.business_type,
        message=message.message,
        phone_number=message.phone_number,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@app.get("/messages/", response_model=schemas.MessageList)
def get_messages(
    page_number: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    # Token doğrulandı, kullanıcı: current_user
    messages = db.query(models.Message).offset((page_number - 1) * page_size).limit(page_size).all()
    messageList = schemas.MessageList(
        items=messages,
        page_number=page_number,
        page_size=page_size,
        total_count=db.query(models.Message).count(),
        total_pages=(db.query(models.Message).count() + page_size - 1) // page_size,
        has_next_page=(db.query(models.Message).count() > page_number * page_size),
        has_previous_page=(page_number > 1)
    )
    return messageList


@app.post("/login/", response_model=schemas.LoginSuperAdmin)
def login_super_admin(username: str, password: str, db: Session = Depends(get_db)):
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


# ==================== About Endpoints ====================
@app.get("/about/", response_model=schemas.AboutRead)
def get_about(db: Session = Depends(get_db)):
    """Get About bilgisi - ilk kaydı getirir, yoksa default değerlerle oluşturur"""
    about = db.query(models.About).first()
    if not about:
        # Default değerlerle oluştur
        about = models.About(
            description="Ahudio hakkında açıklama",
            vision="Vizyonumuz",
            mission="Misyonumuz"
        )
        db.add(about)
        db.commit()
        db.refresh(about)
    return about


@app.put("/about/", response_model=schemas.AboutRead)
def update_about(
    about_data: schemas.AboutUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """About bilgisini güncelle - token gerekli"""
    about = db.query(models.About).first()
    if not about:
        # Yoksa oluştur
        about = models.About(
            description=about_data.description,
            vision=about_data.vision,
            mission=about_data.mission
        )
        db.add(about)
    else:
        # Varsa güncelle
        about.description = about_data.description
        about.vision = about_data.vision
        about.mission = about_data.mission
    
    db.commit()
    db.refresh(about)
    return about


# ==================== Email Address Endpoints ====================
@app.get("/emails/", response_model=list[schemas.EmailAddressRead])
def get_all_emails(db: Session = Depends(get_db)):
    """Tüm email adreslerini getir"""
    return db.query(models.EmailAddress).all()


@app.get("/emails/{email_id}", response_model=schemas.EmailAddressRead)
def get_email(email_id: int, db: Session = Depends(get_db)):
    """Belirli bir email adresini getir"""
    email = db.query(models.EmailAddress).filter(models.EmailAddress.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email adresi bulunamadı")
    return email


@app.post("/emails/", response_model=schemas.EmailAddressRead, status_code=201)
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


@app.put("/emails/{email_id}", response_model=schemas.EmailAddressRead)
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


@app.delete("/emails/{email_id}", status_code=204)
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


# ==================== Phone Number Endpoints ====================
@app.get("/phones/", response_model=list[schemas.PhoneNumberRead])
def get_all_phones(db: Session = Depends(get_db)):
    """Tüm telefon numaralarını getir"""
    return db.query(models.PhoneNumber).all()


@app.get("/phones/{phone_id}", response_model=schemas.PhoneNumberRead)
def get_phone(phone_id: int, db: Session = Depends(get_db)):
    """Belirli bir telefon numarasını getir"""
    phone = db.query(models.PhoneNumber).filter(models.PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Telefon numarası bulunamadı")
    return phone


@app.post("/phones/", response_model=schemas.PhoneNumberRead, status_code=201)
def create_phone(
    phone_data: schemas.PhoneNumberCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Yeni telefon numarası ekle - token gerekli"""
    phone = models.PhoneNumber(value=phone_data.value)
    db.add(phone)
    db.commit()
    db.refresh(phone)
    return phone


@app.put("/phones/{phone_id}", response_model=schemas.PhoneNumberRead)
def update_phone(
    phone_id: int,
    phone_data: schemas.PhoneNumberCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Telefon numarasını güncelle - token gerekli"""
    phone = db.query(models.PhoneNumber).filter(models.PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Telefon numarası bulunamadı")
    
    phone.value = phone_data.value
    db.commit()
    db.refresh(phone)
    return phone


@app.delete("/phones/{phone_id}", status_code=204)
def delete_phone(
    phone_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Telefon numarasını sil - token gerekli"""
    phone = db.query(models.PhoneNumber).filter(models.PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Telefon numarası bulunamadı")
    
    db.delete(phone)
    db.commit()
    return None


# ==================== Property Endpoints ====================
@app.get("/property/", response_model=schemas.PropertyRead)
def get_property(db: Session = Depends(get_db)):
    """Property bilgisi - ilk kaydı getirir, yoksa default değerlerle oluşturur"""
    prop = db.query(models.Property).first()
    if not prop:
        # Default değerlerle oluştur
        prop = models.Property(
            voice_type=models.VoiceType.SES_1,
            behavior_type=models.BehaviorType.DAVRANIS_1,
            opening_message="Hoş geldiniz",
            closing_message="İyi günler",
            prompt=""
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)
    return prop


@app.put("/property/", response_model=schemas.PropertyRead)
def update_property(
    property_data: schemas.PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Property bilgisini güncelle - token gerekli"""
    prop = db.query(models.Property).first()
    if not prop:
        # Yoksa oluştur
        prop = models.Property(
            voice_type=property_data.voice_type,
            behavior_type=property_data.behavior_type,
            opening_message=property_data.opening_message,
            closing_message=property_data.closing_message,
            prompt=property_data.prompt
        )
        db.add(prop)
    else:
        # Varsa güncelle
        prop.voice_type = property_data.voice_type
        prop.behavior_type = property_data.behavior_type
        prop.opening_message = property_data.opening_message
        prop.closing_message = property_data.closing_message
        prop.prompt = property_data.prompt
    
    db.commit()
    db.refresh(prop)
    return prop


@app.post("/property/upload-prompt/", response_model=schemas.PropertyRead)
async def upload_prompt_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """TXT dosyası yükleyerek prompt alanını güncelle - token gerekli"""
    # Dosya uzantısı kontrolü
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Sadece .txt dosyaları kabul edilir")
    
    # Dosya boyutu kontrolü (20MB = 20 * 1024 * 1024 bytes)
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    if file_size_mb > 20:
        raise HTTPException(status_code=400, detail=f"Dosya boyutu {file_size_mb:.2f}MB. Maksimum 20MB olmalıdır")
    
    # Dosya içeriğini oku ve decode et
    try:
        prompt_text = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            # UTF-8 başarısız olursa ISO-8859-9 (Turkish) dene
            prompt_text = content.decode('iso-8859-9')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Dosya içeriği okunamadı. UTF-8 veya ISO-8859-9 formatında olmalıdır")
    
    # Property kaydını bul veya oluştur
    prop = db.query(models.Property).first()
    if not prop:
        # Yoksa oluştur
        prop = models.Property(
            voice_type=models.VoiceType.SES_1,
            behavior_type=models.BehaviorType.DAVRANIS_1,
            opening_message="Hoş geldiniz",
            closing_message="İyi günler",
            prompt=prompt_text
        )
        db.add(prop)
    else:
        # Varsa sadece prompt'u güncelle
        prop.prompt = prompt_text
    
    db.commit()
    db.refresh(prop)
    return prop


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)