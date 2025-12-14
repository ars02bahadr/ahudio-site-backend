import json
from sqlalchemy.orm import Session
from datetime import datetime
import models
from services.vapi_service import VAPIService


async def sync_assistant_from_vapi(vapi_assistant: dict, db: Session) -> models.Assistant:
    """VAPI'den gelen asistan verisini veritabanına kaydet veya güncelle"""
    vapi_service = VAPIService()
    
    # Mevcut asistanı kontrol et
    existing = db.query(models.Assistant).filter(
        models.Assistant.vapi_id == vapi_assistant.get("id")
    ).first()
    
    # Voice bilgilerini çıkar
    voice_data = vapi_assistant.get("voice", {})
    # Voice type'ı voiceId'den çıkar
    voice_type = voice_data.get("voiceId") if voice_data else None
    
    # Model bilgilerini çıkar
    model_data = vapi_assistant.get("model", {})
    # Behavior type'ı model.model'den çıkar
    behavior_type = model_data.get("model") if model_data else None
    
    if existing:
        # Güncelle
        existing.name = vapi_assistant.get("name", "")
        existing.org_id = vapi_assistant.get("orgId")
        existing.voice_type = voice_type
        existing.behavior_type = behavior_type
        existing.first_message = vapi_assistant.get("firstMessage")
        existing.voicemail_message = vapi_assistant.get("voicemailMessage")
        existing.end_call_message = vapi_assistant.get("endCallMessage")
        existing.model_data = json.dumps(model_data)
        existing.transcriber_data = json.dumps(vapi_assistant.get("transcriber", {}))
        existing.silence_timeout_seconds = vapi_assistant.get("silenceTimeoutSeconds")
        existing.client_messages = json.dumps(vapi_assistant.get("clientMessages", []))
        existing.server_messages = json.dumps(vapi_assistant.get("serverMessages", []))
        existing.end_call_phrases = json.dumps(vapi_assistant.get("endCallPhrases", []))
        existing.hipaa_enabled = str(vapi_assistant.get("hipaaEnabled", False)).lower()
        existing.background_denoising_enabled = str(vapi_assistant.get("backgroundDenoisingEnabled", False)).lower()
        existing.start_speaking_plan = json.dumps(vapi_assistant.get("startSpeakingPlan", {}))
        existing.is_server_url_secret_set = str(vapi_assistant.get("isServerUrlSecretSet", False)).lower()
        existing.created_at = vapi_service.parse_datetime(vapi_assistant.get("createdAt"))
        existing.updated_at = vapi_service.parse_datetime(vapi_assistant.get("updatedAt"))
        
        assistant_id = existing.id
        assistant = existing
    else:
        # Yeni oluştur
        new_assistant = models.Assistant(
            vapi_id=vapi_assistant.get("id"),
            org_id=vapi_assistant.get("orgId"),
            name=vapi_assistant.get("name", ""),
            voice_type=voice_type,
            behavior_type=behavior_type,
            first_message=vapi_assistant.get("firstMessage"),
            voicemail_message=vapi_assistant.get("voicemailMessage"),
            end_call_message=vapi_assistant.get("endCallMessage"),
            model_data=json.dumps(model_data),
            transcriber_data=json.dumps(vapi_assistant.get("transcriber", {})),
            silence_timeout_seconds=vapi_assistant.get("silenceTimeoutSeconds"),
            client_messages=json.dumps(vapi_assistant.get("clientMessages", [])),
            server_messages=json.dumps(vapi_assistant.get("serverMessages", [])),
            end_call_phrases=json.dumps(vapi_assistant.get("endCallPhrases", [])),
            hipaa_enabled=str(vapi_assistant.get("hipaaEnabled", False)).lower(),
            background_denoising_enabled=str(vapi_assistant.get("backgroundDenoisingEnabled", False)).lower(),
            start_speaking_plan=json.dumps(vapi_assistant.get("startSpeakingPlan", {})),
            is_server_url_secret_set=str(vapi_assistant.get("isServerUrlSecretSet", False)).lower(),
            created_at=vapi_service.parse_datetime(vapi_assistant.get("createdAt")),
            updated_at=vapi_service.parse_datetime(vapi_assistant.get("updatedAt"))
        )
        db.add(new_assistant)
        db.flush()
        assistant_id = new_assistant.id
        assistant = new_assistant
    
    # Voice kaydını güncelle veya oluştur
    existing_voice = db.query(models.Voice).filter(
        models.Voice.assistant_id == assistant_id
    ).first()
    
    if existing_voice:
        existing_voice.model = voice_data.get("model")
        existing_voice.voice_id = voice_data.get("voiceId")
        existing_voice.provider = voice_data.get("provider")
        existing_voice.stability = str(voice_data.get("stability")) if voice_data.get("stability") is not None else None
        existing_voice.similarity_boost = str(voice_data.get("similarityBoost")) if voice_data.get("similarityBoost") is not None else None
    else:
        if voice_data:
            new_voice = models.Voice(
                assistant_id=assistant_id,
                model=voice_data.get("model"),
                voice_id=voice_data.get("voiceId"),
                provider=voice_data.get("provider"),
                stability=str(voice_data.get("stability")) if voice_data.get("stability") is not None else None,
                similarity_boost=str(voice_data.get("similarityBoost")) if voice_data.get("similarityBoost") is not None else None
            )
            db.add(new_voice)
    
    db.commit()
    db.refresh(assistant)
    return assistant

