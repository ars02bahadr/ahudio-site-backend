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


@router.get("/", response_model=list[schemas.AssistantWithVoice])
async def get_assistants(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Tüm asistanları getir - token gerekli"""
    vapi_service = VAPIService()
    
    try:
        vapi_assistants = await vapi_service.get_assistants()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'den veri çekilemedi: {str(e)}")
    
    # VAPI'den gelen tüm asistanları veritabanına kaydet
    for vapi_assistant in vapi_assistants:
        await sync_assistant_from_vapi(vapi_assistant, db)
    
    # Veritabanından tüm asistanları getir ve voice/model bilgilerini ekle
    assistants = db.query(models.Assistant).all()
    result = []
    for assistant in assistants:
        voice = db.query(models.Voice).filter(models.Voice.assistant_id == assistant.id).first()
        
        # Voice objesini oluştur (stability ve similarity_boost'u float'a çevir)
        voice_obj = None
        if voice:
            voice_obj = schemas.VoiceRead(
                id=voice.id,
                assistant_id=voice.assistant_id,
                model=voice.model,
                voice_id=voice.voice_id,
                provider=voice.provider,
                stability=float(voice.stability) if voice.stability else None,
                similarity_boost=float(voice.similarity_boost) if voice.similarity_boost else None
            )
        
        # Model bilgisini parse et
        model_obj = None
        if assistant.model_data:
            model_data = json.loads(assistant.model_data)
            model_obj = schemas.ModelRead(
                model=model_data.get("model"),
                provider=model_data.get("provider"),
                temperature=model_data.get("temperature"),
                max_tokens=model_data.get("maxTokens"),
                messages=model_data.get("messages", []),
                tool_ids=model_data.get("toolIds", [])
            )
        
        result_dict = {
            "id": assistant.id,
            "vapi_id": assistant.vapi_id,
            "org_id": assistant.org_id,
            "name": assistant.name,
            "first_message": assistant.first_message,
            "voicemail_message": assistant.voicemail_message,
            "end_call_message": assistant.end_call_message,
            "created_at": assistant.created_at,
            "updated_at": assistant.updated_at,
            "created_at_local": assistant.created_at_local,
            "updated_at_local": assistant.updated_at_local,
            "voice": voice_obj,
            "model": model_obj
        }
        result.append(schemas.AssistantWithVoice(**result_dict))
    
    return result


@router.get("/{assistant_id}", response_model=schemas.AssistantWithVoice)
async def get_assistant(
    assistant_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Belirli bir asistanı getir - token gerekli"""
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
    
    # Voice objesini oluştur (stability ve similarity_boost'u float'a çevir)
    voice_obj = None
    if voice:
        voice_obj = schemas.VoiceRead(
            id=voice.id,
            assistant_id=voice.assistant_id,
            model=voice.model,
            voice_id=voice.voice_id,
            provider=voice.provider,
            stability=float(voice.stability) if voice.stability else None,
            similarity_boost=float(voice.similarity_boost) if voice.similarity_boost else None
        )
    
    # Model bilgisini parse et
    model_obj = None
    if assistant.model_data:
        model_data = json.loads(assistant.model_data)
        model_obj = schemas.ModelRead(
            model=model_data.get("model"),
            provider=model_data.get("provider"),
            temperature=model_data.get("temperature"),
            max_tokens=model_data.get("maxTokens"),
            messages=model_data.get("messages", []),
            tool_ids=model_data.get("toolIds", [])
        )
    
    # AssistantWithVoice oluştur
    result_dict = {
        "id": assistant.id,
        "vapi_id": assistant.vapi_id,
        "org_id": assistant.org_id,
        "name": assistant.name,
        "first_message": assistant.first_message,
        "voicemail_message": assistant.voicemail_message,
        "end_call_message": assistant.end_call_message,
        "created_at": assistant.created_at,
        "updated_at": assistant.updated_at,
        "created_at_local": assistant.created_at_local,
        "updated_at_local": assistant.updated_at_local,
        "voice": voice_obj,
        "model": model_obj
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
                
                # System prompt varsa, messages array'ini güncelle
                if assistant_data.system_prompt is not None:
                    # System message'ı bul veya oluştur
                    system_message_found = False
                    for i, msg in enumerate(messages):
                        if msg.get("role") == "system":
                            messages[i] = {
                                "role": "system",
                                "content": assistant_data.system_prompt
                            }
                            system_message_found = True
                            break
                    
                    # System message yoksa ekle
                    if not system_message_found:
                        messages = [{"role": "system", "content": assistant_data.system_prompt}] + messages
                
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
            # Model bulunamadı, system_prompt varsa messages ile birlikte gönder
            if assistant_data.system_prompt is not None:
                vapi_data["model"] = {
                    "model": assistant_data.behavior_type,
                    "messages": [{"role": "system", "content": assistant_data.system_prompt}]
                }
            else:
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
    
    # Önce VAPI'den mevcut asistanı çek
    try:
        current_vapi_assistant = await vapi_service.get_assistant(assistant.vapi_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'den mevcut asistan bilgisi alınamadı: {str(e)}")
    
    # VAPI'den mevcut asistanları çek (config bilgileri için)
    vapi_assistants = await vapi_service.get_assistants()
    
    # VAPI'ye gönderilecek veri - mevcut asistanın bilgilerini kullan
    vapi_data = {}
    if assistant_data.name is not None:
        vapi_data["name"] = assistant_data.name
    if assistant_data.first_message is not None:
        vapi_data["firstMessage"] = assistant_data.first_message
    if assistant_data.voicemail_message is not None:
        vapi_data["voicemailMessage"] = assistant_data.voicemail_message
    if assistant_data.end_call_message is not None:
        vapi_data["endCallMessage"] = assistant_data.end_call_message
    
    # Voice bilgilerini güncelle (voice_type varsa)
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
            # Mevcut voice bilgilerini al, sadece voiceId'yi değiştir
            current_voice = current_vapi_assistant.get("voice", {})
            vapi_data["voice"] = {
                "voiceId": assistant_data.voice_type,
                "model": current_voice.get("model"),
                "provider": current_voice.get("provider"),
                "stability": current_voice.get("stability"),
                "similarityBoost": current_voice.get("similarityBoost")
            }
    
    # Model bilgilerini güncelle (behavior_type veya system_prompt varsa)
    if assistant_data.behavior_type is not None or assistant_data.system_prompt is not None:
        # Mevcut model bilgilerini al
        current_model = current_vapi_assistant.get("model", {})
        current_messages = current_model.get("messages", [])
        
        if assistant_data.behavior_type is not None:
            model_found = False
            for vapi_assistant in vapi_assistants:
                model_data = vapi_assistant.get("model", {})
                if model_data and model_data.get("model") == assistant_data.behavior_type:
                    messages = model_data.get("messages", [])
                    
                    # System prompt varsa, messages array'ini güncelle
                    if assistant_data.system_prompt is not None:
                        # System message'ı bul veya oluştur
                        system_message_found = False
                        for i, msg in enumerate(messages):
                            if msg.get("role") == "system":
                                messages[i] = {
                                    "role": "system",
                                    "content": assistant_data.system_prompt
                                }
                                system_message_found = True
                                break
                        
                        # System message yoksa ekle
                        if not system_message_found:
                            messages = [{"role": "system", "content": assistant_data.system_prompt}] + messages
                    
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
                # Model bulunamadı, mevcut model bilgilerini kullan
                if not current_model:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Model '{assistant_data.behavior_type}' bulunamadı ve mevcut asistanın model bilgisi yok. Lütfen geçerli bir model adı kullanın."
                    )
                
                # Mevcut model bilgilerini kullan, sadece model adını değiştir
                provider = current_model.get("provider") or "openai"
                messages = current_messages.copy()
                
                # System prompt varsa, messages array'ini güncelle
                if assistant_data.system_prompt is not None:
                    system_message_found = False
                    for i, msg in enumerate(messages):
                        if msg.get("role") == "system":
                            messages[i] = {
                                "role": "system",
                                "content": assistant_data.system_prompt
                            }
                            system_message_found = True
                            break
                    
                    if not system_message_found:
                        messages = [{"role": "system", "content": assistant_data.system_prompt}] + messages
                
                vapi_data["model"] = {
                    "model": assistant_data.behavior_type,
                    "provider": provider,
                    "temperature": current_model.get("temperature"),
                    "maxTokens": current_model.get("maxTokens"),
                    "messages": messages
                }
        elif assistant_data.system_prompt is not None:
            # Sadece system_prompt güncelleniyor, model değişmiyor
            if not current_model:
                raise HTTPException(
                    status_code=400,
                    detail="Mevcut asistanın model bilgisi yok. System prompt'u güncellemek için önce model bilgisi olmalı."
                )
            
            messages = current_messages.copy()
            # System message'ı bul veya oluştur
            system_message_found = False
            for i, msg in enumerate(messages):
                if msg.get("role") == "system":
                    messages[i] = {
                        "role": "system",
                        "content": assistant_data.system_prompt
                    }
                    system_message_found = True
                    break
            
            if not system_message_found:
                messages = [{"role": "system", "content": assistant_data.system_prompt}] + messages
            
            vapi_data["model"] = {
                "model": current_model.get("model"),
                "provider": current_model.get("provider"),
                "temperature": current_model.get("temperature"),
                "maxTokens": current_model.get("maxTokens"),
                "messages": messages
            }
    
    # Boş dict kontrolü
    if not vapi_data:
        raise HTTPException(status_code=400, detail="Güncellenecek alan belirtilmedi")
    
    try:
        vapi_response = await vapi_service.update_assistant(assistant.vapi_id, vapi_data)
    except Exception as e:
        # Daha detaylı hata mesajı için response body'yi de göster
        error_detail = str(e)
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            try:
                error_body = e.response.text
                error_detail = f"{error_detail}\nResponse: {error_body}"
            except:
                pass
        raise HTTPException(status_code=500, detail=f"VAPI'de asistan güncellenemedi: {error_detail}")
    
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

