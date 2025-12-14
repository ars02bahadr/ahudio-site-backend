from fastapi import APIRouter, HTTPException
from services.vapi_service import VAPIService
from typing import List, Dict

router = APIRouter(prefix="/vapi", tags=["VAPI Tipleri"])


@router.get("/voice-types", response_model=List[Dict])
async def get_voice_types():
    """VAPI'den ses tiplerini getir (mevcut asistanlardan unique voice'ları çıkarır)"""
    vapi_service = VAPIService()
    
    try:
        assistants = await vapi_service.get_assistants()
        # Tüm asistanlardan unique voice bilgilerini çıkar
        voice_types = []
        seen_voices = set()
        
        for assistant in assistants:
            voice = assistant.get("voice", {})
            if voice:
                voice_id = voice.get("voiceId")
                if voice_id and voice_id not in seen_voices:
                    seen_voices.add(voice_id)
                    voice_types.append({
                        "voice_id": voice_id,
                        "model": voice.get("model"),
                        "provider": voice.get("provider"),
                        "stability": voice.get("stability"),
                        "similarity_boost": voice.get("similarityBoost")
                    })
        
        return voice_types
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'den ses tipleri çekilemedi: {str(e)}")


@router.get("/behavior-types", response_model=List[Dict])
async def get_behavior_types():
    """VAPI'den davranış tiplerini getir (model bilgilerinden)"""
    vapi_service = VAPIService()
    
    try:
        assistants = await vapi_service.get_assistants()
        # Tüm asistanlardan unique model/prompt bilgilerini çıkar
        behavior_types = []
        seen_behaviors = set()
        
        for assistant in assistants:
            model_data = assistant.get("model", {})
            if model_data:
                # Model tipini ve messages içindeki system prompt'u kullan
                model_type = model_data.get("model")
                messages = model_data.get("messages", [])
                system_message = None
                for msg in messages:
                    if msg.get("role") == "system":
                        system_message = msg.get("content", "")
                        break
                
                behavior_key = f"{model_type}_{hash(system_message) if system_message else 'default'}"
                if behavior_key not in seen_behaviors:
                    seen_behaviors.add(behavior_key)
                    behavior_types.append({
                        "model": model_type,
                        "provider": model_data.get("provider"),
                        "temperature": model_data.get("temperature"),
                        "max_tokens": model_data.get("maxTokens"),
                        "description": system_message[:100] if system_message else None
                    })
        
        return behavior_types
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'den davranış tipleri çekilemedi: {str(e)}")

