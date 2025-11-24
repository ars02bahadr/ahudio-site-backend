from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas
from database import engine, Base, get_db


app = FastAPI(title="Ahudio Site Backend API", version="1.0.0")

# CORS Ayarları
# allow_origins=["*"] ile tüm kaynaklardan gelen isteklere izin verilir.
# Production ortamında buraya sadece kendi frontend domainini yazman daha güvenli olur.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tüm domainlere izin ver
    allow_credentials=True,
    allow_methods=["*"],  # Tüm HTTP metodlarına (GET, POST, PUT vs.) izin ver
    allow_headers=["*"],  # Tüm headerlara izin ver
)

Base.metadata.create_all(bind=engine)


@app.post("/contactUs/", response_model=schemas.MessageRead, status_code=201)
def create_message(message: schemas.MessageCreate, db: Session = Depends(get_db)):

    db_obj = models.Message(
        name=message.name,
        email=message.email,
        company=message.company,
        business_type=message.business_type,
        message=message.message,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj