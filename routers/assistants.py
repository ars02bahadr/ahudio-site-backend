import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import schemas
import models
from database import get_db
from decode import verify_token
from services.vapi_service import VAPIService
from services.assistant_service import sync_assistant_from_vapi

router = APIRouter(prefix="/assistants", tags=["Asistanlar"])


@router.get("/", response_model=list[schemas.AssistantRead])
async def get_assistants(db: Session = Depends(get_db)):
    """Tüm asistanları getir - önce VAPI'den çek, sonra veritabanına kaydet"""
    vapi_service = VAPIService()
    
    try:
        vapi_assistants = await vapi_service.get_assistants()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'den veri çekilemedi: {str(e)}")
    
    # VAPI'den gelen tüm asistanları veritabanına kaydet
    for vapi_assistant in vapi_assistants:
        await sync_assistant_from_vapi(vapi_assistant, db)
    
    # Veritabanından tüm asistanları getir
    return db.query(models.Assistant).all()


@router.get("/{assistant_id}", response_model=schemas.AssistantWithVoice)
async def get_assistant(assistant_id: int, db: Session = Depends(get_db)):
    """Belirli bir asistanı getir - önce VAPI'den çek, sonra veritabanına kaydet"""
    assistant = db.query(models.Assistant).filter(models.Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Asistan bulunamadı")
    
    vapi_service = VAPIService()
    
    try:
        # VAPI'den bu asistanı çek
        vapi_assistant = await vapi_service.get_assistant(assistant.vapi_id)
        # Veritabanını güncelle
        assistant = await sync_assistant_from_vapi(vapi_assistant, db)
    except Exception as e:
        # VAPI'den çekilemezse veritabanından getir
        pass
    
    voice = db.query(models.Voice).filter(models.Voice.assistant_id == assistant_id).first()
    
    # AssistantWithVoice oluştur
    result_dict = {
        "id": assistant.id,
        "vapi_id": assistant.vapi_id,
        "org_id": assistant.org_id,
        "name": assistant.name,
        "voice_type": assistant.voice_type,
        "behavior_type": assistant.behavior_type,
        "first_message": assistant.first_message,
        "voicemail_message": assistant.voicemail_message,
        "end_call_message": assistant.end_call_message,
        "created_at": assistant.created_at,
        "updated_at": assistant.updated_at,
        "created_at_local": assistant.created_at_local,
        "updated_at_local": assistant.updated_at_local,
        "voice": schemas.VoiceRead.model_validate(voice) if voice else None
    }
    return schemas.AssistantWithVoice(**result_dict)


@router.post("/", response_model=schemas.AssistantRead, status_code=201)
async def create_assistant(
    assistant_data: schemas.AssistantCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """VAPI'de yeni asistan oluştur - token gerekli"""
    vapi_service = VAPIService()
    
    # VAPI'den mevcut asistanları çek (config bilgileri için)
    vapi_assistants = await vapi_service.get_assistants()
    
    # VAPI'ye gönderilecek veri
    vapi_data = {
        "name": assistant_data.name,
        "firstMessage": assistant_data.first_message,
        "voicemailMessage": assistant_data.voicemail_message,
        "endCallMessage": assistant_data.end_call_message
    }
    
    # Voice bilgilerini otomatik doldur (voice_type varsa)
    if assistant_data.voice_type:
        voice_found = False
        for assistant in vapi_assistants:
            voice = assistant.get("voice", {})
            if voice and voice.get("voiceId") == assistant_data.voice_type:
                vapi_data["voice"] = {
                    "voiceId": voice.get("voiceId"),
                    "model": voice.get("model"),
                    "provider": voice.get("provider"),
                    "stability": voice.get("stability"),
                    "similarityBoost": voice.get("similarityBoost")
                }
                voice_found = True
                break
        if not voice_found:
            # Sadece voiceId ile gönder
            vapi_data["voice"] = {
                "voiceId": assistant_data.voice_type
            }
    
    # Model bilgilerini otomatik doldur (behavior_type varsa)
    if assistant_data.behavior_type:
        model_found = False
        for assistant in vapi_assistants:
            model_data = assistant.get("model", {})
            if model_data and model_data.get("model") == assistant_data.behavior_type:
                messages = model_data.get("messages", [])
                vapi_data["model"] = {
                    "model": model_data.get("model"),
                    "provider": model_data.get("provider"),
                    "temperature": model_data.get("temperature"),
                    "maxTokens": model_data.get("maxTokens"),
                    "messages": messages
                }
                model_found = True
                break
        if not model_found:
            # Sadece model ile gönder
            vapi_data["model"] = {
                "model": assistant_data.behavior_type
            }
    
    # Transcriber bilgilerini otomatik doldur (mevcut asistanlardan ilk transcriber'ı kullan)
    transcriber_found = False
    for assistant in vapi_assistants:
        transcriber = assistant.get("transcriber", {})
        if transcriber:
            vapi_data["transcriber"] = {
                "model": transcriber.get("model"),
                "language": transcriber.get("language"),
                "provider": transcriber.get("provider"),
                "endpointing": transcriber.get("endpointing")
            }
            transcriber_found = True
            break
    
    # Silence timeout'u otomatik doldur (mevcut asistanlardan ilk değeri kullan)
    for assistant in vapi_assistants:
        silence_timeout = assistant.get("silenceTimeoutSeconds")
        if silence_timeout is not None:
            vapi_data["silenceTimeoutSeconds"] = silence_timeout
            break
    
    try:
        vapi_response = await vapi_service.create_assistant(vapi_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'de asistan oluşturulamadı: {str(e)}")
    
    # Veritabanına kaydet
    new_assistant = models.Assistant(
        vapi_id=vapi_response.get("id"),
        org_id=vapi_response.get("orgId"),
        name=vapi_response.get("name", assistant_data.name),
        voice_type=assistant_data.voice_type,
        behavior_type=assistant_data.behavior_type,
        first_message=vapi_response.get("firstMessage", assistant_data.first_message),
        voicemail_message=vapi_response.get("voicemailMessage", assistant_data.voicemail_message),
        end_call_message=vapi_response.get("endCallMessage", assistant_data.end_call_message),
        model_data=json.dumps(vapi_response.get("model", {})),
        transcriber_data=json.dumps(vapi_response.get("transcriber", {})),
        silence_timeout_seconds=vapi_response.get("silenceTimeoutSeconds"),
        client_messages=json.dumps(vapi_response.get("clientMessages", [])),
        server_messages=json.dumps(vapi_response.get("serverMessages", [])),
        end_call_phrases=json.dumps(vapi_response.get("endCallPhrases", [])),
        hipaa_enabled=str(vapi_response.get("hipaaEnabled", False)).lower(),
        background_denoising_enabled=str(vapi_response.get("backgroundDenoisingEnabled", False)).lower(),
        start_speaking_plan=json.dumps(vapi_response.get("startSpeakingPlan", {})),
        is_server_url_secret_set=str(vapi_response.get("isServerUrlSecretSet", False)).lower(),
        created_at=vapi_service.parse_datetime(vapi_response.get("createdAt")),
        updated_at=vapi_service.parse_datetime(vapi_response.get("updatedAt"))
    )
    db.add(new_assistant)
    db.flush()
    
    # Voice kaydını oluştur
    voice_data = vapi_response.get("voice", {})
    if voice_data:
        new_voice = models.Voice(
            assistant_id=new_assistant.id,
            model=voice_data.get("model"),
            voice_id=voice_data.get("voiceId"),
            provider=voice_data.get("provider"),
            stability=str(voice_data.get("stability")) if voice_data.get("stability") is not None else None,
            similarity_boost=str(voice_data.get("similarityBoost")) if voice_data.get("similarityBoost") is not None else None
        )
        db.add(new_voice)
    
    db.commit()
    db.refresh(new_assistant)
    return new_assistant


@router.patch("/{assistant_id}", response_model=schemas.AssistantRead)
async def update_assistant(
    assistant_id: int,
    assistant_data: schemas.AssistantUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """VAPI'de asistanı güncelle - token gerekli"""
    assistant = db.query(models.Assistant).filter(models.Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Asistan bulunamadı")
    
    vapi_service = VAPIService()
    
    # VAPI'den mevcut asistanları çek (config bilgileri için)
    vapi_assistants = await vapi_service.get_assistants()
    
    # VAPI'ye gönderilecek veri
    vapi_data = {}
    if assistant_data.name is not None:
        vapi_data["name"] = assistant_data.name
    if assistant_data.first_message is not None:
        vapi_data["firstMessage"] = assistant_data.first_message
    if assistant_data.voicemail_message is not None:
        vapi_data["voicemailMessage"] = assistant_data.voicemail_message
    if assistant_data.end_call_message is not None:
        vapi_data["endCallMessage"] = assistant_data.end_call_message
    
    # Voice bilgilerini otomatik doldur (voice_type varsa)
    if assistant_data.voice_type is not None:
        voice_found = False
        for vapi_assistant in vapi_assistants:
            voice = vapi_assistant.get("voice", {})
            if voice and voice.get("voiceId") == assistant_data.voice_type:
                vapi_data["voice"] = {
                    "voiceId": voice.get("voiceId"),
                    "model": voice.get("model"),
                    "provider": voice.get("provider"),
                    "stability": voice.get("stability"),
                    "similarityBoost": voice.get("similarityBoost")
                }
                voice_found = True
                break
        if not voice_found:
            vapi_data["voice"] = {"voiceId": assistant_data.voice_type}
    
    # Model bilgilerini otomatik doldur (behavior_type varsa)
    if assistant_data.behavior_type is not None:
        model_found = False
        for vapi_assistant in vapi_assistants:
            model_data = vapi_assistant.get("model", {})
            if model_data and model_data.get("model") == assistant_data.behavior_type:
                messages = model_data.get("messages", [])
                vapi_data["model"] = {
                    "model": model_data.get("model"),
                    "provider": model_data.get("provider"),
                    "temperature": model_data.get("temperature"),
                    "maxTokens": model_data.get("maxTokens"),
                    "messages": messages
                }
                model_found = True
                break
        if not model_found:
            vapi_data["model"] = {"model": assistant_data.behavior_type}
    
    try:
        vapi_response = await vapi_service.update_assistant(assistant.vapi_id, vapi_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'de asistan güncellenemedi: {str(e)}")
    
    # Veritabanını güncelle
    if assistant_data.name is not None:
        assistant.name = vapi_response.get("name", assistant_data.name)
    if assistant_data.first_message is not None:
        assistant.first_message = vapi_response.get("firstMessage", assistant_data.first_message)
    if assistant_data.voicemail_message is not None:
        assistant.voicemail_message = vapi_response.get("voicemailMessage", assistant_data.voicemail_message)
    if assistant_data.end_call_message is not None:
        assistant.end_call_message = vapi_response.get("endCallMessage", assistant_data.end_call_message)
    if assistant_data.voice_type is not None:
        assistant.voice_type = assistant_data.voice_type
    if assistant_data.behavior_type is not None:
        assistant.behavior_type = assistant_data.behavior_type
    
    assistant.updated_at = vapi_service.parse_datetime(vapi_response.get("updatedAt"))
    
    db.commit()
    db.refresh(assistant)
    return assistant


@router.delete("/{assistant_id}", status_code=204)
async def delete_assistant(
    assistant_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """VAPI'den asistanı sil - token gerekli"""
    assistant = db.query(models.Assistant).filter(models.Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Asistan bulunamadı")
    
    vapi_service = VAPIService()
    
    try:
        await vapi_service.delete_assistant(assistant.vapi_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'den asistan silinemedi: {str(e)}")
    
    # Voice kaydını sil
    db.query(models.Voice).filter(models.Voice.assistant_id == assistant_id).delete()
    
    # Asistanı sil
    db.delete(assistant)
    db.commit()
    return None

