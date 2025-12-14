from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import schemas
import models
from database import get_db
from decode import verify_token

router = APIRouter(prefix="/about", tags=["Hakkında"])


@router.get("/", response_model=schemas.AboutRead)
def get_about(db: Session = Depends(get_db)):
    """About bilgisi - ilk kaydı getirir, yoksa default değerlerle oluşturur"""
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


@router.put("/", response_model=schemas.AboutRead)
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

