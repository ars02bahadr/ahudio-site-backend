from datetime import  timedelta

from fastapi import FastAPI, Depends, HTTPException
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)