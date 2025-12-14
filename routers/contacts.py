from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import schemas
import models
from database import get_db
from decode import verify_token

router = APIRouter(tags=["İletişim"])


@router.post("/contactUs/", response_model=schemas.MessageRead, status_code=201)
def create_message(message: schemas.MessageCreate, db: Session = Depends(get_db)):
    """İletişim formu mesajı oluştur"""
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


@router.get("/messages/", response_model=schemas.MessageList, tags=["Mesajlar"])
def get_messages(
    page_number: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Tüm mesajları getir - token gerekli"""
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

