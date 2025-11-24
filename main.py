import asyncio
import sys

# PythonAnywhere üzerinde çakışmayı önlemek için standart asyncio politikasını zorla
if sys.platform != "win32":
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas
from database import engine, Base, get_db

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
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj